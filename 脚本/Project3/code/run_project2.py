"""Unified Project2 experiments. Author: 殷明骏, 202483890029."""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_key] = '1'
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import time
import numpy as np
from opfunu.cec_based import cec2014, cec2017, cec2022
import basic_de
import dspde
import dls_de
import pems_de
import team_de

ROOT = Path(__file__).resolve().parents[1]
FINAL = ['DE', 'DSPDE', 'DLSDE', 'PEMSDE', 'TEAM']
ALL = FINAL+list(dspde.VARIANTS[1:])+list(pems_de.VARIANTS[1:])+list(team_de.VARIANTS[1:])+list(dls_de.VARIANTS[1:-1])


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    temp.replace(path)


def make_problem(suite, fid, dimension):
    module = dict(cec2014=cec2014, cec2017=cec2017, cec2022=cec2022)[suite]
    return getattr(module, f'F{fid}{suite[-4:]}')(ndim=dimension)


def optimize(problem, algorithm, config, seed):
    bounds = np.column_stack((problem.lb, problem.ub))
    common = dict(max_fes=config['max_fes'], population_size=config['population_size'], seed=seed)
    if algorithm == 'DE':
        r = basic_de.minimize(problem.evaluate, bounds, **common)
        return dict(x=r.x.tolist(), fun=r.fun, nfev=r.nfev, history=r.history, diagnostics={})
    if algorithm == 'DSPDE' or algorithm in dspde.VARIANTS[1:]:
        settings = dspde.Settings(population_size=common['population_size'], max_fes=common['max_fes'])
        r = dspde.minimize(problem.evaluate, bounds, settings=settings, seed=seed, variant=algorithm)
        r['diagnostics'] = r.pop('counters')
        return r
    if algorithm == 'DLSDE' or algorithm in dls_de.VARIANTS:
        variant = 'dls_de' if algorithm == 'DLSDE' else algorithm
        r = dls_de.minimize(problem.evaluate, bounds, **common, variant=variant,
                            min_population_size=common['population_size'] if config['population_mode'] == 'fixed' else 4)
        return dict(x=r.x.tolist(), fun=r.fun, nfev=r.nfev, history=r.history, diagnostics=r.diagnostics)
    if algorithm in pems_de.VARIANTS:
        return pems_de.minimize(problem.evaluate, bounds, **common, variant=algorithm)
    if algorithm in team_de.VARIANTS:
        return team_de.minimize(problem.evaluate, bounds, **common, variant=algorithm)
    raise ValueError(algorithm)


def run_one(task):
    config, algorithm, fid, run = task
    problem = make_problem(config['suite'], fid, config['dimension'])
    seed = int(np.random.SeedSequence([config['seed'], int(config['suite'][-4:]), fid, run]).generate_state(1)[0])
    start = time.perf_counter()
    result = optimize(problem, algorithm, config, seed)
    if result['nfev'] != config['max_fes'] or problem.n_fe != config['max_fes']:
        raise RuntimeError('actual objective calls do not match budget')
    x = np.array(result['x'])
    if not np.isfinite(x).all() or np.any(x < problem.lb) or np.any(x > problem.ub):
        raise RuntimeError('invalid saved solution')
    recomputed = float(problem.evaluate(x))
    if not np.isclose(recomputed, result['fun'], rtol=1e-12, atol=1e-9):
        raise RuntimeError('saved solution mismatch')
    signed = result['fun']-float(problem.f_global)
    if signed < -1e-7:
        raise RuntimeError('solution below declared optimum')
    return dict(algorithm=algorithm, suite=config['suite'], function=fid, run=run,
                seed=seed, optimum=float(problem.f_global), error=max(0., signed),
                signed_error=signed, audit_evaluations=1, recomputed_fitness=recomputed,
                seconds=time.perf_counter()-start, **result)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--suite', choices=['cec2014', 'cec2017', 'cec2022'], default='cec2014')
    p.add_argument('--algorithms', nargs='+', choices=ALL, default=FINAL)
    p.add_argument('--functions', nargs='+', type=int)
    p.add_argument('--runs', type=int, default=20)
    p.add_argument('--dimension', type=int, default=10)
    p.add_argument('--max-fes', type=int, default=100000)
    p.add_argument('--population-size', type=int, default=100)
    p.add_argument('--population-mode', choices=['fixed', 'native'], default='fixed')
    p.add_argument('--seed', type=int, default=20261109)
    p.add_argument('--workers', type=int, default=24)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--resume', action='store_true')
    a = p.parse_args()
    maximum = 12 if a.suite == 'cec2022' else 30
    functions = a.functions or [i for i in range(1, maximum+1) if not (a.suite == 'cec2017' and i == 2)]
    if (len(set(functions)) != len(functions) or any(f < 1 or f > maximum for f in functions)
            or len(set(a.algorithms)) != len(a.algorithms) or a.population_size < 18
            or a.max_fes < a.population_size or a.runs < 1 or a.workers < 1 or a.dimension != 10
            or a.seed < 0 or a.suite == 'cec2017' and 2 in functions):
        p.error('invalid experiment settings')
    code_files = sorted(Path(__file__).parent.glob('*.py'))
    module = dict(cec2014=cec2014, cec2017=cec2017, cec2022=cec2022)[a.suite]
    data = Path(module.__file__).parent/f'data_{a.suite[-4:]}'
    config = dict(suite=a.suite, algorithms=sorted(a.algorithms), functions=sorted(functions),
                  runs=a.runs, dimension=a.dimension, max_fes=a.max_fes,
                  population_size=a.population_size, population_mode=a.population_mode, seed=a.seed,
                  benchmark='unmodified opfunu 1.0.4', author='殷明骏', student_id='202483890029',
                  versions={name: importlib.metadata.version(name) for name in ['numpy', 'opfunu', 'scipy']},
                  python=platform.python_version(), source_sha256={f.name: digest(f) for f in code_files},
                  benchmark_module_sha256=digest(module.__file__),
                  benchmark_data_sha256={f.name: digest(f) for f in sorted(data.glob('*.txt'))
                                         if '_D10' in f.name or f.name.startswith('shift')})
    output = a.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output/'manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if not a.resume or manifest['config'] != config:
            p.error('existing output requires --resume with identical code/environment/config')
    else:
        if any(output.iterdir()):
            p.error('new result directory must be empty')
        manifest = dict(config=config, started_utc=datetime.now(timezone.utc).isoformat())
        write_json(manifest_path, manifest)
    tasks = []
    for algorithm in a.algorithms:
        for fid in functions:
            for run in range(1, a.runs+1):
                target = output/algorithm/f'F{fid:02d}_run{run:02d}.json'
                if target.exists():
                    row = json.loads(target.read_text())
                    if (row['algorithm'], row['function'], row['run'], row['nfev']) != (algorithm, fid, run, a.max_fes):
                        raise ValueError(f'invalid existing record: {target}')
                else:
                    tasks.append((config, algorithm, fid, run))
    tasks.sort(key=lambda t: (t[3], -t[2], t[1]))
    log = (output/'experiment.log').open('a', buffering=1)
    def emit(message):
        print(message, flush=True)
        log.write(message+'\n')
    emit(f'PENDING {len(tasks)} workers={a.workers}')
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        futures = [pool.submit(run_one, task) for task in tasks]
        for done, future in enumerate(as_completed(futures), 1):
            row = future.result()
            write_json(output/row['algorithm']/f"F{row['function']:02d}_run{row['run']:02d}.json", row)
            emit(f"RESULT algorithm={row['algorithm']} function=F{row['function']:02d} run={row['run']:02d} "
                 f"seed={row['seed']} fes={row['nfev']} fitness={row['fun']:.12e} error={row['error']:.12e} "
                 f"seconds={row['seconds']:.3f} completed={done}/{len(tasks)}")
    manifest.update(completed_utc=datetime.now(timezone.utc).isoformat(),
                    record_count=len(a.algorithms)*len(functions)*a.runs)
    write_json(manifest_path, manifest)
    emit(f"COMPLETE {manifest['record_count']}")
    log.close()


if __name__ == '__main__':
    main()
