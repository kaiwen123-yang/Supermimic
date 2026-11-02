#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source activate.sh
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
unset HTTPS_PROXY HTTP_PROXY ALL_PROXY https_proxy http_proxy all_proxy
source /etc/network_turbo >/dev/null
tag="${1:?Pass the unique P3 campaign name}"
parent="outputs/parents/${tag}/checkpoint_0006000.pt"
mkdir -p outputs/campaigns
for arm in h32_state_only h32_aux_bce; do
  run="${tag}-${arm}"
  python -u scripts/train.py --method supermimic --config "configs/lafan40_${arm}.json" --run "$run" --resume "$parent" > "outputs/campaigns/${run}.train.log" 2>&1
  iteration="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["iteration"])' "outputs/runs/${run}/status.json")"
  if (( iteration % 1000 != 0 )); then
    bash scripts/publish_checkpoint_d57.sh "$run" "$iteration" --final &
    wait "$!" || printf 'Final publication incomplete; files retained.\n'
  fi
done
for arm in h32_state_only h32_aux_bce; do
  run="${tag}-${arm}"
  iteration="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["iteration"])' "outputs/runs/${run}/status.json")"
  for ((node=7000; node<=iteration; node+=1000)); do
    session="sm-pub-${run}-$(printf '%07d' "$node")"
    while tmux has-session -t "$session" 2>/dev/null && [[ "$(tmux display-message -p -t "$session" '#{pane_dead}')" == 0 ]]; do
      sleep 30
    done
  done
done
python -u scripts/finish_tracking_campaign.py "$tag"
