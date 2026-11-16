"""Run CEC2014 experiments with deterministic seeds and audited resume."""
import bootstrap
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import time
import numpy as np
from opfunu.cec_based import cec2014
from dls_de import minimize, initial_population_size, VARIANTS

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    path = Path(path)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    tmp.replace(path)


def run_one(task):
    variant, fid, run, config = task
    problem = getattr(cec2014, f"F{fid}2014")(ndim=config["dimension"])
    # The same (suite,function,run) seed across variants gives identical initialization.
    seed = int(np.random.SeedSequence([config["seed"], 2014, fid, run]).generate_state(1)[0])
    start = time.perf_counter()
    result = minimize(problem.evaluate, np.column_stack((problem.lb, problem.ub)),
                      variant=variant, max_fes=config["max_fes"], seed=seed,
                      population_size=config["population_size"], gate=config["gate"])
    assert result.nfev == problem.n_fe == config["max_fes"]
    signed_error = result.fun - float(problem.f_global)
    if signed_error < -1e-8:
        raise ValueError(f"F{fid} below optimum: {signed_error}")
    # This call is a post-run audit, explicitly excluded from the optimization budget.
    recomputed = float(problem.evaluate(result.x))
    assert np.isclose(recomputed, result.fun, rtol=1e-12, atol=1e-9)
    return dict(algorithm=variant, function=fid, run=run, seed=seed, name=problem.name,
                best_fitness=result.fun, optimum=float(problem.f_global),
                error=max(0.0, signed_error), signed_error=signed_error,
                nfev=result.nfev, audit_evaluations=1, recomputed_fitness=recomputed,
                best_x=result.x.tolist(), history=result.history,
                diagnostics=result.diagnostics, seconds=time.perf_counter() - start)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--algorithms", nargs="+", choices=VARIANTS, default=["dls_de"])
    parser.add_argument("--functions", type=int, nargs="+", default=list(range(1, 31)))
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--dimension", type=int, default=10)
    parser.add_argument("--max-fes", type=int)
    parser.add_argument("--population-size", type=int)
    parser.add_argument("--seed", type=int, default=20261030)
    parser.add_argument("--gate", choices=["pseudocode", "text"], default="pseudocode")
    parser.add_argument("--workers", type=int, default=min(16, os.cpu_count() or 1))
    parser.add_argument("--output", type=Path, default=ROOT / "results")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.dimension not in (10, 20, 30, 50, 100):
        parser.error("CEC2014 dimension must be 10,20,30,50,100")
    np0 = args.population_size or initial_population_size(args.dimension)
    budget = args.max_fes or 10000 * args.dimension
    if (args.runs < 2 or args.workers < 1 or args.seed < 0 or np0 < 4 or budget < np0
            or len(set(args.functions)) != len(args.functions)
            or len(set(args.algorithms)) != len(args.algorithms)
            or any(i not in range(1, 31) for i in args.functions)):
        parser.error("invalid experiment settings")
    config = dict(algorithms=sorted(args.algorithms), functions=sorted(args.functions),
                  runs=args.runs, dimension=args.dimension, max_fes=budget,
                  population_size=np0, seed=args.seed, gate=args.gate,
                  suite="CEC2014", H=6, p=.11, archive_ratio=1.6, NP_min=4,
                  lambda_sigma=.1, ST=30, tau=.3, sigma_initial=.05, SR_initial=.5,
                  phase_fraction=.3, boundary="parent-bound midpoint", selection="<=",
                  versions={p: importlib.metadata.version(p) for p in ("numpy", "opfunu")},
                  python=platform.python_version(),
                  source_sha256={p: digest(ROOT / p) for p in ("dls_de.py", "run_experiments.py", "bootstrap.py")})
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / "manifest.json"
    if manifest_path.exists():
        if not args.resume:
            parser.error("results exist; choose a new output or --resume")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["config"] != config:
            parser.error("resume config, code or environment differs")
    else:
        if any(args.output.iterdir()):
            parser.error("new experiment output must be empty")
        manifest = dict(config=config, started_utc=datetime.now(timezone.utc).isoformat())
        write_json(manifest_path, manifest)
    log = (args.output / "experiment.log").open("a", encoding="utf-8", buffering=1)

    def emit(message):
        print(message, flush=True)
        log.write(message + "\n")

    tasks = []
    for algorithm in config["algorithms"]:
        (args.output / algorithm).mkdir(exist_ok=True)
        for fid in config["functions"]:
            for run in range(1, args.runs + 1):
                target = args.output / algorithm / f"F{fid:02d}_run{run:02d}.json"
                if target.exists():
                    row = json.loads(target.read_text(encoding="utf-8"))
                    if (row["algorithm"], row["function"], row["run"], row["nfev"]) != (algorithm, fid, run, budget):
                        raise ValueError(f"invalid resumed record: {target}")
                else:
                    tasks.append((algorithm, fid, run, config))
    # Spread expensive composition functions throughout the run.
    tasks.sort(key=lambda t: (t[2], -t[1], t[0]))
    emit("CONFIG " + json.dumps(config, sort_keys=True))
    emit(f"PENDING {len(tasks)} workers={args.workers}")
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, task) for task in tasks]
        for done, future in enumerate(as_completed(futures), 1):
            row = future.result()
            write_json(args.output / row["algorithm"] / f"F{row['function']:02d}_run{row['run']:02d}.json", row)
            emit(f"RESULT algorithm={row['algorithm']} function=F{row['function']:02d} run={row['run']:02d} "
                 f"seed={row['seed']} fes={row['nfev']} error={row['error']:.12e} "
                 f"seconds={row['seconds']:.3f} completed={done}/{len(tasks)}")
    manifest.update(completed_utc=datetime.now(timezone.utc).isoformat(),
                    result_count=len(config["algorithms"]) * len(config["functions"]) * args.runs)
    write_json(manifest_path, manifest)
    emit("COMPLETE " + str(manifest["result_count"]))
    log.close()


if __name__ == "__main__":
    main()
