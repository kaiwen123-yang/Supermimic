#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source scripts/activate.sh
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
tag="${1:?campaign tag}"
checkpoint="${2:?checkpoint path}"
exec > >(tee -a "outputs/campaigns/${tag}.log") 2>&1
if [[ -f "outputs/campaigns/${tag}.exit" ]]; then
  mv "outputs/campaigns/${tag}.exit" "outputs/campaigns/${tag}.before-checkpoint-change.exit"
fi
trap 'status=$?; printf "%s\n" "$status" > "outputs/campaigns/${tag}.exit"; python scripts/collect_results.py --tag "$tag"; exit "$status"' EXIT
printf 'RESUME_WITH_PER_ITERATION_CHECKPOINTS %s\n' "$checkpoint"
python -u scripts/train.py --method supermimic --config configs/lafan40.json --run "${tag}-supermimic" --resume "$checkpoint" --resume-in-place
python -u scripts/evaluate_retained.py "outputs/runs/${tag}-supermimic"
python scripts/collect_results.py --tag "$tag"
python -u scripts/train.py --method ppo_sim --config configs/lafan40.json --run "${tag}-ppo_sim"
python -u scripts/evaluate_retained.py "outputs/runs/${tag}-ppo_sim"
python scripts/collect_results.py --tag "$tag"
