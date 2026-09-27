"""Load a task's pre-isolated trusted samples through its FLGo task pipe."""

import hashlib
import json
from pathlib import Path

import torch


def load_root_data(task_path, task_pipe_class):
    task_path = Path(task_path)
    info = json.loads((task_path / "info").read_text(encoding="utf-8"))
    metadata = info.get("root_data")
    if not isinstance(metadata, dict) or metadata.get("source") != "benchmark_train":
        raise ValueError("task has no supported pre-isolated root data")

    pipe = task_pipe_class(str(task_path))
    source = pipe.train_data
    if source is None:
        raise ValueError("task pipe has no benchmark training dataset")
    size = len(source)
    root = metadata.get("root_indices")
    pool = metadata.get("client_pool_indices")
    if metadata.get("source_size") != size or not isinstance(root, list) or not root:
        raise ValueError("root data metadata has an invalid source or empty root set")
    if not isinstance(pool, list):
        raise ValueError("root data metadata has no client pool")
    for indices in (root, pool):
        if any(type(i) is not int or i < 0 or i >= size for i in indices):
            raise ValueError("root data contains an out-of-range index")
        if len(indices) != len(set(indices)):
            raise ValueError("root data contains duplicate indices")
    if set(root) & set(pool) or len(root) + len(pool) != size:
        raise ValueError("root and client training pools must partition the source")
    clients = pipe.feddata["client_names"]
    client_indices = [i for name in clients for i in pipe.feddata[name]["data"]]
    if set(client_indices) != set(pool) or len(client_indices) != len(pool):
        raise ValueError("saved client partitions do not match the root metadata")

    identity = hashlib.sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest()
    return torch.utils.data.Subset(source, root), identity
