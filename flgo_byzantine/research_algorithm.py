"""FLGo asynchronous research adapter for triage, timing, roots and budgets.

Research modes are deliberately named differently from published methods.
The simulator's virtual clock schedules every reply, including malicious ones.
All oracle labels are confined to injection and reporting code.
"""

from __future__ import annotations

from collections import Counter
from time import perf_counter

import numpy as np
import torch
from torch.utils.data import Dataset

import flgo.simulator.base as simulator
from flgo.algorithm import asyncbase as _asyncbase
from flgo.algorithm import fedbase as _fedbase

from flgo_byzantine.algorithm import _attack_update, _build_aggregator, _model_from_update, _parameter_vector
from flgo_byzantine.research_methods import (
    Anytime, Triage, Update, clipped_mean, cosine, project_conflict,
    reference_fusion, root_align,
)


class _RootSamples(Dataset):
    def __init__(self, samples):
        self.samples = samples

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        return self.samples[index]


def _trigger(image, size):
    if image.ndim < 2:
        raise ValueError("backdoor trigger requires image inputs")
    image = image.clone()
    image[..., -size:, -size:] = image.max().clamp_min(1.0)
    return image


class _TriggeredTest(Dataset):
    def __init__(self, source, target, size):
        self.source = source
        self.target = target
        self.size = size
        self.indices = [i for i, label in enumerate(_dataset_labels(source))
                        if label != target]

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, index):
        image, _ = self.source[self.indices[index]]
        return _trigger(image, self.size), self.target


def _dataset_labels(dataset):
    source = getattr(dataset, "dataset", None)
    indices = getattr(dataset, "indices", None)
    targets = getattr(source, "targets", None) if source is not None else getattr(dataset, "targets", None)
    if targets is not None and indices is not None:
        return [int(targets[index]) for index in indices]
    if targets is not None:
        return [int(targets[index]) for index in range(len(dataset))]
    return [int(dataset[index][1]) for index in range(len(dataset))]


class Server(_asyncbase.AsyncServer):
    def initialize(self):
        self.research_mode = str(self.option.get("byz_mode", "baseline"))
        self.research_attack = str(self.option.get("byz_attack", "none"))
        if self.research_mode not in {"baseline", "triage", "root_only", "root_fusion", "anytime"}:
            raise ValueError("unknown byz_mode")
        if self.research_attack not in {"none", "alie", "ipm", "timed_ipm", "joint_random", "joint_timing", "backdoor"}:
            raise ValueError("unknown byz_attack")
        seed = int(self.option["byz_seed"])
        self.research_rng = np.random.default_rng(seed)
        self.delay_rng = np.random.default_rng(seed + 100_003)
        self.attack_delay_rng = np.random.default_rng(seed + 200_003)
        self.root_ids = frozenset(int(x) for x in self.option.get("byz_root_ids", []))
        if any(cid < 0 or cid >= self.num_clients for cid in self.root_ids):
            raise ValueError("root client ID outside task range")
        if self.research_mode in {"root_only", "root_fusion"} and not self.root_ids:
            raise ValueError("root modes require explicitly reserved trusted client IDs")
        eligible = sorted(set(range(self.num_clients)) - self.root_ids)
        if not eligible:
            raise ValueError("no training clients remain after reserving root clients")
        ratio = float(self.option.get("byz_malicious_fraction", 0.0))
        if not 0 <= ratio < 1:
            raise ValueError("byz_malicious_fraction must be in [0, 1)")
        attack_count = int(ratio * len(eligible)) if self.research_attack != "none" else 0
        self.byz_malicious_ids = frozenset(int(x) for x in self.research_rng.choice(
            eligible, attack_count, replace=False))
        self.byz_last_round = {}
        self.byz_history = None
        self.byz_previous_history = None
        self.byz_triage = Triage(max_age=int(self.option.get("byz_max_staleness", 4)))
        self.byz_anytime = Anytime(float(self.option.get("byz_budget_ms", 5.0)))
        self.byz_snapshots = {}
        self.byz_root = self._make_root_samples()
        self.byz_triggered_test = (
            _TriggeredTest(self.test_data,
                           int(self.option.get("byz_target_label", 0)),
                           int(self.option.get("byz_trigger_size", 3)))
            if self.research_attack == "backdoor" and self.test_data is not None else None
        )
        self.byz_aggregator = None
        self.byz_aggregator_key = None
        self.byz_minority_ids = self._minority_ids(eligible)

    def _make_root_samples(self):
        if not self.root_ids:
            return None
        classes = set(int(x) for x in self.option.get("byz_root_classes", []))
        requested = int(self.option.get("byz_root_samples", 50))
        noise = float(self.option.get("byz_root_noise", 0.0))
        if requested < 1 or not 0 <= noise <= 1:
            raise ValueError("invalid root sample count or label noise")
        pool = []
        label_space = 0
        for cid in sorted(self.root_ids):
            dataset = self.clients[cid].train_data
            for index, label in enumerate(_dataset_labels(dataset)):
                label_space = max(label_space, label + 1)
                if not classes or label in classes:
                    pool.append((dataset, index, label))
        if not pool:
            raise ValueError("trusted clients provide no matching root examples")
        chosen = self.research_rng.choice(len(pool), min(requested, len(pool)), replace=False)
        samples = []
        for index in chosen:
            dataset, sample_index, label = pool[int(index)]
            x, _ = dataset[sample_index]
            if self.research_rng.random() < noise and label_space > 1:
                label = (label + int(self.research_rng.integers(1, label_space))) % label_space
            samples.append((x, label))
        return _RootSamples(samples)

    def _minority_ids(self, eligible):
        """Oracle-only tag: clients in a sparsely represented dominant-label group."""
        dominant = {}
        for cid in eligible:
            labels = Counter(_dataset_labels(self.clients[cid].train_data))
            if labels:
                dominant[cid] = labels.most_common(1)[0][0]
        group_sizes = Counter(dominant.values())
        if not group_sizes or len(set(group_sizes.values())) == 1:
            return frozenset()
        threshold = float(np.quantile(list(group_sizes.values()), 0.25))
        rare = {label for label, count in group_sizes.items()
                if count <= threshold and count < max(group_sizes.values())}
        return frozenset(cid for cid, label in dominant.items() if label in rare)

    def sample(self):
        return [cid for cid in super().sample()
                if cid not in self.root_ids and cid not in self.concurrent_clients]

    def pack(self, client_id, mtype=0, *args, **kwargs):
        self.byz_snapshots.setdefault(self.current_round,
                                      _parameter_vector(self.model).clone())
        package = super().pack(client_id, mtype, *args, **kwargs)
        package["byz_version"] = self.current_round
        package["byz_backdoor"] = self.research_attack == "backdoor" and client_id in self.byz_malicious_ids
        package["byz_target"] = int(self.option.get("byz_target_label", 0))
        package["byz_trigger_size"] = int(self.option.get("byz_trigger_size", 3))
        return package

    @simulator.with_clock
    def communicate(self, selected_clients, mtype=0, asynchronous=False):
        # Call FLGo's original transport inside its clock decorator.  Modifying
        # __t here changes when the virtual clock releases each complete reply.
        response = _fedbase.BasicServer.communicate.__wrapped__(
            self, selected_clients, mtype, asynchronous)
        ids = response.get("__cid", [])
        models = response.get("model", [])
        if not ids:
            return response
        versions = response.get("byz_version", [])
        benign = []
        for cid, model, version in zip(ids, models, versions):
            if cid not in self.byz_malicious_ids:
                benign.append(self.byz_snapshots[int(version)] - _parameter_vector(model))
        malicious_count = sum(cid in self.byz_malicious_ids for cid in ids)
        for index, cid in enumerate(ids):
            delay = self._ordinary_delay()
            if cid in self.byz_malicious_ids and self.research_attack != "backdoor":
                version = int(versions[index])
                base = self.byz_snapshots[version]
                attack = self._malicious_update(benign, base, len(ids), malicious_count)
                response["model"][index] = _model_from_update(self.model, attack)
                if self.research_attack == "joint_timing":
                    delay = self._attack_delay(attack)
                elif self.research_attack == "joint_random":
                    delay = int(self.attack_delay_rng.integers(
                        0, int(self.option.get("byz_attack_max_delay", 6)) + 1))
                elif self.research_attack == "timed_ipm":
                    delay = int(self.option.get("byz_attack_max_delay", 6))
            response["__t"][index] = self.gv.clock.current_time + delay
        return response

    def _ordinary_delay(self):
        low = int(self.option.get("byz_delay_min", 0))
        high = int(self.option.get("byz_delay_max", 3))
        if low < 0 or high < low:
            raise ValueError("invalid delay bounds")
        return int(self.delay_rng.integers(low, high + 1))

    def _malicious_update(self, benign, base, total, malicious_count):
        if self.research_attack in {"alie", "ipm", "timed_ipm"}:
            if not benign:
                reference = self.byz_history if self.byz_history is not None else base * 0
                return -float(self.option.get("byz_attack_scale", 1.0)) * reference
            name = "alie" if self.research_attack == "alie" else "ipm"
            if name == "alie" and len(benign) < 2:
                return -float(self.option.get("byz_attack_scale", 1.0)) * benign[0]
            return _attack_update(name, benign, total, malicious_count, self.option)
        direction = self.byz_history
        if direction is None:
            direction = clipped_mean(benign) if benign else torch.ones_like(base)
        scale = float(self.option.get("byz_attack_scale", 1.0))
        magnitude = torch.stack([v.norm() for v in benign]).median() if benign else direction.norm()
        return -scale * magnitude * direction / direction.norm().clamp_min(1e-12)

    def _attack_delay(self, attack):
        """White-box timing choice from a linear history extrapolation."""
        max_delay = int(self.option.get("byz_attack_max_delay", 6))
        if max_delay < 0:
            raise ValueError("attack delay budget must be nonnegative")
        if self.byz_history is None or self.byz_previous_history is None:
            return max_delay
        momentum = self.byz_history - self.byz_previous_history
        scores = [cosine(attack, self.byz_history + (d + 1) * momentum)
                  for d in range(max_delay + 1)]
        return int(np.argmin(scores))

    def _root_reference(self):
        if self.byz_root is None:
            return None
        loader = self.calculator.get_dataloader(
            self.byz_root, batch_size=min(len(self.byz_root),
                                           int(self.option.get("byz_root_batch", 32))),
            shuffle=False)
        self.model.zero_grad()
        was_training = self.model.training
        # Gradients still flow in eval mode, while BatchNorm buffers stay fixed.
        self.model.eval()
        for batch in loader:
            loss = self.calculator.compute_loss(self.model, batch)["loss"]
            (loss * (len(batch[-1]) / len(self.byz_root))).backward()
        gradient = torch.cat([p.grad.detach().reshape(-1) for p in self.model.parameters()])
        self.model.zero_grad()
        self.model.train(was_training)
        return gradient

    def package_handler(self, packages: dict):
        ids = packages.get("__cid", [])
        if not ids:
            return False
        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)
        server_start = perf_counter()
        now = self.gv.clock.current_time
        updates = []
        max_stale = int(self.option.get("byz_max_staleness", 4))
        for cid, model, version in zip(ids, packages["model"], packages["byz_version"]):
            version = int(version)
            if version not in self.byz_snapshots or self.current_round - version > max_stale:
                continue
            vector = self.byz_snapshots[version] - _parameter_vector(model).to(self.device)
            if torch.isfinite(vector).all().item():
                updates.append(Update(int(cid), vector, version, now))
        if not updates:
            self.byz_last_round = {"received": len(ids), "used": 0, "stale_dropped": len(ids)}
            return False
        peer = torch.stack([u.vector for u in updates]).median(dim=0).values
        root = self._root_reference() if self.research_mode in {"root_only", "root_fusion"} else None
        reference, root_weight = reference_fusion(root, self.byz_history, peer)
        decisions = {u.client_id: "accepted" for u in updates}
        detail = {}
        if self.research_mode == "triage":
            selected, decisions = self.byz_triage.process(updates, reference, self.current_round)
            if not selected:
                # An asynchronous server must eventually advance.  A bounded
                # projected fallback avoids deadlock when every reply is deferred.
                selected = [project_conflict(u.vector, reference) for u in updates]
                decisions.update({u.client_id: "fallback" for u in updates})
                for update in updates:
                    self.byz_triage.pending.pop(update.client_id, None)
            aggregate = clipped_mean(selected)
        elif self.research_mode == "root_only":
            aggregate = root_align([u.vector for u in updates], root)
            root_weight = 1.0
        elif self.research_mode == "root_fusion":
            aggregate = root_align([u.vector for u in updates], reference)
        elif self.research_mode == "anytime":
            aggregate, detail = self.byz_anytime.aggregate(
                updates, reference, self.byz_triage, self.current_round)
            decisions = detail["decisions"]
        else:
            name = str(self.option.get("byz_aggregator", "avg"))
            f = int(self.option.get("byz_assumed_count", 0))
            key = (name, len(updates), f)
            if self.byz_aggregator_key != key:
                self.byz_aggregator = _build_aggregator(name, len(updates), f, self.option)
                self.byz_aggregator_key = key
            aggregate = self.byz_aggregator([u.vector for u in updates])
        if aggregate is None:
            self.byz_last_round = {"received": len(ids), "used": 0,
                                   "decisions": decisions}
            return False
        self.model = _model_from_update(self.model, aggregate)
        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)
        server_ms = (perf_counter() - server_start) * 1000
        self.byz_previous_history = self.byz_history
        self.byz_history = aggregate.detach().clone()
        valid_versions = {version for version in self.byz_snapshots
                          if self.current_round - version <= max_stale + 1}
        self.byz_snapshots = {version: value for version, value in self.byz_snapshots.items()
                              if version in valid_versions}
        false_reject = sum(cid not in self.byz_malicious_ids and choice == "rejected"
                           for cid, choice in decisions.items())
        benign_deferred = sum(cid not in self.byz_malicious_ids and choice == "deferred"
                              for cid, choice in decisions.items())
        benign_decisions = sum(cid not in self.byz_malicious_ids for cid in decisions)
        minority_false_reject = sum(cid in self.byz_minority_ids and choice == "rejected"
                                    for cid, choice in decisions.items())
        minority_deferred = sum(cid in self.byz_minority_ids and choice == "deferred"
                                for cid, choice in decisions.items())
        minority_decisions = sum(cid in self.byz_minority_ids for cid in decisions)
        self.byz_last_round = {
            "received": len(ids), "used": len(updates),
            "malicious": sum(u.client_id in self.byz_malicious_ids for u in updates),
            "staleness": [max(0, self.current_round - u.sent_round) for u in updates],
            "decisions": decisions, "false_reject": false_reject,
            "benign_deferred": benign_deferred,
            "benign_decisions": benign_decisions,
            "minority_false_reject": minority_false_reject,
            "minority_deferred": minority_deferred,
            "minority_decisions": minority_decisions,
            "root_weight": root_weight, **detail,
            "server_ms": server_ms,
        }
        return True

    def backdoor_asr(self):
        dataset = self.byz_triggered_test
        if dataset is None:
            return None
        if not len(dataset):
            return None
        return self.calculator.test(self.model, dataset,
                                    batch_size=min(128, len(dataset)),
                                    num_workers=0)["accuracy"]


class Client(_fedbase.BasicClient):
    def reply(self, server_package):
        self.byz_backdoor = bool(server_package["byz_backdoor"])
        self.byz_target = int(server_package["byz_target"])
        self.byz_trigger_size = int(server_package["byz_trigger_size"])
        result = super().reply(server_package)
        result["byz_version"] = int(server_package["byz_version"])
        return result

    def train(self, model):
        if not getattr(self, "byz_backdoor", False):
            return super().train(model)
        model.train()
        optimizer = self.calculator.get_optimizer(
            model, lr=self.learning_rate, weight_decay=self.weight_decay,
            momentum=self.momentum)
        for _ in range(self.num_steps):
            images, labels = self.get_batch_data()
            images, labels = images.clone(), labels.clone()
            affected = max(1, len(labels) // 2)
            images[:affected] = _trigger(images[:affected], self.byz_trigger_size)
            labels[:affected] = self.byz_target
            model.zero_grad()
            loss = self.calculator.compute_loss(model, (images, labels))["loss"]
            loss.backward()
            if self.clip_grad > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), self.clip_grad)
            optimizer.step()
