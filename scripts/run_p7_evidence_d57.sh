#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source activate.sh
python -u scripts/p7_evidence.py > outputs/campaigns/20261105-p7-feedback-reproduction-s0.evidence.log 2>&1
