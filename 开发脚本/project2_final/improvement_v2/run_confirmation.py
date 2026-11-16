"""Separate revision experiment runner; frozen sources are read-only. Author: 殷明骏."""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import time
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'code'))
import run_project2 as frozen
import dls_combined
NEW_ALGORITHMS = ["DLC", "DUAL", "DLC_no_phase", "DLC_no_learning", "DUAL_no_phase", "DUAL_no_learning"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    temp.replace(path)


def one(task):
    config, algorithm, fid, run = task
    problem = frozen.make_problem('cec2014', fid, 10)
    seed = int(np.random.SeedSequence([config['seed'], 2014, fid, run]).generate_state(1)[0])
    start = time.perf_counter()
    if algorithm in NEW_ALGORITHMS:
        r = dls_combined.minimize(problem.evaluate, np.column_stack((problem.lb, problem.ub)),
                                 max_fes=config['max_fes'], population_size=100,
                                 min_population_size=100,seed=seed,
                                 revision='cls' if algorithm.startswith('DLC') else 'dual',
                                 variant='no_two_phase' if algorithm.endswith('_no_phase') else
                                         'no_learning' if algorithm.endswith('_no_learning') else 'dls_de')
        result = dict(x=r.x.tolist(),fun=r.fun,nfev=r.nfev,history=r.history,diagnostics=r.diagnostics)
    else:
        result = frozen.optimize(problem, algorithm, config, seed)
    assert result['nfev'] == problem.n_fe == config['max_fes']
    x = np.asarray(result['x'])
    assert np.isfinite(x).all() and np.all(x >= problem.lb) and np.all(x <= problem.ub)
    actual = float(problem.evaluate(x))
    assert np.isclose(actual, result['fun'], rtol=1e-12, atol=1e-9)
    signed = result['fun']-float(problem.f_global)
    assert signed >= -1e-7
    return dict(algorithm=algorithm, suite='cec2014', function=fid, run=run,
                seed=seed, optimum=float(problem.f_global), error=max(0., signed),
                signed_error=signed, audit_evaluations=1, recomputed_fitness=actual,
                seconds=time.perf_counter()-start, **result)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--algorithms', nargs='+', choices=frozen.ALL+NEW_ALGORITHMS, required=True)
    p.add_argument('--functions', nargs='+', type=int, default=list(range(1, 31)))
    p.add_argument('--runs', type=int, default=20)
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--max-fes', type=int, default=100000)
    p.add_argument('--workers', type=int, default=24)
    p.add_argument('--initial-workers',type=int)
    p.add_argument('--competing-pid',type=int,default=0)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--resume', action='store_true')
    a = p.parse_args()
    if (a.runs < 1 or a.workers < 1 or a.max_fes < 100 or a.seed < 0
            or a.initial_workers is not None and not 1<=a.initial_workers<=a.workers
            or len(set(a.algorithms)) != len(a.algorithms)
            or len(set(a.functions)) != len(a.functions)
            or any(f < 1 or f > 30 for f in a.functions)):
        p.error('invalid settings')
    sources = list((ROOT/'code').glob('*.py')) + [Path(__file__), Path(dls_combined.__file__)]
    config = dict(suite='cec2014', algorithms=sorted(a.algorithms), functions=sorted(a.functions),
                  runs=a.runs, seed=a.seed, dimension=10, population_size=100,
                  population_mode='fixed', max_fes=a.max_fes, benchmark='unmodified opfunu 1.0.4',
                  versions={k: importlib.metadata.version(k) for k in ('numpy','scipy','opfunu')},
                  python=platform.python_version(),
                  source_sha256={str(s.relative_to(ROOT)):sha(s) for s in sources})
    output = a.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    path = output/'manifest.json'
    if path.exists():
        manifest = json.loads(path.read_text())
        if not a.resume or manifest['config'] != config:
            p.error('resume requires identical sources and configuration')
    else:
        if any(output.iterdir()): p.error('new directory must be empty')
        manifest = dict(author='殷明骏', config=config, started_utc=datetime.now(timezone.utc).isoformat())
        save(path, manifest)
    tasks = []
    for run in range(1, a.runs+1):
        for fid in reversed(a.functions):
            for algorithm in a.algorithms:
                target = output/algorithm/f'F{fid:02d}_run{run:02d}.json'
                if not target.exists(): tasks.append((config, algorithm, fid, run))
                else:
                    r = json.loads(target.read_text())
                    expected_seed = int(np.random.SeedSequence([a.seed, 2014, fid, run]).generate_state(1)[0])
                    assert (r['algorithm'],r['function'],r['run'],r['seed'],r['nfev']) == (algorithm,fid,run,expected_seed,a.max_fes)
    with (output/'experiment.log').open('a', buffering=1) as log:
        def emit(s):
            print(s, flush=True)
            log.write(s+'\n')
        emit(f'PENDING {len(tasks)} workers={a.workers}')
        def worker_cap():
            if not a.competing_pid:return a.workers
            try:
                proc=Path('/proc')/str(a.competing_pid)
                live=(proc/'stat').read_text().split()[2]!='Z'
                command=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode()
                same_job=(proc/'cwd').resolve()==ROOT/'improvement' and '--output results/validation' in command
                return (a.initial_workers or a.workers) if live and same_job else a.workers
            except (FileNotFoundError,ProcessLookupError):return a.workers
        with ProcessPoolExecutor(max_workers=a.workers) as pool:
            pending=set();submitted=done=0;last_cap=None
            while submitted<len(tasks) or pending:
                cap=worker_cap()
                if cap!=last_cap:emit(f'WORKER_CAP {cap}');last_cap=cap
                while len(pending)<cap and submitted<len(tasks):
                    pending.add(pool.submit(one,tasks[submitted]));submitted+=1
                complete,_=wait(pending,timeout=5,return_when=FIRST_COMPLETED)
                for future in complete:
                    pending.remove(future);r=future.result();done+=1
                    save(output/r['algorithm']/f"F{r['function']:02d}_run{r['run']:02d}.json",r)
                    emit(f"RESULT algorithm={r['algorithm']} function=F{r['function']:02d} run={r['run']:02d} seed={r['seed']} fes={r['nfev']} error={r['error']:.12e} completed={done}/{len(tasks)}")
        manifest.update(completed_utc=datetime.now(timezone.utc).isoformat(),record_count=len(a.algorithms)*len(a.functions)*a.runs)
        save(path, manifest)
        emit(f"COMPLETE {manifest['record_count']}")


if __name__ == '__main__': main()
