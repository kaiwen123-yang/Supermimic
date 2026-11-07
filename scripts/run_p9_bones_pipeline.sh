#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source activate.sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python -u scripts/prepare_bones_p9.py > outputs/campaigns/p9-bones-preparation.log 2>&1
bash scripts/start_p9_bones_when_ready.sh
