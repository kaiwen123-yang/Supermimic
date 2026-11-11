#!/bin/bash
set -e
workspace=/root/autodl-tmp/robot-repro/supermimic-official-workspace
export UV_CACHE_DIR="$workspace/.uv-cache"
export UV_PYTHON_INSTALL_DIR="$workspace/.python"
export UV_PYTHON_BIN_DIR="$workspace/tools"
export XDG_CACHE_HOME="$workspace/.cache"
export TORCHINDUCTOR_CACHE_DIR="$workspace/.cache/torchinductor"
export TORCHINDUCTOR_COMPILE_THREADS=2
export CUDA_CACHE_PATH="$workspace/.cache/cuda"
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export NUMEXPR_NUM_THREADS=2
export CUDA_VISIBLE_DEVICES=0
export PYTHONUNBUFFERED=1
export WANDB_MODE=offline
mkdir -p "$workspace/outputs/o1-official-lafan40-s0"
cd "$workspace/supermimic"
exec ../tools/uv run --no-sync python ../work/o1/train_official.py --workspace "$workspace" "$@" >> "$workspace/outputs/o1-official-lafan40-s0/train.log" 2>&1
