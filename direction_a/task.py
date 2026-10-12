"""Offline, immutable CIFAR-LT index manifests with an independent audit.

This task format is A-specific; it is not an easyFL task loader. No framework
partitioner, root data, model, registration event, or training is initialized.
"""

import hashlib
import math
import pickle
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class TaskSpec:
    dataset: str
    identity: str
    classes: int
    clients: int
    head_count: int
    validation_per_class: int
    test_per_class: int
    seed: int = 20261012
    imbalance_factor: int = 100
    alpha: float = 0.1


class CIFARSource:
    def __init__(self, root, dataset, budget):
        self.dataset = dataset
        self.classes = 10 if dataset == "CIFAR10" else 100
        root = Path(root) / dataset
        if dataset == "CIFAR10":
            folder = root / "cifar-10-batches-py"
            train_files = [folder / f"data_batch_{i}" for i in range(1, 6)]
            test_files = [folder / "test_batch"]
            label_key = b"labels"
        elif dataset == "CIFAR100":
            folder = root / "cifar-100-python"
            train_files, test_files = [folder / "train"], [folder / "test"]
            label_key = b"fine_labels"
        else:
            raise ValueError(dataset)
        self.file_hashes = {}

        def read(files, split):
            labels, images = [], []
            for path in files:
                budget.check()
                raw = path.read_bytes()
                self.file_hashes[str(path.resolve())] = sha256_bytes(raw)
                batch = pickle.loads(raw, encoding="bytes")
                labels.extend(batch[label_key])
                images.append(batch[b"data"])
            labels = np.asarray(labels, dtype=np.int64)
            images = np.concatenate(images).reshape(-1, 3, 32, 32)
            budget.scan(f"{dataset}:{split}:source_label_count")
            expected_size = 50000 if split == "train" else 10000
            expected_per_class = expected_size // self.classes
            assert len(labels) == len(images) == expected_size, "official source size"
            assert labels.min() == 0 and labels.max() == self.classes - 1
            assert np.bincount(labels, minlength=self.classes).tolist() == [expected_per_class] * self.classes
            return labels, images

        self.train_labels, self.train_images = read(train_files, "train")
        self.test_labels, self.test_images = read(test_files, "test")


def lt_counts(head_count, classes, imbalance_factor):
    if classes < 2 or head_count < 1 or imbalance_factor < 1:
        raise ValueError("invalid LT configuration")
    return [max(1, math.floor(head_count * imbalance_factor ** (-c / (classes - 1))))
            for c in range(classes)]


def apportion(count, probabilities):
    probabilities = np.asarray(probabilities, dtype=np.float64)
    if count < 0 or probabilities.ndim != 1 or len(probabilities) == 0:
        raise ValueError("invalid apportionment")
    if np.any(probabilities < 0) or not np.isfinite(probabilities).all():
        raise ValueError("invalid probability")
    probabilities = probabilities / probabilities.sum()
    shares = count * probabilities
    allocation = np.floor(shares).astype(np.int64)
    remainder = count - int(allocation.sum())
    order = sorted(range(len(shares)), key=lambda i: (-(shares[i] - allocation[i]), i))
    for i in order[:remainder]:
        allocation[i] += 1
    return allocation


def class_groups(counts):
    """Descending training counts; ties use class ID; rank thirds."""
    order = sorted(range(len(counts)), key=lambda c: (-counts[c], c))
    first, second = len(order) // 3, 2 * len(order) // 3
    return {"head": order[:first], "middle": order[first:second], "tail": order[second:]}


def build_task(source, spec, budget):
    if source.classes != spec.classes or source.dataset != spec.dataset:
        raise ValueError("source/spec mismatch")
    rng = np.random.Generator(np.random.PCG64(spec.seed))
    train = [[] for _ in range(spec.clients)]
    client_test = [[] for _ in range(spec.clients)]
    validation, selected_test = [], []
    target = lt_counts(spec.head_count, spec.classes, spec.imbalance_factor)
    dirichlet_draws = []
    for c in range(spec.classes):
        budget.scan(f"{spec.identity}:select_train_class:{c}")
        indices = rng.permutation(np.flatnonzero(source.train_labels == c))
        v = spec.validation_per_class
        if v + target[c] > len(indices):
            raise ValueError(f"insufficient class {c}")
        validation.extend(indices[:v].tolist())
        chosen = indices[v:v + target[c]]
        probs = rng.dirichlet(np.full(spec.clients, spec.alpha))
        dirichlet_draws.append(probs.tolist())
        amounts = apportion(len(chosen), probs)
        start = 0
        for i, amount in enumerate(amounts):
            train[i].extend(chosen[start:start + int(amount)].tolist())
            start += int(amount)
        budget.scan(f"{spec.identity}:select_test_class:{c}")
        tests = rng.permutation(np.flatnonzero(source.test_labels == c))[:spec.test_per_class].tolist()
        if len(tests) != spec.test_per_class:
            raise ValueError("insufficient test")
        selected_test.extend(tests)
        for j, index in enumerate(tests):
            client_test[j % spec.clients].append(index)
    budget.scan(f"{spec.identity}:discarded_index_complement")
    used = set(validation) | {j for part in train for j in part}
    data = {"index_namespaces": {"train": "official_train", "validation": "official_train",
                                 "test": "official_test"},
            "clients": [{"id": f"client_{i:03d}", "train": sorted(train[i]),
                         "test": sorted(client_test[i])} for i in range(spec.clients)],
            "validation": sorted(validation), "global_test": sorted(selected_test),
            "discarded_official_train": sorted(set(range(len(source.train_labels))) - used),
            "unused_official_test": sorted(set(range(len(source.test_labels))) - set(selected_test))}
    budget.scan(f"{spec.identity}:training_count_matrix")
    matrix = [np.bincount(source.train_labels[part], minlength=spec.classes).tolist() for part in train]
    groups = class_groups(target)
    support = np.count_nonzero(np.asarray(matrix), axis=0).tolist()
    counts = {"n_ic": matrix, "N_c": target, "sources_per_class": support,
              "a_ic": (np.asarray(matrix) / np.asarray(target)[None, :]).tolist(),
              "zero_source_classes": [c for c, n in enumerate(support) if n == 0],
              "single_source_classes": [c for c, n in enumerate(support) if n == 1],
              "multi_source_classes": [c for c, n in enumerate(support) if n > 1],
              "missing_classes_by_client": [[c for c, n in enumerate(row) if n == 0] for row in matrix],
              "empty_train_clients": [i for i, row in enumerate(matrix) if sum(row) == 0],
              "class_groups": groups,
              "tail_holding_clients": [i for i, row in enumerate(matrix) if sum(row[c] for c in groups["tail"]) > 0]}
    info = {"spec": asdict(spec), "source_file_sha256": source.file_hashes,
            "source_sizes": {"official_train": len(source.train_labels), "official_test": len(source.test_labels)},
            "label_mapping": {str(c): c for c in range(spec.classes)},
            "partitioner": "direction_a.task: PCG64; per-class symmetric Dirichlet; largest remainder",
            "dirichlet_parameter_vector": [spec.alpha] * spec.clients,
            "dirichlet_draws_by_class": dirichlet_draws,
            "if_formula": "max(1,floor(H*IF**(-c/(C-1)))) on final training pool",
            "actual_training_if": max(target) / min(target),
            "test_rule": "class-stratified official_test round-robin, independent of training",
            "validation_rule": "global class-balanced official_train holdout; no client validation duplication",
            "allowed_overlap": "global_test is exactly the union of client test views",
            "state": "smoke" if "smoke" in spec.identity else "full_size_candidate_pending_review"}
    return info, data, counts


def audit_task(source, spec, data, counts, budget):
    """Use set algebra and scalar Counters, not the generation bin-count path."""
    budget.scan(f"{spec.identity}:independent_index_and_count_audit")
    clients = data["clients"]
    assert len(clients) == spec.clients
    assert [p["id"] for p in clients] == [f"client_{i:03d}" for i in range(spec.clients)]

    def unique(indices, size):
        assert len(indices) == len(set(indices)), "duplicate index"
        assert all(type(j) is int and 0 <= j < size for j in indices), "index domain"
        return set(indices)

    train_parts = [unique(p["train"], len(source.train_labels)) for p in clients]
    test_parts = [unique(p["test"], len(source.test_labels)) for p in clients]
    validation = unique(data["validation"], len(source.train_labels))
    discarded = unique(data["discarded_official_train"], len(source.train_labels))
    global_test = unique(data["global_test"], len(source.test_labels))
    unused_test = unique(data["unused_official_test"], len(source.test_labels))
    train_union = set().union(*train_parts)
    test_union = set().union(*test_parts)
    assert sum(map(len, train_parts)) == len(train_union), "client train overlap"
    assert sum(map(len, test_parts)) == len(test_union), "client test overlap"
    assert train_union.isdisjoint(validation) and train_union.isdisjoint(discarded)
    assert validation.isdisjoint(discarded)
    assert train_union | validation | discarded == set(range(len(source.train_labels)))
    assert test_union == global_test and global_test.isdisjoint(unused_test)
    assert global_test | unused_test == set(range(len(source.test_labels)))
    scalar_matrix = [[sum(int(source.train_labels[j]) == c for j in part) for c in range(spec.classes)]
                     for part in train_parts]
    overall = Counter(int(source.train_labels[j]) for j in train_union)
    N_c = [overall[c] for c in range(spec.classes)]
    assert scalar_matrix == counts["n_ic"]
    assert len(counts["n_ic"]) == spec.clients and all(len(row) == spec.classes for row in counts["n_ic"])
    assert N_c == counts["N_c"]
    assert [sum(row[c] for row in scalar_matrix) for c in range(spec.classes)] == N_c
    # Algebraically independent formulation of the requested exponential schedule.
    expected = [max(1, math.floor(math.exp(math.log(spec.head_count) - c * math.log(spec.imbalance_factor) / (spec.classes - 1)) + 1e-9))
                for c in range(spec.classes)]
    assert N_c == expected and N_c[0] == spec.head_count and N_c[-1] == max(1, spec.head_count // spec.imbalance_factor)
    validation_counts = Counter(int(source.train_labels[j]) for j in validation)
    test_counts = Counter(int(source.test_labels[j]) for j in global_test)
    assert [validation_counts[c] for c in range(spec.classes)] == [spec.validation_per_class] * spec.classes
    assert [test_counts[c] for c in range(spec.classes)] == [spec.test_per_class] * spec.classes
    client_test_counts = [[sum(int(source.test_labels[j]) == c for j in part) for c in range(spec.classes)] for part in test_parts]
    assert all(row == [spec.test_per_class // spec.clients] * spec.classes for row in client_test_counts)
    sources = [sum(row[c] > 0 for row in scalar_matrix) for c in range(spec.classes)]
    assert sources == counts["sources_per_class"]
    assert counts["zero_source_classes"] == [c for c in range(spec.classes) if sources[c] == 0]
    assert counts["single_source_classes"] == [c for c in range(spec.classes) if sources[c] == 1]
    assert counts["multi_source_classes"] == [c for c in range(spec.classes) if sources[c] >= 2]
    assert counts["missing_classes_by_client"] == [[c for c in range(spec.classes) if row[c] == 0] for row in scalar_matrix]
    for i, row in enumerate(scalar_matrix):
        assert all(abs(counts["a_ic"][i][c] - row[c] / N_c[c]) < 1e-15 for c in range(spec.classes))
    assert sorted(c for group in counts["class_groups"].values() for c in group) == list(range(spec.classes))
    return {"status": "data_pass", "independent_reference": "set conservation + scalar labels/Counter + exp/log LT formula",
            "train_total": len(train_union), "validation_total": len(validation), "test_total": len(global_test),
            "discarded_train_total": len(discarded), "unused_test_total": len(unused_test),
            "matrix_shape": [spec.clients, spec.classes], "training_class_counts": N_c,
            "client_train_totals": [sum(row) for row in scalar_matrix],
            "client_train_class_coverage": [sum(n > 0 for n in row) for row in scalar_matrix],
            "client_test_totals": list(map(len, test_parts)), "client_test_classes": [sum(n > 0 for n in row) for row in client_test_counts],
            "source_count_range": [min(sources), max(sources)], "zero_source_classes": counts["zero_source_classes"],
            "single_source_classes": counts["single_source_classes"], "multi_source_classes": counts["multi_source_classes"],
            "missing_client_class_pairs": sum(len(row) for row in counts["missing_classes_by_client"]),
            "actual_training_if": max(N_c) / min(N_c), "class_groups": counts["class_groups"],
            "theoretical_registration_count_bytes_int64": spec.clients * spec.classes * 8,
            "actual_registration_sent_bytes": None, "registration_status": "not_executed_in_0.2"}


def save_task(folder, source, spec, budget):
    info, data, counts = build_task(source, spec, budget)
    acceptance = audit_task(source, spec, data, counts, budget)
    folder = Path(folder)
    hashes = {}
    for name, value in (("data.json", data), ("counts.json", counts), ("acceptance.json", acceptance)):
        hashes[name] = sha256_bytes(budget.write_json(folder / name, value))
    info["artifact_sha256"] = hashes
    raw = budget.write_json(folder / "info.json", info)
    hashes["info.json"] = sha256_bytes(raw)
    # Re-read the exact persisted artifacts and audit those, not only RAM objects.
    import json
    stored_data = json.loads((folder / "data.json").read_text(encoding="utf-8"))
    stored_counts = json.loads((folder / "counts.json").read_text(encoding="utf-8"))
    assert audit_task(source, spec, stored_data, stored_counts, budget) == acceptance
    for name, digest in hashes.items():
        assert sha256_bytes((folder / name).read_bytes()) == digest
    return {"identity": spec.identity, "folder": str(folder), "sha256": hashes, "acceptance": acceptance}


class TaskReader:
    """Load sealed indices/counts by hashes, without repartitioning/recounting.

    Global test and client test are explicit views of the same source. A caller
    must supply the source bound by the recorded official pickle hashes.
    """

    def __init__(self, folder):
        import json
        self.folder = Path(folder)
        self.info = json.loads((self.folder / "info.json").read_text(encoding="utf-8"))
        for name, digest in self.info["artifact_sha256"].items():
            if sha256_bytes((self.folder / name).read_bytes()) != digest:
                raise ValueError(f"sealed task hash mismatch: {name}; return to checkpoint 0.2")
        self.data = json.loads((self.folder / "data.json").read_text(encoding="utf-8"))
        self.counts = json.loads((self.folder / "counts.json").read_text(encoding="utf-8"))

    def indices(self, split, client_id=None):
        if split == "validation" and client_id is None:
            return tuple(self.data["validation"])
        if split == "test" and client_id is None:
            return tuple(self.data["global_test"])
        if split in ("train", "test") and client_id is not None:
            for client in self.data["clients"]:
                if client["id"] == client_id:
                    return tuple(client[split])
            raise KeyError(client_id)
        raise ValueError("train requires a client ID; validation is global")

    def dataset_view(self, source, split, client_id=None):
        if source.file_hashes != self.info["source_file_sha256"]:
            raise ValueError("task/source identity mismatch")
        return IndexedDataset(source, self.indices(split, client_id), split)


class IndexedDataset:
    """PyTorch DataLoader-compatible view; lazy deterministic A transform."""

    def __init__(self, source, indices, split):
        self.source = source
        self.indices = tuple(indices)
        self.split = split

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, position):
        from direction_a.model import transform_images
        index = self.indices[position]
        images = self.source.test_images if self.split == "test" else self.source.train_images
        labels = self.source.test_labels if self.split == "test" else self.source.train_labels
        return transform_images(images[index:index + 1], self.source.dataset)[0], int(labels[index])
