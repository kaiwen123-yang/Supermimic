#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source activate.sh
tag="${1:?Pass the P4 campaign name}"
run="${tag}-h32_aux_bce"
parent="outputs/parents/${tag}/checkpoint_0009000.pt"
mkdir -p outputs/campaigns
python -u scripts/train.py --method supermimic --config configs/lafan40_c0_continuation.json --run "$run" --resume "$parent" > "outputs/campaigns/${run}.train.log" 2>&1
python -u scripts/finish_c0_continuation.py "$tag"
