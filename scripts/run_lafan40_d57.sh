#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source scripts/activate.sh
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
tag="${1:?Pass a unique run tag}"
mkdir -p outputs/campaigns
exec > >(tee -a "outputs/campaigns/${tag}.log") 2>&1
trap 'status=$?; printf "%s\n" "$status" > "outputs/campaigns/${tag}.exit"; python scripts/collect_results.py --tag "$tag"; exit "$status"' EXIT
for method in supermimic ppo_sim; do
  run="${tag}-${method}"
  python -u scripts/train.py --method "$method" --config configs/lafan40.json --run "$run"
  python -u scripts/evaluate_retained.py "outputs/runs/${run}"
  python scripts/collect_results.py --tag "$tag"
done
