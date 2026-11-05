#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source activate.sh
job="${1:?Pass continuation or from_scratch}"
config="configs/lafan40_p7_${job}.json"
readarray -t settings < <(python -c 'import json,sys; c=json.load(open(sys.argv[1])); print(c["run"]); print(c["parent_checkpoint"] or "")' "$config")
run="${settings[0]}"
resume=()
if [[ "$job" == continuation ]]; then
    resume=(--resume "${settings[1]}")
fi
mkdir -p outputs/campaigns work outputs/publications
python -u scripts/train.py --method supermimic --config "$config" --run "$run" "${resume[@]}" > "outputs/campaigns/${run}.train.log" 2>&1
python -u scripts/finish_p7_reproduction.py "$job" > "outputs/campaigns/${run}.finish.log" 2>&1
