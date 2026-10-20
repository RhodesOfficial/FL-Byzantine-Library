"""Metric denominators for the immutable A task; no model evaluation loop."""

import math

import numpy as np


def summarize(confusion, groups, client_correct, client_total, tail_holders, covered_classes):
    confusion = np.asarray(confusion, dtype=np.int64)
    C = len(confusion)
    if confusion.shape != (C, C) or np.any(confusion < 0):
        raise ValueError("invalid confusion matrix")
    total = confusion.sum(axis=1)
    recalls = [None if total[c] == 0 else float(confusion[c, c] / total[c]) for c in range(C)]

    def macro(classes):
        values = [recalls[c] for c in classes]
        return {"value": None if not values or any(v is None for v in values) else sum(values) / len(values),
                "class_denominator": len(classes), "missing_classes": [c for c in classes if recalls[c] is None]}

    client_correct, client_total = list(client_correct), list(client_total)
    if len(client_correct) != len(client_total) or any(n < 0 or k < 0 or k > n for k, n in zip(client_correct, client_total)):
        raise ValueError("invalid client counts")
    accuracy = [None if n == 0 else k / n for k, n in zip(client_correct, client_total)]
    k = max(1, math.ceil(0.1 * len(accuracy)))
    order = sorted(range(len(accuracy)), key=lambda i: (math.inf if accuracy[i] is None else accuracy[i], i))
    complete = bool(accuracy) and all(a is not None for a in accuracy)
    tail_complete = bool(tail_holders) and all(accuracy[i] is not None for i in tail_holders)
    return {"sample_accuracy": None if confusion.sum() == 0 else float(np.trace(confusion) / confusion.sum()),
            "sample_denominator": int(confusion.sum()), "recall_by_class": recalls,
            "macro_all_classes": macro(list(range(C))), "macro_covered_classes": macro(list(covered_classes)),
            "groups": {name: macro(classes) for name, classes in groups.items()},
            "client_accuracy": accuracy, "client_denominator": len(accuracy),
            "client_equal_mean": sum(accuracy) / len(accuracy) if complete else None,
            "worst_10_percent_count": k, "worst_10_percent_mean": sum(accuracy[i] for i in order[:k]) / k if complete else None,
            "minimum_client": min(accuracy) if complete else None,
            "tail_holder_denominator": len(tail_holders),
            "tail_holder_mean": sum(accuracy[i] for i in tail_holders) / len(tail_holders) if tail_complete else None,
            "missing_test_clients": [i for i, a in enumerate(accuracy) if a is None]}
