#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source scripts/activate.sh
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
tag="${1:?Pass a unique run tag, e.g. 20261031-r1}"
mkdir -p outputs/development
exec > >(tee -a "outputs/development/${tag}.log") 2>&1
trap 'status=$?; printf "%s\n" "$status" > "outputs/development/${tag}.exit"; python scripts/collect_results.py --tag "$tag"; exit "$status"' EXIT
python -u scripts/train.py --method supermimic --config configs/lafan40_development.json --run "${tag}-supermimic"
python -u scripts/evaluate.py "outputs/runs/${tag}-supermimic/checkpoint_latest.pt"
python -u scripts/train.py --method ppo_sim --config configs/lafan40_development.json --run "${tag}-ppo-sim"
python -u scripts/evaluate.py "outputs/runs/${tag}-ppo-sim/checkpoint_latest.pt"
