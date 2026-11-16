"""Run the actual opfunu CEC2014 functions; save one JSON per independent run."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import time

# Prevent each process from starting a separate BLAS thread pool.
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ.setdefault("MPLCONFIGDIR", "/tmp/project1-matplotlib")

import numpy as np
from opfunu.cec_based import cec2014
from de import minimize


def run_one(task):
    function_id, run, config = task
    problem = getattr(cec2014, f"F{function_id}2014")(ndim=config["dimension"])
    seed = int(np.random.SeedSequence([config["seed"], function_id, run]).generate_state(1)[0])
    start = time.perf_counter()
    result = minimize(problem.evaluate, np.column_stack([problem.lb, problem.ub]),
                      population_size=config["population_size"], max_fes=config["max_fes"],
                      f=config["f"], cr=config["cr"], seed=seed)
    assert result.nfev == config["max_fes"] == problem.n_fe
    error = result.fun - float(problem.f_global)
    if error < -1e-8:
        raise RuntimeError(f"F{function_id}: value below advertised optimum: {error}")
    return dict(function=function_id, name=problem.name, run=run, seed=seed,
                best_fitness=result.fun, optimum=float(problem.f_global),
                error=abs(error), signed_error=error, nfev=result.nfev,
                best_x=result.x.tolist(), history=result.history,
                seconds=time.perf_counter() - start)


def source_hashes():
    root = Path(__file__).parent
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ("de.py", "run_experiments.py")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--functions", type=int, nargs="+", default=list(range(1, 31)))
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--dimension", type=int, default=10)
    parser.add_argument("--population-size", type=int, default=100)
    parser.add_argument("--max-fes", type=int, default=100000)
    parser.add_argument("--f", type=float, default=0.5)
    parser.add_argument("--cr", type=float, default=0.9)
    parser.add_argument("--seed", type=int, default=20261026)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "results")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if (args.runs < 1 or args.workers < 1 or args.seed < 0
            or len(set(args.functions)) != len(args.functions)
            or any(i not in range(1, 31) for i in args.functions)
            or args.dimension not in (10, 20, 30, 50, 100)
            or args.population_size < 4 or args.max_fes < args.population_size
            or not 0 < args.f <= 2 or not 0 <= args.cr <= 1):
        parser.error("invalid functions, dimensions, runs, workers, seed, NP, FE budget, F or CR")
    config = {key: getattr(args, key) for key in
              ("dimension", "population_size", "max_fes", "f", "cr", "seed", "runs")}
    config.update(functions=sorted(args.functions), algorithm="DE/rand/1/bin",
                  boundary="clip", selection="strict", updating="generational",
                  versions={p: importlib.metadata.version(p) for p in ("numpy", "opfunu")},
                  python=platform.python_version(), source_sha256=source_hashes())
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = args.output / "manifest.json"
    if manifest.exists():
        if not args.resume:
            parser.error("output already exists; use --resume or a new --output directory")
        old = json.loads(manifest.read_text())
        if old["config"] != config:
            parser.error("resume configuration/source/environment differs from manifest")
    else:
        if any(args.output.iterdir()):
            parser.error("output directory must be empty for a new experiment")
        manifest.write_text(json.dumps(dict(config=config, workers=args.workers,
                            started_utc=datetime.now(timezone.utc).isoformat()), indent=2))
    tasks = []
    for function_id in config["functions"]:
        for run in range(1, args.runs + 1):
            target = args.output / f"F{function_id:02d}_run{run:02d}.json"
            if target.exists():
                row = json.loads(target.read_text())
                if row["function"] != function_id or row["run"] != run or row["nfev"] != args.max_fes:
                    parser.error(f"invalid saved record: {target}")
            else:
                tasks.append((function_id, run, config))
    print(f"CONFIG {json.dumps(config, sort_keys=True)}", flush=True)
    print(f"PENDING {len(tasks)} / {len(config['functions']) * args.runs}", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, task) for task in tasks]
        for completed, future in enumerate(as_completed(futures), 1):
            row = future.result()
            target = args.output / f"F{row['function']:02d}_run{row['run']:02d}.json"
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps(row, indent=2, allow_nan=False))
            temporary.replace(target)
            print(f"RESULT function=F{row['function']:02d} run={row['run']:02d} "
                  f"seed={row['seed']} fes={row['nfev']} error={row['error']:.12e} "
                  f"seconds={row['seconds']:.3f} completed={completed}/{len(tasks)}", flush=True)
    data = json.loads(manifest.read_text())
    data["completed_utc"] = datetime.now(timezone.utc).isoformat()
    manifest.write_text(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
