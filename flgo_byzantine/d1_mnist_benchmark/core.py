"""Use FLGo's MNIST task interfaces after reserving 200 root samples per class."""

import json
from pathlib import Path

import flgo.benchmark
import torch
import torchvision
from flgo.benchmark.toolkits.cv.classification import (
    FromDatasetGenerator, FromDatasetPipe, GeneralCalculator,
)


_DATA_ROOT = Path(flgo.benchmark.data_root) / "MNIST"
_TRANSFORM = torchvision.transforms.Compose([
    torchvision.transforms.ToTensor(),
    torchvision.transforms.Normalize((0.1307,), (0.3081,)),
])


def _mnist(train):
    # Explicitly prohibit a network download in this experimental adapter.
    return torchvision.datasets.MNIST(
        root=str(_DATA_ROOT), train=train, download=False, transform=_TRANSFORM)


class TaskGenerator(FromDatasetGenerator):
    def __init__(self):
        super().__init__(benchmark="flgo_byzantine.d1_mnist_benchmark",
                         train_data=_mnist(True), test_data=_mnist(False))

    def partition(self):
        labels = self.train_data.targets
        generator = torch.Generator().manual_seed(torch.initial_seed())
        self.root_seed = torch.initial_seed()
        root = []
        for label in range(10):
            available = torch.where(labels == label)[0]
            if len(available) < 200:
                raise ValueError(f"MNIST has fewer than 200 samples for class {label}")
            selected = available[torch.randperm(len(available), generator=generator)[:200]]
            root.extend(int(index) for index in selected)
        self.root_indices = sorted(root)
        root_set = set(self.root_indices)
        self.client_pool_indices = [index for index in range(len(self.train_data))
                                    if index not in root_set]
        pool = torch.utils.data.Subset(self.train_data, self.client_pool_indices)
        relative_parts = self.partitioner(pool)
        self.local_datas = [[self.client_pool_indices[int(index)] for index in part]
                            for part in relative_parts]
        self.num_clients = len(self.local_datas)


class TaskPipe(FromDatasetPipe):
    def __init__(self, task_path):
        super().__init__(task_path, train_data=_mnist(True), test_data=_mnist(False))

    def save_info(self, generator):
        super().save_info(generator)
        info_path = Path(self.task_path) / "info"
        info = json.loads(info_path.read_text(encoding="utf-8"))
        info["root_data"] = {
            "source": "benchmark_train",
            "seed": generator.root_seed,
            "source_size": len(generator.train_data),
            "root_indices": generator.root_indices,
            "client_pool_indices": generator.client_pool_indices,
        }
        info_path.write_text(json.dumps(info), encoding="utf-8")


TaskCalculator = GeneralCalculator
