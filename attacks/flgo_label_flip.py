"""Deterministic cyclic training-label flip for FLGo malicious clients."""

import torch
from torch.utils.data import Dataset


class LabelFlippedDataset(Dataset):
    def __init__(self, source, num_classes):
        if source is None or type(num_classes) is not int or num_classes < 2:
            raise ValueError("label flip requires training data and at least two classes")
        self.source = source
        self.num_classes = num_classes

    def __len__(self):
        return len(self.source)

    def __getitem__(self, index):
        sample = self.source[index]
        if not isinstance(sample, (tuple, list)) or len(sample) < 2:
            raise ValueError("label flip requires labeled samples")
        label = sample[-1]
        flipped = (int(label) + 1) % self.num_classes
        if isinstance(label, torch.Tensor):
            flipped = label.new_tensor(flipped)
        return (*sample[:-1], flipped)
