"""Reuse the repository ResNet-8 backbone; expose raw logits and its head."""

import hashlib

import torch
import torch.nn.functional as F
from torch import nn

from models.ResNet import BasicBlock, ResNet_3Layer


NORMALIZATION = {
    "CIFAR10": ((0.4914, 0.4822, 0.4465), (0.247, 0.243, 0.262)),
    "CIFAR100": ((0.5071, 0.4867, 0.4408), (0.2675, 0.2565, 0.2761)),
}


def transform_images(images, dataset):
    """NCHW uint8 to deterministic float32 normalized RGB; no augmentation."""
    mean, std = NORMALIZATION[dataset]
    x = torch.as_tensor(images.copy(), dtype=torch.float32) / 255.0
    return (x - torch.tensor(mean)[None, :, None, None]) / torch.tensor(std)[None, :, None, None]


class ResNet8Adapter(ResNet_3Layer):
    feature_dim = 128

    def __init__(self, num_classes):
        if num_classes not in (10, 100):
            raise ValueError("A requires C=10 or C=100")
        super().__init__(BasicBlock, [1, 1, 1], norm=nn.BatchNorm2d, num_classes=num_classes)

    @property
    def head(self):
        # A property avoids duplicate module/state_dict registration.
        return self.linear

    def encode(self, x):
        x = F.relu(self.bn1(self.conv1(x)))
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = F.avg_pool2d(x, x.size(3))
        return x.reshape(x.size(0), self.feature_dim)

    def forward(self, x):
        # Keep a complete path for independent split-path comparison.
        x = F.relu(self.bn1(self.conv1(x)))
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = F.avg_pool2d(x, x.size(3))
        return self.linear(x.reshape(x.size(0), -1))

    def freeze_reference(self):
        self.eval()
        self.requires_grad_(False)
        return self

    def state_identity(self):
        digest = hashlib.sha256()
        for name, value in self.state_dict().items():
            value = value.detach().cpu().contiguous()
            digest.update(f"{name}:{value.dtype}:{tuple(value.shape)}".encode())
            digest.update(value.numpy().tobytes())
        return digest.hexdigest()
