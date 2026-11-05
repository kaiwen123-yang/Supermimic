#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source activate.sh
arm="${1:?Pass no_position_feedback or root_position_feedback}"
config="configs/lafan40_p6_${arm}.json"
readarray -t settings < <(python -c 'import json,sys; c=json.load(open(sys.argv[1])); print(c["run"]); print(c["parent_checkpoint"])' "$config")
run="${settings[0]}"
mkdir -p outputs/campaigns work outputs/publications
python -u scripts/train.py --method supermimic --config "$config" --run "$run" --resume "${settings[1]}" > "outputs/campaigns/${run}.train.log" 2>&1
python -u scripts/finish_p6_position_feedback.py "$arm" > "outputs/campaigns/${run}.finish.log" 2>&1
