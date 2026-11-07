#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
source activate.sh
exec > outputs/campaigns/p9-bones-dispatch.log 2>&1
while [[ ! -f work/p9_full_runtime_ready ]]; do
    sleep 10
done
tmux new-session -d -s sm-p9-bones-full-lafan "bash /root/autodl-tmp/robot-repro/supermimic-p9-critic-full-scale/scripts/run_p9_d57.sh bones_full_lafan_survival"
tmux set-option -t sm-p9-bones-full-lafan remain-on-exit on
python -u scripts/publish_p9_data.py > outputs/campaigns/p9-bones-manifest.log 2>&1
