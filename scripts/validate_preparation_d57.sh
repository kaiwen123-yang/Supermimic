#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source scripts/activate.sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p outputs/preparation
exec > >(tee -a outputs/preparation/validation.log) 2>&1
trap 'status=$?; printf "%s\n" "$status" > outputs/preparation/validation-exit-code; exit "$status"' EXIT
date -Is
CUDA_VISIBLE_DEVICES="" nice -n 10 python -u scripts/audit_reference_kinematics.py
CUDA_VISIBLE_DEVICES=0 nice -n 10 python -u scripts/reference_pd.py --batch-size 40
date -Is
