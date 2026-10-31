# Source this file to enter the isolated SuperMimic environment.
_supermimic_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$_supermimic_root/.venv/bin/activate"
unset PYTHONPATH PYTHONHOME LD_LIBRARY_PATH
export PYTHONNOUSERSITE=1
export PATH="$PATH:/root/autodl-tmp/tools/uv-env/bin"
export UV_CACHE_DIR=/root/autodl-tmp/robot-repro/.cache/uv
export UV_PYTHON_INSTALL_DIR=/root/autodl-tmp/tools/python
export UV_LINK_MODE=clone
export XDG_CACHE_HOME="$_supermimic_root/.cache"
export HF_HOME="$_supermimic_root/.cache/huggingface"
export TORCH_HOME="$_supermimic_root/.cache/torch"
export TORCHINDUCTOR_CACHE_DIR="$_supermimic_root/.cache/torchinductor"
export WANDB_DIR="$_supermimic_root/outputs"
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export MUJOCO_GL=egl PYOPENGL_PLATFORM=egl
cd "$_supermimic_root"
unset _supermimic_root
