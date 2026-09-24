from torch import nn

from flgo.utils.fmodule import FModule


class Model(FModule):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(2, 2)

    def forward(self, x):
        return self.linear(x)


def init_local_module(obj):
    pass


def init_global_module(obj):
    if obj.__class__.__name__.endswith("Server"):
        obj.model = Model().to(obj.device)
