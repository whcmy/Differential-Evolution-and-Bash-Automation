"""Full-budget same-seed replay of selected final runs; 殷明骏."""
import os
for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[k] = '1'
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import sys
import numpy as np
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'code'))
from run_adaptive_de import run_one, FINAL


def one(algorithm):
    directory = ROOT/'results/common_benchmark'
    config = json.loads((directory/'manifest.json').read_text())['config']
    # F9 is multimodal and exercises multiple update generations at full budget.
    original = json.loads((directory/algorithm/'F09_run01.json').read_text())
    repeated = run_one((config, algorithm, 9, 1))
    fields = ['algorithm', 'suite', 'function', 'run', 'seed', 'optimum', 'error',
              'signed_error', 'x', 'fun', 'nfev', 'history', 'diagnostics']
    if algorithm == 'DSPDE':
        fields += ['generations', 'subgroup_size']
    mismatches = [key for key in fields if json.dumps(original[key], sort_keys=True) != json.dumps(repeated[key], sort_keys=True)]
    return dict(algorithm=algorithm, function=9, run=1, seed=original['seed'], nfev=repeated['nfev'],
                checked_fields=fields, mismatches=mismatches, verdict='EXACT_MATCH' if not mismatches else 'MISMATCH')


if __name__ == '__main__':
    with ProcessPoolExecutor(max_workers=5) as pool:
        rows = list(pool.map(one, FINAL))
    d = dict(author='殷明骏', student_id='202483890029', selected_runs=rows,
             passed=all(r['verdict'] == 'EXACT_MATCH' for r in rows),
             scope='five selected full-budget F9/run1 replays; not every run replayed')
    (ROOT/'output/selected_replay.json').write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(d, ensure_ascii=False, indent=2))
    sys.exit(0 if d['passed'] else 1)
