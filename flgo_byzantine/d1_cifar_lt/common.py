"""CIFAR-LT benchmark support; root selection precedes long-tail thinning."""

from __future__ import annotations

import json
from pathlib import Path

import flgo.benchmark
import numpy as np
import torch
import torchvision
from flgo.benchmark.toolkits.cv.classification import (
    FromDatasetGenerator, FromDatasetPipe, GeneralCalculator,
)


TRANSFORM = torchvision.transforms.Compose([
    torchvision.transforms.ToTensor(),
    torchvision.transforms.Normalize((0.4914, 0.4822, 0.4465),
                                     (0.247, 0.243, 0.262)),
])


def dataset(name: str, train: bool):
    cls = torchvision.datasets.CIFAR10 if name == "CIFAR10" else torchvision.datasets.CIFAR100
    path = Path(flgo.benchmark.data_root) / name
    return cls(root=str(path), train=train, download=True, transform=TRANSFORM)


class LTGenerator(FromDatasetGenerator):
    def __init__(self, benchmark: str, name: str, missing_fraction: float, seed: int):
        if missing_fraction not in (0.0, 0.2):
            raise ValueError("D1 full supports only full or 20% missing root coverage")
        self.name = name
        self.num_classes = 10 if name == "CIFAR10" else 100
        self.missing_fraction = missing_fraction
        self.root_seed = int(seed) + 12001
        super().__init__(benchmark=benchmark, train_data=dataset(name, True),
                         test_data=dataset(name, False))

    def partition(self):
        labels = np.asarray(self.train_data.targets)
        rng = np.random.default_rng(self.root_seed)
        missing = int(self.num_classes * self.missing_fraction)
        # The highest-numbered classes are the predeclared, least frequent tail.
        covered = list(range(self.num_classes - missing))
        root, pool = [], []
        max_count = 4000 if self.num_classes == 10 else 400
        targets = [max(1, int(round(max_count * 50 ** (-c / (self.num_classes - 1)))))
                   for c in range(self.num_classes)]
        minimum = 20 if self.num_classes == 10 else 10
        root_counts = {c: minimum for c in covered}
        remaining = 2000 - minimum * len(covered)
        weights = np.asarray([targets[c] for c in covered], dtype=float)
        shares = remaining * weights / weights.sum()
        allocated = np.floor(shares).astype(int)
        for c, amount in zip(covered, allocated):
            root_counts[c] += int(amount)
        for j in np.argsort(-(shares - allocated))[:remaining - int(allocated.sum())]:
            root_counts[covered[int(j)]] += 1
        for label in range(self.num_classes):
            indices = rng.permutation(np.flatnonzero(labels == label)).tolist()
            count = root_counts.get(label, 0)
            if len(indices) - count < targets[label]:
                raise ValueError(f"class {label} cannot supply root plus LT pool")
            root.extend(indices[:count])
            pool.extend(indices[count:count + targets[label]])
        self.root_indices = sorted(root)
        self.client_pool_indices = sorted(pool)
        used = set(root) | set(pool)
        self.discarded_indices = [i for i in range(len(labels)) if i not in used]
        self.lt_counts = targets
        self.root_counts = [root_counts.get(c, 0) for c in range(self.num_classes)]
        subset = torch.utils.data.Subset(self.train_data, self.client_pool_indices)
        relative = self.partitioner(subset)
        self.local_datas = [[self.client_pool_indices[int(j)] for j in part]
                            for part in relative]
        self.num_clients = len(self.local_datas)


class LTPipe(FromDatasetPipe):
    def __init__(self, task_path: str, name: str):
        super().__init__(task_path, train_data=dataset(name, True),
                         test_data=dataset(name, False))

    def save_info(self, generator):
        super().save_info(generator)
        path = Path(self.task_path) / "info"
        info = json.loads(path.read_text(encoding="utf-8"))
        info["root_data"] = {
            "source": "benchmark_train",
            "source_size": len(generator.train_data),
            "seed": generator.root_seed,
            "root_indices": generator.root_indices,
            "client_pool_indices": generator.client_pool_indices,
            "discarded_indices": generator.discarded_indices,
            "lt_counts": generator.lt_counts,
            "root_counts": generator.root_counts,
            "root_scheme": "lt_proportional_minimum_v2",
            "imbalance_ratio": 50,
            "missing_fraction": generator.missing_fraction,
        }
        path.write_text(json.dumps(info), encoding="utf-8")


TaskCalculator = GeneralCalculator
