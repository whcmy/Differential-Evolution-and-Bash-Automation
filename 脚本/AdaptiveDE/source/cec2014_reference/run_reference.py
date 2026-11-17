"""Independent C++ CEC2014 check; this calls our DLS-DE, not Minion's optimizers.

The protocol's opfunu results are kept in separate directories. MinionPy 1.9.1 is
an optional audit dependency, not a replacement of the requested opfunu runs.
"""
import bootstrap
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
if (ROOT / ".audit_vendor").exists():
    sys.path.insert(0, str(ROOT / ".audit_vendor"))
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import importlib.metadata
import json
import platform
import time
import numpy as np
import minionpy
from dls_de import minimize
from run_experiments import write_json, digest


def run_one(task):
    fid, run, config = task
    reference = minionpy.CEC2014Functions(fid, 10)
    calls = 0
    def objective(x):
        nonlocal calls
        calls += 1
        return float(reference([x.tolist()])[0])
    seed = int(np.random.SeedSequence([config["seed"], 2014, fid, run]).generate_state(1)[0])
    start = time.perf_counter()
    r = minimize(objective, [(-100., 100.)] * 10, max_fes=100000, seed=seed)
    assert calls == r.nfev == 100000
    value = objective(r.x)
    assert value == r.fun
    return dict(algorithm="dls_de", function=fid, run=run, seed=seed,
                name=f"CEC2014 F{fid} (MinionPy C++ reference)", best_fitness=r.fun,
                optimum=100. * fid, signed_error=r.fun - 100. * fid,
                error=max(0., r.fun - 100. * fid), nfev=r.nfev,
                audit_evaluations=1, recomputed_fitness=value, best_x=r.x.tolist(),
                history=r.history, diagnostics=r.diagnostics,
                seconds=time.perf_counter() - start)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "results_reference")
    args = parser.parse_args()
    # Match all optimizer settings and random seeds to the baseline experiment.
    source = json.loads((ROOT / "results/manifest.json").read_text(encoding="utf-8"))
    config = dict(source["config"])
    config.update(evaluator="minionpy_cpp", evaluator_version=importlib.metadata.version("minionpy"))
    config["source_sha256"] = dict(config["source_sha256"], run_reference_py=digest(__file__))
    # Use the actual filename so the standard verification path can check it.
    config["source_sha256"]["run_reference.py"] = config["source_sha256"].pop("run_reference_py")
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_file = args.output / "manifest.json"
    if manifest_file.exists():
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        if not args.resume or manifest["config"] != config:
            raise ValueError("existing reference config differs, or --resume missing")
    else:
        if any(args.output.iterdir()):
            raise ValueError("output must be empty")
        manifest = dict(config=config, started_utc=datetime.now(timezone.utc).isoformat())
        write_json(manifest_file, manifest)
    target_dir = args.output / "dls_de"
    target_dir.mkdir(exist_ok=True)
    tasks = [(fid, run, config) for run in range(1, 21) for fid in range(1, 31)
             if not (target_dir / f"F{fid:02d}_run{run:02d}.json").exists()]
    with (args.output / "experiment.log").open("a", encoding="utf-8", buffering=1) as log:
        log.write("CONFIG " + json.dumps(config) + "\n")
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for done, future in enumerate(as_completed([pool.submit(run_one, task) for task in tasks]), 1):
                row = future.result()
                write_json(target_dir / f"F{row['function']:02d}_run{row['run']:02d}.json", row)
                line = (f"RESULT function=F{row['function']:02d} run={row['run']:02d} seed={row['seed']} "
                        f"fes=100000 error={row['error']:.12e} seconds={row['seconds']:.3f} done={done}/{len(tasks)}")
                log.write(line + "\n")
                if done % 30 == 0:
                    print(line, flush=True)
        manifest.update(completed_utc=datetime.now(timezone.utc).isoformat(), result_count=600)
        write_json(manifest_file, manifest)
        log.write("COMPLETE 600\n")


if __name__ == "__main__":
    main()
