#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
source activate.sh
exec > outputs/campaigns/p8-bones-dispatch.log 2>&1
# H32 observed~22GiB plus6.79GiB reference. Admission check, not a memory cap.
while (( $(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1) < 32768 )); do
    echo "Frozen40h ready; waiting for32GiB free on the shared GPU"
    sleep 30
done
python -u scripts/publish_bones_data.py starting
bash scripts/run_p8_d57.sh bones40_transfer_h32
