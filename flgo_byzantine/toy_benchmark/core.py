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


class TaskPipe(FromDatasetPipe):
    def __init__(self, task_path):
        super().__init__(task_path, train_data=TRAIN_DATA, test_data=TEST_DATA)


TaskCalculator = GeneralCalculator
