#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source activate.sh
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
unset HTTPS_PROXY HTTP_PROXY ALL_PROXY https_proxy http_proxy all_proxy
source /etc/network_turbo >/dev/null
tag="${1:?Pass the unique P2 campaign name}"
mkdir -p outputs/campaigns
publishers=()
for mode in robot_root reference_heading; do
  run="${tag}-${mode}"
  python -u scripts/train.py --method supermimic --config "configs/lafan40_goal_${mode}.json" --run "$run" > "outputs/campaigns/${run}.train.log" 2>&1
  iteration="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["iteration"])' "outputs/runs/${run}/status.json")"
  bash scripts/publish_checkpoint_d57.sh "$run" "$iteration" --final &
  publishers+=("$!")
done
for pid in "${publishers[@]}"; do
  wait "$pid" || printf 'Final publisher failed; unpublished files remain.\n'
done
# Exact milestone tmux sessions finish before any archive or cleanup touches their files.
for mode in robot_root reference_heading; do
  run="${tag}-${mode}"
  iteration="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["iteration"])' "outputs/runs/${run}/status.json")"
  for ((node=1000; node<=iteration; node+=1000)); do
    session="sm-pub-${run}-$(printf '%07d' "$node")"
    while tmux has-session -t "$session" 2>/dev/null && [[ "$(tmux display-message -p -t "$session" '#{pane_dead}')" == 0 ]]; do
      sleep 30
    done
  done
done
python -u scripts/finish_goal_campaign.py "$tag"
