#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source scripts/activate.sh
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export HTTPS_PROXY=http://127.0.0.1:7890 HTTP_PROXY=http://127.0.0.1:7890
tag="${1:?Pass a unique paired experiment tag}"
mkdir -p outputs/campaigns
exec > >(tee -a "outputs/campaigns/${tag}.log") 2>&1
trap 'status=$?; printf "%s\n" "$status" > "outputs/campaigns/${tag}.exit"; python scripts/collect_results.py --tag "$tag"; exit "$status"' EXIT

python - <<'PY'
import json
from pathlib import Path
base = json.loads(Path('configs/lafan40.json').read_text())
learned = json.loads(Path('configs/lafan40_termination_learned.json').read_text())
analytic = json.loads(Path('configs/lafan40_termination_analytic_smooth.json').read_text())
different = {k for k in learned.keys() | analytic.keys() if learned.get(k) != analytic.get(k)}
assert different == {'imagination_termination'}, different
assert all(learned[k] == v for k, v in base.items())
assert set(learned) - set(base) == {'imagination_termination', 'termination_smoothing_temperature'}
assert learned['imagination_horizon'] == 32 and learned['max_hours'] == 3.0
assert learned['checkpoint_every_iterations'] == 1 and learned['publish_every_iterations'] == 1000
print('FROZEN_TERMINATION_COMPARISON', json.dumps({'changed_field': sorted(different), 'learned': learned, 'analytic': analytic}), flush=True)
PY

for mode in learned analytic_smooth; do
  run="${tag}-${mode}"
  extra=(--initialization-reference "outputs/runs/20261031-learning-s0-supermimic/checkpoint_0000000.pt")
  if [[ "$mode" == analytic_smooth ]]; then
    extra=(--initialization-reference "outputs/runs/${tag}-learned/checkpoint_0000000.pt")
  fi
  python -u scripts/train.py --method supermimic --config "configs/lafan40_termination_${mode}.json" --run "$run" "${extra[@]}"
  python -u scripts/evaluate_retained.py "outputs/runs/${run}"
  iteration="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["iteration"])' "outputs/runs/${run}/status.json")"
  bash scripts/publish_checkpoint_d57.sh "$run" "$iteration" --final
  python scripts/collect_results.py --tag "$tag" --publish
done
