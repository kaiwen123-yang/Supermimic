#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
source activate.sh
python -u scripts/record_p9_started.py > outputs/campaigns/p9-all-started-publication.log 2>&1
