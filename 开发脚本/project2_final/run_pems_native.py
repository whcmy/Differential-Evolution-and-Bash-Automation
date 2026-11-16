"""Strict-budget PEMS-DE reproduction, CEC2017 reference, 20 runs."""
import os
for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[k] = '1'
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import time
import numpy as np
from pems_native_problem import Reference2017

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'code'))
from run_project2 import digest, write_json
from pems_de import minimize


def run_one(task):
    fid, run = task
    problem = Reference2017(fid)
    seed = int(np.random.SeedSequence([20261109, 2017, fid, run]).generate_state(1)[0])
    start = time.perf_counter()
    result = minimize(problem.evaluate, np.column_stack((problem.lb, problem.ub)),
                      seed=seed, population_size=60, max_fes=100000)
    assert result['nfev'] == problem.n_fe == 100000
    recomputed = problem.evaluate(np.array(result['x']))
    assert np.isclose(recomputed, result['fun'], rtol=1e-12, atol=1e-9)
    signed = result['fun']-problem.f_global
    assert signed >= -1e-7
    return dict(algorithm='PEMSDE', suite='cec2017', function=fid, run=run, seed=seed,
                optimum=problem.f_global, error=max(0., signed), signed_error=signed,
                audit_evaluations=1, recomputed_fitness=recomputed, seconds=time.perf_counter()-start, **result)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--resume', action='store_true')
    a = p.parse_args()
    functions = [1]+list(range(3, 31))
    for fid in functions:
        problem = Reference2017(fid)
        value = problem.evaluate(np.zeros(10))
        assert np.isfinite(value)
    output = ROOT/'results/pems_native_reference'
    output.mkdir(parents=True, exist_ok=True)
    c = dict(suite='cec2017', algorithms=['PEMSDE'], functions=functions, runs=20, dimension=10,
             max_fes=100000, population_size=60, seed=20261109,
             benchmark='CEC2017-py reference, official numbering; opfunu interface adapter',
             author='殷明骏', student_id='202483890029', python=platform.python_version(),
             versions={name: importlib.metadata.version(name) for name in ['numpy', 'opfunu']},
             source_sha256={str(f.relative_to(ROOT)): digest(f) for f in
                            [ROOT/'code/pems_de.py', ROOT/'run_pems_native.py', ROOT/'pems_native_problem.py']},
             reference_sha256={str(f.relative_to(ROOT/'vendor')): digest(f) for f in
                               sorted((ROOT/'vendor/cec2017').rglob('*')) if f.is_file() and '__pycache__' not in f.parts})
    mp = output/'manifest.json'
    if mp.exists():
        manifest = json.loads(mp.read_text())
        if not a.resume or manifest['config'] != c:
            raise ValueError('resume config differs')
    else:
        manifest = dict(config=c, started_utc=datetime.now(timezone.utc).isoformat())
        write_json(mp, manifest)
    tasks = [(f, r) for r in range(1, 21) for f in reversed(functions)
             if not (output/'PEMSDE'/f'F{f:02d}_run{r:02d}.json').exists()]
    print(f'PENDING {len(tasks)} workers={a.workers}', flush=True)
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        for done, future in enumerate(as_completed([pool.submit(run_one, t) for t in tasks]), 1):
            row = future.result()
            write_json(output/'PEMSDE'/f"F{row['function']:02d}_run{row['run']:02d}.json", row)
            print(f"RESULT function=F{row['function']:02d} run={row['run']:02d} fes={row['nfev']} "
                  f"error={row['error']:.12e} seconds={row['seconds']:.3f} completed={done}/{len(tasks)}", flush=True)
    manifest.update(completed_utc=datetime.now(timezone.utc).isoformat(), record_count=580)
    write_json(mp, manifest)
    print('COMPLETE 580', flush=True)


if __name__ == '__main__':
    main()
