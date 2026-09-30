"""Isolated FLGo algorithm for the D1 full-study attacks and controls."""

from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

from aggregators.d1_reference_baselines import RootBaseline
from attacks.d1_full_attacks import FixedTriggerDataset, root_constrained_update
from attacks.flgo_label_flip import LabelFlippedDataset
from .algorithm import (AggregationContext, Client as BridgeClient,
                        Server as BridgeServer,
                        _build_aggregator, _model_from_update, _parameter_vector)
from .root_data import load_root_data


METHODS = frozenset({"avg", "d1", "fltrust", "brdrag", "flest",
                     "balanced_brdrag", "balanced_splice"})
ATTACKS = frozenset({"none", "label_flip", "adaptive_root", "backdoor"})
ROOT_METHODS = METHODS - {"avg"}


class Server(BridgeServer):
    def initialize(self):
        self.byz_aggregator = str(self.option["byz_aggregator"])
        self.byz_attack = str(self.option["byz_attack"])
        if self.byz_aggregator not in METHODS or self.byz_attack not in ATTACKS:
            raise ValueError("unsupported D1 full method or attack")
        ratio = float(self.option.get("byz_malicious_fraction", 0))
        if ratio not in (0, 0.1, 0.3, 0.6):
            raise ValueError("unexpected full-study malicious fraction")
        rng = np.random.default_rng(int(self.option["byz_seed"]))
        count = int(ratio * self.num_clients) if self.byz_attack != "none" else 0
        self.byz_malicious_ids = frozenset(int(x) for x in rng.choice(self.num_clients, count, replace=False))
        self.byz_assumed_count = 0
        self.byz_last_round = {}
        self._byz_aggregator_instance = None
        self._byz_root_data = None
        self._byz_root_identity = None
        self._byz_context = None
        self.full_round_stats = []
        self._tail_client_ids = None
        self._attacker_samples = None
        self._attacker_samples_raw_count = None

    def _load_context(self):
        if self._byz_root_data is None:
            self._byz_root_data, self._byz_root_identity = load_root_data(
                self.task, self.gv.TaskPipe)
        if self._byz_context is None:
            self._byz_context = AggregationContext(
                self.model, self.device, self.calculator, self._byz_root_data)
        else:
            self._byz_context.model = self.model
        if self._tail_client_ids is None:
            info = json.loads(open(f"{self.task}/info", encoding="utf-8").read())
            data = json.loads(open(f"{self.task}/data.json", encoding="utf-8").read())
            counts = info["root_data"]["lt_counts"]
            n_tail = max(1, len(counts) // 5)
            tail = set(sorted(range(len(counts)), key=lambda c: counts[c])[:n_tail])
            source = self._byz_root_data.dataset
            pool = info["root_data"]["client_pool_indices"]
            global_share = sum(int(source.targets[i] in tail) for i in pool) / len(pool)
            self._tail_client_ids = frozenset(
                cid for cid, name in enumerate(data["client_names"])
                if sum(int(source.targets[i] in tail) for i in data[name]["data"])
                / len(data[name]["data"]) > global_share)
            self.full_tail_classes = sorted(tail)
            self.full_tail_client_definition = "local tail fraction > global LT pool tail fraction"

    def _root_train_indices(self):
        buckets = defaultdict(list)
        for i in range(len(self._byz_root_data)):
            buckets[int(self._byz_root_data[i][-1])].append(i)
        generator = torch.Generator().manual_seed(int(self.option["byz_seed"]))
        extra = ((len(self._byz_root_data) + 1) // 2
                 - sum(len(indices) // 2 for indices in buckets.values()))
        train = []
        for label in range(int(self.option["byz_d1_num_classes"])):
            indices = buckets[label]
            cut = len(indices) // 2
            if len(indices) % 2 and extra:
                cut += 1
                extra -= 1
            train.extend(indices[j] for j in torch.randperm(
                len(indices), generator=generator)[:cut].tolist())
        return train

    def _owned_tail_samples(self):
        if self._attacker_samples is None:
            info = json.loads(open(f"{self.task}/data.json", encoding="utf-8").read())
            source = self._byz_root_data.dataset
            selected = []
            for cid in sorted(self.byz_malicious_ids):
                name = info["client_names"][cid]
                selected.extend(i for i in info[name]["data"]
                                if int(source.targets[i]) in self.full_tail_classes)
            self._attacker_samples_raw_count = len(selected)
            selected = selected[:64]
            self._attacker_samples = [source[i] for i in selected]
        return self._attacker_samples

    def _aggregator(self):
        if self._byz_aggregator_instance is None:
            name = self.byz_aggregator
            if name in {"avg", "d1"}:
                self._byz_aggregator_instance = _build_aggregator(
                    name, 20, 0, self.option, self._byz_context)
            else:
                self._byz_aggregator_instance = RootBaseline(
                    self._byz_context, int(self.option["byz_d1_num_classes"]), name,
                    seed=int(self.option["byz_seed"]),
                    root_step=float(self.option.get("byz_d1_root_step", 0.1)),
                    batch_size=int(self.option.get("byz_d1_batch_size", 64)),
                    drag_strength=float(self.option.get("byz_d1_drag_strength", 0.5)))
        return self._byz_aggregator_instance

    def _write_diagnostic(self, attack, instance):
        output_dir = self.option.get("byz_diagnostic_output_dir")
        if output_dir is None:
            output_dir = Path(self.gv.logger.get_output_path()).parent
        path = Path(output_dir) / "diagnostic_log.jsonl"
        record = {
            "schema_version": 1, "round": len(self.full_round_stats),
            "seed": int(self.option["byz_seed"]), "method": self.byz_aggregator,
            "attack_name": self.byz_attack,
            "received_client_ids": [int(cid) for cid in self.received_clients],
            "malicious_client_ids": [int(cid) for cid in self.received_clients
                                     if cid in self.byz_malicious_ids],
            "attack_called": attack is not None, "attack": attack,
            "d1": instance.last_diagnostics if self.byz_aggregator == "d1" else None,
        }
        nonfinite_fields = []

        def finite_json(value, location):
            if isinstance(value, float) and not math.isfinite(value):
                nonfinite_fields.append(location)
                return None
            if isinstance(value, dict):
                return {key: finite_json(item, f"{location}.{key}") for key, item in value.items()}
            if isinstance(value, (list, tuple)):
                return [finite_json(item, f"{location}[{index}]") for index, item in enumerate(value)]
            return value

        record = finite_json(record, "record")
        record["nonfinite_fields"] = nonfinite_fields
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")

    def aggregate(self, models: list, *args, **kwargs):
        if len(models) != len(self.received_clients):
            raise ValueError("received client IDs and models differ")
        self._load_context()
        base = _parameter_vector(self.model)
        updates = [base - _parameter_vector(model).to(base) for model in models]
        if any(not torch.isfinite(x).all() for x in updates):
            raise ValueError("non-finite client update")
        malicious = [i for i, cid in enumerate(self.received_clients)
                     if cid in self.byz_malicious_ids]
        benign_positions = [i for i in range(len(updates)) if i not in malicious]
        benign = [updates[i] for i in benign_positions]
        adaptive_zero = False
        attack_diagnostics = None
        if malicious and self.byz_attack == "adaptive_root":
            attack_diagnostics = {}
            crafted = root_constrained_update(
                benign, self._byz_context, self._owned_tail_samples(),
                self._root_train_indices(),
                batch_size=int(self.option.get("byz_d1_batch_size", 64)),
                diagnostics=attack_diagnostics)
            attack_diagnostics["attacker_samples_raw_count"] = self._attacker_samples_raw_count
            adaptive_zero = crafted.norm().item() <= 1e-12
            for i in malicious:
                updates[i] = crafted.clone()
        start = time.perf_counter()
        instance = self._aggregator()
        aggregate = instance(updates)
        if self.byz_aggregator == "d1":
            if (instance.last_stats.get("root_train_count") != 1000
                    or instance.last_stats.get("root_audit_count") != 1000):
                raise AssertionError("D1 root training/audit split must be 1000/1000")
        elif self.byz_aggregator in ROOT_METHODS:
            if sum(len(v) for v in instance.train_indices.values()) != 1000:
                raise AssertionError("root baseline must train on exactly 1000 examples")
        root_seconds = time.perf_counter() - start if self.byz_aggregator != "avg" else 0.0
        if aggregate.shape != base.shape or not torch.isfinite(aggregate).all():
            raise ValueError("aggregator returned invalid update")
        weights = getattr(instance, "last_client_weights", None)
        if weights is None or len(weights) != len(updates):
            weights = [1.0 / len(updates)] * len(updates)
        tail_weights = [weights[i] for i in benign_positions
                        if self.received_clients[i] in self._tail_client_ids]
        other_weights = [weights[i] for i in benign_positions
                         if self.received_clients[i] not in self._tail_client_ids]
        tail_total = sum(tail_weights)
        ideal_tail = len(tail_weights) / len(updates)
        stats = {
            "received": len(updates), "malicious": len(malicious),
            "malicious_fraction": len(malicious) / len(updates),
            "aggregator": self.byz_aggregator, "attack": self.byz_attack,
            "root_compute_seconds": root_seconds,
            "tail_benign_mean_weight": (tail_total / len(tail_weights) if tail_weights else None),
            "other_benign_mean_weight": (sum(other_weights) / len(other_weights) if other_weights else None),
            "tail_benign_weight_loss": ideal_tail - tail_total,
            "tail_benign_count": len(tail_weights),
            "weight_kind": "coefficient_proxy" if self.byz_aggregator == "d1" else "explicit",
            "adaptive_zero_update": adaptive_zero,
        }
        if hasattr(instance, "get_attack_stats"):
            stats["aggregator_stats"] = instance.get_attack_stats()
        self.byz_last_round = stats
        self.full_round_stats.append(stats)
        self._write_diagnostic(attack_diagnostics, instance)
        return _model_from_update(self.model, aggregate)


class Client(BridgeClient):
    def initialize(self):
        if self.id not in self.server.byz_malicious_ids:
            return
        if self.server.byz_attack == "label_flip":
            self.set_data(LabelFlippedDataset(
                self.train_data, int(self.option["byz_label_flip_num_classes"])), "train")
        elif self.server.byz_attack == "backdoor":
            self.set_data(FixedTriggerDataset(self.train_data), "train")
