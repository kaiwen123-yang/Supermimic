#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source scripts/activate.sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export HTTPS_PROXY=http://127.0.0.1:7890 HTTP_PROXY=http://127.0.0.1:7890
mkdir -p outputs/publications
exec > >(tee -a "outputs/publications/${1:?run}-i${2:?iteration}.log") 2>&1
python -u scripts/publish_checkpoint.py "$1" "$2"
