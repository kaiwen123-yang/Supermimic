#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export UV_CACHE_DIR=/root/autodl-tmp/robot-repro/.cache/uv
export UV_PYTHON_INSTALL_DIR=/root/autodl-tmp/tools/python
export UV_LINK_MODE=clone
/root/autodl-tmp/tools/uv-env/bin/uv sync --frozen
/root/autodl-tmp/tools/uv-env/bin/uv pip check --python .venv/bin/python
