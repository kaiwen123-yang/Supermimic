#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source activate.sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p outputs/publications
exec > >(tee -a "outputs/publications/${1:?run}-i${2:?iteration}.log") 2>&1
python -u scripts/publish_p9.py "$@"
