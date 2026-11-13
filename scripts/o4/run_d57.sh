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
export PYTHONPATH="$workspace/supermimic-o3-stability/src:$workspace/mjlab_research/src"
mkdir -p "$workspace/outputs/20261113-o4-official-bones-long-s0"
cd "$workspace/supermimic-o3-stability"
exec "$workspace/supermimic/.venv/bin/python" ../work/o4/driver.py --workspace "$workspace" "$@" >> "$workspace/outputs/20261113-o4-official-bones-long-s0/driver.log" 2>&1
