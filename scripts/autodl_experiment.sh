#!/usr/bin/env bash
# AutoDL runner. Keep the repository, Conda environment, datasets and logs on
# /root/autodl-tmp so they survive a system-disk reset.
set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
DATA_DISK="${DATA_DISK:-/root/autodl-tmp}"
CONDA_ENV_NAME="${CONDA_ENV_NAME:-flbyz312}"
ENV_DIR="$DATA_DISK/conda/envs/$CONDA_ENV_NAME"
PYTHON_BIN="$ENV_DIR/bin/python"
GPU_INDEX="${GPU_INDEX:-0}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_DIR/outputs/d1_3b}"
LOG_FILE="${LOG_FILE:-$OUTPUT_DIR/run.log}"
RAW_DATA_DIR="$PROJECT_DIR/easyFL/flgo/benchmark/RAW_DATA"

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

check_paths() {
    [[ -d "$DATA_DISK" ]] || die "Data disk missing: $DATA_DISK"
    [[ -e "$PROJECT_DIR/.git" ]] || die "Not a Git checkout: $PROJECT_DIR"
    mkdir -p "$RAW_DATA_DIR"
    local disk_real project_real raw_real
    disk_real="$(realpath "$DATA_DISK")"
    project_real="$(realpath "$PROJECT_DIR")"
    raw_real="$(realpath "$RAW_DATA_DIR")"
    case "$project_real" in "$disk_real"/*) ;; *) die "Project is outside data disk: $project_real" ;; esac
    case "$raw_real" in "$disk_real"/*) ;; *) die "FLGo RAW_DATA is outside data disk: $raw_real" ;; esac
    printf 'PROJECT_DIR=%s\nRAW_DATA=%s\n' "$project_real" "$raw_real"
    df -h "$DATA_DISK"
}

require_python() {
    [[ -x "$PYTHON_BIN" ]] || die "Conda environment missing: $PYTHON_BIN (run setup)"
}

setup_env() {
    check_paths
    local conda_sh="${CONDA_BASE:-/root/miniconda3}/etc/profile.d/conda.sh"
    [[ -f "$conda_sh" ]] || die "Conda activation script missing: $conda_sh"
    # Keep package caches and the environment off the system disk.
    export CONDA_PKGS_DIRS="$DATA_DISK/conda/pkgs"
    export PIP_CACHE_DIR="$DATA_DISK/pip-cache"
    mkdir -p "$CONDA_PKGS_DIRS" "$PIP_CACHE_DIR" "$(dirname "$ENV_DIR")"
    # shellcheck disable=SC1090
    source "$conda_sh"
    if [[ ! -x "$PYTHON_BIN" ]]; then
        conda create -y -p "$ENV_DIR" python=3.12 pip
    fi
    conda activate "$ENV_DIR"
    "$PYTHON_BIN" -m pip install torch==2.5.1 torchvision==0.20.1 \
        --index-url https://download.pytorch.org/whl/cu124
    # Versions mirror the locally checked D1 environment. hdbscan is not used
    # by D1; future experiments can install their own extra dependencies.
    "$PYTHON_BIN" -m pip install numpy==1.26.4 scipy==1.13.1 \
        scikit-learn==1.5.1 matplotlib==3.10.0 tqdm==4.66.5 \
        prettytable==3.17.0 ujson==5.10.0 PyYAML==6.0.1 \
        requests==2.32.3 networkx==3.3 nvidia-ml-py
    "$PYTHON_BIN" -m pip check
    check_env
}

check_env() {
    check_paths
    require_python
    command -v nvidia-smi >/dev/null || die "nvidia-smi is unavailable"
    nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv,noheader
    GPU_INDEX="$GPU_INDEX" "$PYTHON_BIN" -u - <<'PY'
import os
import torch
import torchvision

index = int(os.environ['GPU_INDEX'])
print(f'Python torch={torch.__version__} torchvision={torchvision.__version__} '
      f'CUDA runtime={torch.version.cuda} CUDA available={torch.cuda.is_available()}', flush=True)
assert torch.__version__.split('+')[0] == '2.5.1'
assert torchvision.__version__.split('+')[0] == '0.20.1'
assert torch.cuda.is_available() and index < torch.cuda.device_count()
print(f'GPU {index}: {torch.cuda.get_device_name(index)}', flush=True)
PY
    "$PYTHON_BIN" -u "$PROJECT_DIR/run_d1_full.py" --profile full --list | tail -n 1
}

prepare_d1_data() {
    check_paths
    require_python
    # The repository's CIFAR loader uses download=True. Any download or
    # integrity error stops this command and the full run before training.
    PYTHONPATH="$PROJECT_DIR/easyFL:$PROJECT_DIR${PYTHONPATH:+:$PYTHONPATH}" \
        "$PYTHON_BIN" -u - <<'PY'
from pathlib import Path
import flgo.benchmark
from flgo_byzantine.d1_cifar_lt.common import dataset

print(f'FLGO_RAW_DATA={Path(flgo.benchmark.data_root).resolve()}', flush=True)
for name in ('CIFAR10', 'CIFAR100'):
    train = dataset(name, True)
    test = dataset(name, False)
    assert len(train) == 50000 and len(test) == 10000, name
    print(f'{name}_READY train={len(train)} test={len(test)}', flush=True)
PY
}

start_log() {
    command -v flock >/dev/null || die "flock is unavailable"
    mkdir -p "$OUTPUT_DIR" "$(dirname "$LOG_FILE")"
    exec 9>"$OUTPUT_DIR/.run.lock"
    flock -n 9 || die "Another experiment already holds $OUTPUT_DIR/.run.lock"
    exec >>"$LOG_FILE" 2>&1
    rm -f "$OUTPUT_DIR/last_exit_code"
    trap 'rc=$?; printf "RUN_EXIT=%s at %s\n" "$rc" "$(date -Is)"; printf "%s\n" "$rc" > "$OUTPUT_DIR/last_exit_code"' EXIT
    printf 'RUN_START=%s pid=%s project=%s output=%s\n' \
        "$(date -Is)" "$$" "$PROJECT_DIR" "$OUTPUT_DIR"
    printf 'COMMIT=%s\n' "$(git -C "$PROJECT_DIR" rev-parse --short=8 HEAD)"
}

status_run() {
    printf 'TIME=%s\n' "$(date -Is)"
    printf 'OUTPUT_DIR=%s\nLOG_FILE=%s\n' "$OUTPUT_DIR" "$LOG_FILE"
    if [[ -d "$OUTPUT_DIR/reports" ]]; then
        printf 'COMPLETED_REPORTS=%s/100\n' \
            "$(find "$OUTPUT_DIR/reports" -maxdepth 1 -name 'unit_*.json' -type f | wc -l)"
    fi
    if [[ -f "$OUTPUT_DIR/last_exit_code" ]]; then
        printf 'LAST_EXIT_CODE=%s\n' "$(cat "$OUTPUT_DIR/last_exit_code")"
    fi
    pgrep -af '[r]un_d1_full.py|[a]utodl_experiment.sh run-d1' || true
    nvidia-smi
    if [[ -f "$LOG_FILE" ]]; then tail -n 12 "$LOG_FILE"; fi
}

command_name="${1:-}"
if [[ $# -gt 0 ]]; then shift; fi
case "$command_name" in
    setup) setup_env ;;
    check) check_env ;;
    data-d1) prepare_d1_data ;;
    run-d1)
        start_log
        check_env
        prepare_d1_data
        "$PYTHON_BIN" -u "$PROJECT_DIR/run_d1_full.py" --profile full --all \
            --gpu "$GPU_INDEX" --output-dir "$OUTPUT_DIR"
        ;;
    run)
        [[ $# -ge 1 ]] || die "Usage: run <entrypoint.py> [arguments...]"
        entrypoint="$1"; shift
        [[ "$entrypoint" = /* ]] || entrypoint="$PROJECT_DIR/$entrypoint"
        [[ -f "$entrypoint" ]] || die "Entrypoint missing: $entrypoint"
        start_log
        require_python
        "$PYTHON_BIN" -u "$entrypoint" "$@"
        ;;
    summary-d1)
        require_python
        "$PYTHON_BIN" -u "$PROJECT_DIR/run_d1_full.py" --profile full \
            --summarize --output-dir "$OUTPUT_DIR"
        ;;
    status) status_run ;;
    *)
        cat <<'USAGE'
Usage: bash scripts/autodl_experiment.sh COMMAND
  setup       Create a data-disk Conda environment and install D1 dependencies
  check       Check paths, CUDA, dependencies and the 100-unit plan
  data-d1     Download/verify both CIFAR datasets; fail on any error
  run-d1      Log, verify data, then run all 100 D1 units
  run         Log a different Python entrypoint and its arguments
  summary-d1  Summarize completed D1 reports
  status      Show process, GPU, completed reports and recent log lines
Environment overrides: DATA_DISK, CONDA_ENV_NAME, CONDA_BASE, GPU_INDEX,
                       OUTPUT_DIR, LOG_FILE.
USAGE
        [[ -z "$command_name" ]] || exit 2
        ;;
esac
