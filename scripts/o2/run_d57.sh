#!/bin/bash
set -e
workspace=/root/autodl-tmp/robot-repro/supermimic-official-workspace
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
mkdir -p "$workspace/outputs/o2-official-bones-s0"
cd "$workspace/supermimic"
exec .venv/bin/python ../work/o2/driver.py --workspace "$workspace" "$@" >> "$workspace/outputs/o2-official-bones-s0/driver.log" 2>&1
