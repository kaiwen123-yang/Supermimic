#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
source activate.sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
exec > outputs/campaigns/p8-bones-prepare.log 2>&1
echo "Waiting for the active official G1 acquisition tmux"
while [[ ! -f data/raw/bones_seed/g1.tar.gz ]]; do
    if [[ "$(tmux display-message -p -t sm-p8-bones-data '#{pane_dead}')" == 1 ]]; then
        echo "BONES acquisition exited before completing g1.tar.gz; see p8-bones-fetch.log"
        exit 1
    fi
    sleep 15
done
python -u scripts/prepare_bones_p8.py
