"""Isolated evaluator checks. Never imported or called by training processes."""
import inspect
import json
import math
from pathlib import Path
import random
import sys
from types import SimpleNamespace

from execute_diag import ROOT, OUT, PYTHON, BASELINE, make_logger
import numpy as np
import torch
from flgo.algorithm.fedbase import BasicServer
from flgo.benchmark.toolkits.cv.classification import GeneralCalculator


def snapshot():
    return (random.getstate(), np.random.get_state(), torch.get_rng_state().clone(),
            [s.clone() for s in torch.cuda.get_rng_state_all()])


def restore(states):
    random.setstate(states[0])
    np.random.set_state(states[1])
    torch.set_rng_state(states[2])
    torch.cuda.set_rng_state_all(states[3])


def equal(a, b):
    return {
        "python": a[0] == b[0],
        "numpy": (a[1][0] == b[1][0] and np.array_equal(a[1][1], b[1][1]) and a[1][2:] == b[1][2:]),
        "torch_cpu": torch.equal(a[2], b[2]),
        "torch_cuda_all": len(a[3]) == len(b[3]) and all(torch.equal(x, y) for x, y in zip(a[3], b[3])),
    }


def check(device):
    directory = OUT / "selftest" / device.type
    directory.mkdir(parents=True, exist_ok=True)
    baseline_file = next((BASELINE / "seed_101/record").glob("*.json"))
    options = json.loads(baseline_file.read_text(encoding="utf-8"))["option"]
    options = dict(options, no_log_console=True, log_file=False, test_batch_size=8)
    model = torch.nn.Linear(4, 10).to(device)
    with torch.no_grad():
        model.weight.copy_((torch.arange(40, device=device).reshape(10, 4) - 20) / 50)
        model.bias.copy_(torch.arange(10, device=device) / 20)
    inputs = (torch.arange(148, dtype=torch.float32).reshape(37, 4) % 19 - 9) / 7
    targets = torch.arange(37, dtype=torch.long) % 10
    dataset = torch.utils.data.TensorDataset(inputs, targets)
    calculator = GeneralCalculator(device)
    server = BasicServer.__new__(BasicServer)
    server.option = options
    server.device = device
    server.model = model
    server.calculator = calculator
    server.test_data = dataset
    server.clients = []
    server.current_round = 1
    server.learning_rate = 0.1
    logger = make_logger(directory)(str(directory), options, name=f"selftest_{device.type}")
    logger.register_variable(coordinator=server, participants=[], clock=SimpleNamespace(current_time=0))
    logger.initialize()
    batches = []
    hook = model.register_forward_pre_hook(lambda _, args: batches.append(args[0].detach().cpu().clone()))
    weights = {k: v.clone() for k, v in model.state_dict().items()}
    random.seed(123)
    np.random.seed(456)
    torch.manual_seed(789)
    torch.cuda.manual_seed_all(789)
    initial = snapshot()
    assert not getattr(calculator, "collect_class_stats", False)
    disabled = server.test()
    after_disabled = snapshot()
    disabled_batches = batches[:]
    batches.clear()
    restore(initial)
    assert all(equal(snapshot(), initial).values())
    calculator.collect_class_stats = True

    # Trace the added block from its first assertion to the next loop boundary.
    function = inspect.unwrap(GeneralCalculator.test)
    source, first_line = inspect.getsourcelines(function)
    start_line = first_line + next(i for i, s in enumerate(source) if "assert outputs.ndim" in s)
    loop_line = first_line + next(i for i, s in enumerate(source) if "for batch_id" in s)
    block_before = None
    block_checks = []

    def trace(frame, event, arg):
        nonlocal block_before
        if event == "line" and frame.f_code is function.__code__:
            if frame.f_lineno == start_line:
                assert block_before is None
                block_before = snapshot()
            elif frame.f_lineno == loop_line and block_before is not None:
                block_checks.append(equal(block_before, snapshot()))
                block_before = None
        return trace

    sys.settrace(trace)
    try:
        logger.log_once()  # The second test() call uses the actual proposed logger path.
    finally:
        sys.settrace(None)
    after_enabled = snapshot()
    enabled = {"accuracy": logger.output["test_accuracy"][-1], "loss": logger.output["test_loss"][-1]}
    stats = logger.coordinator.calculator.last_class_statistics
    print(f"READ_PATH[{device.type}] logger.coordinator.calculator.last_class_statistics={stats}", flush=True)
    assert logger.coordinator is server and logger.coordinator.calculator is calculator
    assert disabled == enabled
    rng_equal = equal(after_disabled, after_enabled)
    assert all(rng_equal.values())
    assert len(block_checks) == len(batches) and block_before is None
    assert all(all(item.values()) for item in block_checks)
    assert len(disabled_batches) == len(batches)
    assert all(torch.equal(x, y) for x, y in zip(disabled_batches, batches))
    assert all(torch.equal(weights[k], v) for k, v in model.state_dict().items())
    accuracy = sum(stats["class_correct"]) / sum(stats["class_total"])
    weighted_loss = sum(n * v for n, v in zip(stats["class_total"], stats["class_loss_mean"])) / sum(stats["class_total"])
    assert accuracy == enabled["accuracy"]
    assert math.isclose(weighted_loss, enabled["loss"], rel_tol=1e-5, abs_tol=1e-6)
    assert stats["class_total"] == torch.bincount(targets, minlength=10).tolist()
    assert set(logger.class_curves) == {"round", "learning_rate_used", "class_correct", "class_loss_mean", "class_total", "trajectory_flags"}
    consumed = {key: not value for key, value in equal(initial, after_disabled).items()}
    restore(initial)
    assert all(equal(snapshot(), initial).values())
    hook.remove()
    print(f"METRICS[{device.type}] disabled={disabled} enabled={enabled}", flush=True)
    print(f"RNG_END_EQUAL[{device.type}] {rng_equal}", flush=True)
    print(f"RNG_CONSUMED_BY_TEST[{device.type}] {consumed}", flush=True)
    print(f"STAT_BLOCK_RNG_UNCHANGED[{device.type}] batches={len(block_checks)} all=True", flush=True)
    print(f"RNG_RESTORED[{device.type}] python,numpy,torch_cpu,torch_cuda_all=True", flush=True)
    print(f"SUMMARIES[{device.type}] accuracy={accuracy} weighted_loss={weighted_loss} "
          f"overall_loss={enabled['loss']} absolute_loss_error={abs(weighted_loss-enabled['loss'])}", flush=True)
    print(f"FORWARD_AND_BATCH_ORDER_EQUAL[{device.type}] batches={len(batches)} model_unchanged=True", flush=True)


if __name__ == "__main__":
    assert Path(sys.executable).resolve() == PYTHON.resolve()
    assert torch.cuda.is_available()
    torch.set_num_threads(1)
    check(torch.device("cpu"))
    check(torch.device("cuda:0"))
    print("ALL_CHECKS_PASSED; runner.run() was not called", flush=True)
