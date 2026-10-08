"""Two serial deterministic CNN units; checkpoint comparisons run in the parent."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import traceback

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
DIAG = ROOT / "outputs/d1_3b/phase_a_diag_20261002"
sys.path.insert(0, str(DIAG))
from execute_diag import PYTHON, BASELINE, make_logger, save, now, validate_task, assert_model_finite


def unit(mode):
    # The parent provides this before importing torch or initializing CUDA.
    assert os.environ["CUBLAS_WORKSPACE_CONFIG"] == ":4096:8"
    import numpy as np
    import torch
    import flgo
    from flgo.algorithm import fedavg
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True, warn_only=False)
    assert torch.cuda.is_available() and torch.__version__.startswith("2.5.1")
    started = time.perf_counter()
    directory = OUT / mode
    manifest = json.loads((BASELINE / "manifest.json").read_text(encoding="utf-8"))
    record = manifest["tasks"]["101"]
    task = validate_task(101, record)
    options = dict(manifest["options"]["101"])
    options["num_rounds"] = 20
    assert options["seed"] == 101 and options["proportion"] == 0.4
    assert options["num_epochs"] == 1 and options["learning_rate"] == 0.1 and options["batch_size"] == 64
    for child in ("record", "log"):
        (directory / child).mkdir()
    baseline_result = json.loads((BASELINE / "seed_101/result.json").read_text(encoding="utf-8"))
    participants, timings = [], []
    LoggerBase = make_logger(directory, collect_class_stats=(mode == "on"))

    class CheckpointLogger(LoggerBase):
        def log_once(self, *args, **kwargs):
            super().log_once(*args, **kwargs)
            round_number = 0 if len(self.output["time"]) == 1 else self.coordinator.current_round
            assert round_number in (0, 10, 20)
            server = self.coordinator
            payload = {
                "round": round_number,
                "model": {name: tensor.detach().cpu().clone() for name, tensor in server.model.state_dict().items()},
                "parameter_names": list(dict(server.model.named_parameters())),
                "buffer_names": list(dict(server.model.named_buffers())),
                "participants": [ids[:] for ids in participants],
                "python_rng": random.getstate(), "numpy_rng": np.random.get_state(),
                "torch_cpu_rng": torch.get_rng_state().clone(),
                "torch_cuda_rng": [state.clone() for state in torch.cuda.get_rng_state_all()],
                "accuracy": self.output["test_accuracy"][-1],
                "loss": self.output["test_loss"][-1],
            }
            target = directory / f"checkpoint_round_{round_number:03d}.pt"
            temporary = target.with_suffix(".tmp")
            torch.save(payload, temporary)
            os.replace(temporary, target)
            if mode == "on":
                # Continue only after the independent parent approves this checkpoint.
                acknowledge = directory / f"approved_round_{round_number:03d}"
                wait_started = time.perf_counter()
                while not acknowledge.exists():
                    if time.perf_counter() - wait_started > 120:
                        raise RuntimeError(f"CHECKPOINT_APPROVAL_TIMEOUT round={round_number}")
                    time.sleep(0.05)

    runner = flgo.init(str(task), fedavg, options, Logger=CheckpointLogger)
    assert runner.num_clients == len(runner.clients) == 100
    assert type(runner.model).__module__ == "flgo.benchmark.cifar10_classification.model.cnn"
    assert runner.option["seed"] == 101 and runner.num_rounds == 20
    assert runner.learning_rate == 0.1 and runner.proportion == 0.4
    assert torch.backends.cudnn.deterministic and not torch.backends.cudnn.benchmark
    assert torch.are_deterministic_algorithms_enabled()
    assert not torch.is_deterministic_algorithms_warn_only_enabled()
    settings = {
        "seed": runner.option["seed"], "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda, "cudnn_version": torch.backends.cudnn.version(),
        "gpu_name": torch.cuda.get_device_name(0),
        "cudnn_deterministic": torch.backends.cudnn.deterministic,
        "cudnn_benchmark": torch.backends.cudnn.benchmark,
        "CUBLAS_WORKSPACE_CONFIG": os.environ["CUBLAS_WORKSPACE_CONFIG"],
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "deterministic_warn_only": torch.is_deterministic_algorithms_warn_only_enabled(),
    }
    save(directory / "determinism.json", settings)
    runner.calculator.collect_class_stats = mode == "on"
    iterate = runner.iterate

    def monitored_iterate():
        begin = time.perf_counter()
        assert all(c.learning_rate == 0.1 for c in runner.clients)
        value = iterate()
        assert_model_finite(runner.model)
        selected = [int(cid) for cid in runner.selected_clients]
        received = [int(cid) for cid in runner.received_clients]
        assert len(selected) == len(set(selected)) == 40 and selected == received
        assert selected == baseline_result["participants"][len(participants)]
        participants.append(selected)
        timings.append(time.perf_counter() - begin)
        return value

    runner.iterate = monitored_iterate
    runner.run()
    assert runner.current_round == 21 and len(participants) == 20
    assert runner.gv.logger.output["time"] == [0, 10, 20]
    assert set(runner.gv.logger.output) == {"option", "client_datavol", "time", "test_accuracy", "test_loss"}
    if mode == "on":
        assert runner.gv.logger.class_curves["round"] == [0, 10, 20]
        assert runner.gv.logger.class_curves["class_total"] == [1000] * 10
    else:
        assert not hasattr(runner.calculator, "last_class_statistics")
    validate_task(101, record)
    save(directory / "result.json", {"seed": 101, "method": "FedAvg", "attack": "none",
         "task": str(task), "rounds": 20, "participants": participants,
         "overall_accuracy": runner.gv.logger.output["test_accuracy"][-1],
         "elapsed_seconds": time.perf_counter()-started, "round_seconds": timings})
    print(f"SWITCH_UNIT_COMPLETE mode={mode} rounds=20 settings={settings}", flush=True)


def compare_checkpoint(round_number):
    import numpy as np
    import torch
    off = torch.load(OUT / f"off/checkpoint_round_{round_number:03d}.pt", map_location="cpu", weights_only=False)
    on = torch.load(OUT / f"on/checkpoint_round_{round_number:03d}.pt", map_location="cpu", weights_only=False)
    assert off["round"] == on["round"] == round_number
    assert off["parameter_names"] == on["parameter_names"]
    assert off["buffer_names"] == on["buffer_names"]
    assert off["model"].keys() == on["model"].keys()
    tensors = []
    for name, reference in off["model"].items():
        current = on["model"][name]
        assert reference.shape == current.shape and reference.dtype == current.dtype
        difference = (current.double() - reference.double()).abs()
        relative = difference / torch.maximum(current.double().abs(), reference.double().abs()).clamp_min(1e-12)
        tensors.append({"name": name, "kind": "parameter" if name in off["parameter_names"] else "buffer",
                        "bitwise_equal": torch.equal(current.contiguous().view(torch.uint8), reference.contiguous().view(torch.uint8)),
                        "max_absolute_difference": difference.max().item() if difference.numel() else 0,
                        "max_relative_difference": relative.max().item() if relative.numel() else 0})
    rng = {
        "python": off["python_rng"] == on["python_rng"],
        "numpy": (off["numpy_rng"][0] == on["numpy_rng"][0] and
                  np.array_equal(off["numpy_rng"][1], on["numpy_rng"][1]) and
                  off["numpy_rng"][2:] == on["numpy_rng"][2:]),
        "torch_cpu": torch.equal(off["torch_cpu_rng"], on["torch_cpu_rng"]),
        "torch_cuda_all": (len(off["torch_cuda_rng"]) == len(on["torch_cuda_rng"]) and
                           all(torch.equal(a, b) for a, b in zip(off["torch_cuda_rng"], on["torch_cuda_rng"]))),
    }
    return {
        "round": round_number, "participants_equal": off["participants"] == on["participants"],
        "participant_rounds": len(off["participants"]), "tensors": tensors,
        "rng_equal": rng, "accuracy_off": off["accuracy"], "accuracy_on": on["accuracy"],
        "accuracy_difference": on["accuracy"] - off["accuracy"],
        "loss_off": off["loss"], "loss_on": on["loss"], "loss_difference": on["loss"] - off["loss"],
    }


def run():
    started = time.perf_counter()
    assert not (OUT / "off").exists() and not (OUT / "on").exists()
    records, comparisons = {}, []
    save(OUT / "launch.json", {"started_at": now(), "python": str(PYTHON), "order": ["off", "on"]})
    environment = dict(os.environ, CUBLAS_WORKSPACE_CONFIG=":4096:8")
    for mode in ("off", "on"):
        directory = OUT / mode
        directory.mkdir()
        child_started = time.perf_counter()
        with (directory / "console.log").open("w", encoding="utf-8") as stream:
            child = subprocess.Popen([str(PYTHON), "-B", "-u", str(Path(__file__).resolve()),
                                      "unit", "--mode", mode], cwd=ROOT, env=environment,
                                     stdout=stream, stderr=subprocess.STDOUT)
            records[mode] = {"pid": child.pid, "started_at": now()}
            try:
                checked = set()
                while True:
                    if mode == "on":
                        for checkpoint in (0, 10, 20):
                            path = directory / f"checkpoint_round_{checkpoint:03d}.pt"
                            if checkpoint not in checked and path.exists():
                                comparison = compare_checkpoint(checkpoint)
                                comparisons.append(comparison)
                                save(OUT / "comparison.json", comparisons)
                                assert comparison["participants_equal"], f"PARTICIPANTS_DIFFER round={checkpoint}"
                                assert all(comparison["rng_equal"].values()), f"RNG_DIFFER round={checkpoint} {comparison['rng_equal']}"
                                unequal = [t for t in comparison["tensors"] if not t["bitwise_equal"]]
                                assert not unequal, f"MODEL_DIFFER round={checkpoint} {unequal}"
                                assert comparison["accuracy_difference"] == 0 and comparison["loss_difference"] == 0, f"METRICS_DIFFER round={checkpoint} {comparison}"
                                (directory / f"approved_round_{checkpoint:03d}").write_text("passed", encoding="utf-8")
                                checked.add(checkpoint)
                                print(f"CHECKPOINT_PASSED round={checkpoint} tensors_equal=True rng_equal=True metrics_equal=True", flush=True)
                    code = child.poll()
                    if code is not None:
                        records[mode].update(returncode=code, ended_at=now(), wall_seconds=time.perf_counter()-child_started)
                        assert code == 0, f"SWITCH_PROCESS_FAILED mode={mode} code={code}"
                        break
                    time.sleep(0.1)
                if mode == "on":
                    assert checked == {0, 10, 20}
            finally:
                if child.poll() is None:
                    child.terminate()
                    child.wait()
                records[mode].update(returncode=child.returncode, ended_at=now(), wall_seconds=time.perf_counter()-child_started)
                save(OUT / "execution.json", {"processes": records, "total_wall_seconds": time.perf_counter()-started})
        print(f"PROCESS_COMPLETE mode={mode} code=0", flush=True)
    off_files = list((OUT / "off/record").glob("*.json"))
    on_files = list((OUT / "on/record").glob("*.json"))
    assert len(off_files) == len(on_files) == 1
    off_record = json.loads(off_files[0].read_text(encoding="utf-8"))
    on_record = json.loads(on_files[0].read_text(encoding="utf-8"))
    assert off_record == on_record
    assert json.loads((OUT / "off/determinism.json").read_text()) == json.loads((OUT / "on/determinism.json").read_text())
    print("SWITCH_CHECK_PASSED; complete records identical; only step 1 executed", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("run", "unit"))
    parser.add_argument("--mode", choices=("off", "on"))
    args = parser.parse_args()
    assert Path(sys.executable).resolve() == PYTHON.resolve()
    try:
        (run() if args.action == "run" else unit(args.mode))
    except Exception:
        traceback.print_exc()
        sys.exit(1)
