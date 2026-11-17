"""Official-numbered CEC2017 reference adapter; author 殷明骏.

The third-party implementation is vendored unchanged with its license. This
adapter uses opfunu's benchmark interface, but does NOT claim that its objective
is the unmodified opfunu CEC2017 implementation.
"""
from pathlib import Path
import sys
import numpy as np
from opfunu.cec_based.cec import CecBenchmark

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'vendor'))
from cec2017 import functions


class Reference2017(CecBenchmark):
    def __init__(self, fid, ndim=10):
        super().__init__()
        if fid not in [1]+list(range(3, 31)) or ndim != 10:
            raise ValueError('reference experiment uses official F1,F3-F30, D=10')
        self.dim_supported = [10]
        self.check_ndim_and_bounds(ndim, 100, None, np.array([[-100., 100.]]*ndim))
        self.f_global = float(100*fid)
        self.fid = fid
        self._objective = getattr(functions, f'f{fid}')

    def evaluate(self, x, *args):
        self.n_fe += 1
        x = np.asarray(x, float)
        if x.shape != (self.ndim,):
            raise ValueError('expected scalar vector')
        return float(np.asarray(self._objective(x[None, :])).reshape(-1)[0])
