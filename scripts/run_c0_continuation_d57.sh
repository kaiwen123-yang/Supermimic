#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source activate.sh
tag="${1:?Pass the P4 campaign name}"
run="${tag}-h32_aux_bce"
parent="outputs/parents/${tag}/checkpoint_0009000.pt"
mkdir -p outputs/campaigns
python -u scripts/train.py --method supermimic --config configs/lafan40_c0_continuation.json --run "$run" --resume "$parent" > "outputs/campaigns/${run}.train.log" 2>&1
start="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["start_iteration"])' "outputs/runs/${run}/status.json")"
iteration="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["iteration"])' "outputs/runs/${run}/status.json")"
for ((node=(start/1000+1)*1000; node<=iteration; node+=1000)); do
  session="sm-pub-${run}-$(printf '%07d' "$node")"
  while tmux has-session -t "$session" 2>/dev/null && [[ "$(tmux display-message -p -t "$session" '#{pane_dead}')" == 0 ]]; do
    sleep 30
  done
done
python -u scripts/finish_c0_continuation.py "$tag"
