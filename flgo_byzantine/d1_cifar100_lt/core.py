"""Offline CIFAR-100-LT task, with a separately selected trusted root."""

from flgo_byzantine.d1_cifar_lt.common import LTGenerator, LTPipe, TaskCalculator

MISSING_FRACTION = 0.0
ROOT_SEED = 1


class TaskGenerator(LTGenerator):
    def __init__(self):
        super().__init__("flgo_byzantine.d1_cifar100_lt", "CIFAR100",
                         MISSING_FRACTION, ROOT_SEED)


class TaskPipe(LTPipe):
    def __init__(self, task_path):
        super().__init__(task_path, "CIFAR100")
