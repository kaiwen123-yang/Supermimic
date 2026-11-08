#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source activate.sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
job="${1:?P10 job}"
readarray -t settings < <(python -c 'import json,sys; p=json.load(open("configs/next_stage_8k_hard_practice_protocol.json")); j=p["jobs"][sys.argv[1]]; print(j["planned_config"]); print(j["run"]); print(p["source"]["checkpoint"])' "$job")
mkdir -p outputs/campaigns outputs/publications
python -u scripts/train.py --method supermimic --config "${settings[0]}" --run "${settings[1]}" --resume "${settings[2]}" > "outputs/campaigns/${settings[1]}.train.log" 2>&1
python -u scripts/finish_p10.py "$job" > "outputs/campaigns/${settings[1]}.finish.log" 2>&1
