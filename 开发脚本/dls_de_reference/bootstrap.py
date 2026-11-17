"""Make optional, study-local dependencies visible; no automatic installs."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if (ROOT / ".vendor").exists():
    sys.path.insert(0, str(ROOT / ".vendor"))
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
