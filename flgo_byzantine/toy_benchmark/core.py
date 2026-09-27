import json
from pathlib import Path

import torch

from flgo.benchmark.toolkits.cv.classification import (
    FromDatasetGenerator, FromDatasetPipe, GeneralCalculator,
)


def _dataset(size, seed):
    generator = torch.Generator().manual_seed(seed)
    x = torch.randn(size, 2, generator=generator)
    y = (x[:, 0] + 0.7 * x[:, 1] > 0).long()
    return torch.utils.data.TensorDataset(x, y)


TRAIN_DATA = _dataset(320, 5)
TEST_DATA = _dataset(80, 6)


class TaskGenerator(FromDatasetGenerator):
    def __init__(self):
        super().__init__(benchmark="flgo_byzantine.toy_benchmark",
                         train_data=TRAIN_DATA, test_data=TEST_DATA)

    def partition(self):
        # FLGo seeds torch with 12 + the task seed before creating this generator.
        self.root_seed = torch.initial_seed()
        order = torch.randperm(len(self.train_data),
                               generator=torch.Generator().manual_seed(self.root_seed)).tolist()
        root_count = max(1, len(order) // 10)
        self.root_indices = sorted(order[:root_count])
        self.client_pool_indices = sorted(order[root_count:])
        client_pool = torch.utils.data.Subset(self.train_data, self.client_pool_indices)
        relative_parts = self.partitioner(client_pool)
        self.local_datas = [[self.client_pool_indices[int(i)] for i in part]
                            for part in relative_parts]
        self.num_clients = len(self.local_datas)


class TaskPipe(FromDatasetPipe):
    def __init__(self, task_path):
        super().__init__(task_path, train_data=TRAIN_DATA, test_data=TEST_DATA)

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
