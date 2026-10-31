#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source scripts/activate.sh
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p outputs/preparation
exec > >(tee -a outputs/preparation/prepare.log) 2>&1
trap 'status=$?; printf "%s\n" "$status" > outputs/preparation/exit-code; exit "$status"' EXIT
date -Is
python -u scripts/fetch_sources.py
nice -n 10 python -u scripts/prepare_lafan1.py
date -Is
