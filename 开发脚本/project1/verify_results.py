"""Independent full-record audit, including reevaluation with unmodified opfunu."""
import argparse
from collections import Counter
import csv
from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import re

os.environ.setdefault("MPLCONFIGDIR", "/tmp/project1-matplotlib")
import numpy as np
from opfunu.cec_based import cec2014
from summarize import load_records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).parent
    parser.add_argument("--results", type=Path, default=root / "results")
    parser.add_argument("--output", type=Path, default=root / "output")
    parser.add_argument("--log", type=Path, default=root / "experiment.log")
    args = parser.parse_args()
    manifest, rows = load_records(args.results)
    config = manifest["config"]
    if config["functions"] != list(range(1, 31)) or config["runs"] != 20 or config["dimension"] != 10:
        raise ValueError("the final Project1 deliverable requires F1-F30, 10D, 20 runs")
    if config["max_fes"] != 100000:
        raise ValueError("final experiment does not use the documented 10000D budget")
    for name, expected in config["source_sha256"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"source differs from executed version: {name}")
    rechecked = 0
    for row in rows:
        problem = getattr(cec2014, f"F{row['function']}2014")(ndim=config["dimension"])
        if abs(problem.evaluate(problem.x_global) - problem.f_global) > 1e-7:
            raise ValueError("advertised optimum failed")
        recomputed = float(problem.evaluate(np.array(row["best_x"])))
        if not math.isclose(recomputed, row["best_fitness"], rel_tol=1e-13, abs_tol=1e-10):
            raise ValueError(f"saved decision vector disagrees with fitness: {row}")
        seed = int(np.random.SeedSequence([config["seed"], row["function"], row["run"]]).generate_state(1)[0])
        if seed != row["seed"]:
            raise ValueError("incorrect per-run seed")
        rechecked += 1
    table_checks = 0
    for filename, measure in (("summary_error.csv", "error"), ("summary_fitness.csv", "best_fitness")):
        summary = list(csv.DictReader((args.output / filename).open()))
        if len(summary) != 30:
            raise ValueError("incorrect summary row count")
        for fid, item in enumerate(summary, 1):
            if item["function"] != f"F{fid:02d}" or int(item["runs"]) != 20:
                raise ValueError("incorrect summary function/run identification")
            values = sorted(r[measure] for r in rows if r["function"] == fid)
            # Recompute independently in decimal arithmetic to avoid cancellation
            # and do not reuse the summary's statistics.mean/variance functions.
            with localcontext() as context:
                context.prec = 100
                decimal_values = [Decimal.from_float(v) for v in values]
                decimal_mean = sum(decimal_values) / Decimal(20)
                decimal_variance = sum((v - decimal_mean) ** 2 for v in decimal_values) / Decimal(19)
                mean, variance = float(decimal_mean), float(decimal_variance)
            expected = dict(best=values[0], median=(values[9] + values[10]) / 2,
                            mean=mean, worst=values[-1], variance=variance, std=math.sqrt(variance))
            for key, value in expected.items():
                if not math.isclose(float(item[key]), value, rel_tol=1e-10, abs_tol=1e-18):
                    raise ValueError(f"incorrect {filename} {fid} {key}")
                table_checks += 1
    for filename, expected_hash in json.loads((args.output / "raw_sha256.json").read_text()).items():
        if hashlib.sha256((args.results / filename).read_bytes()).hexdigest() != expected_hash:
            raise ValueError("raw record changed after summary")
    log = args.log.read_text()
    matches = re.findall(r"RESULT function=F(\d+) run=(\d+) seed=(\d+) fes=(\d+) error=([0-9.eE+-]+)", log)
    counts = Counter((int(fid), int(run)) for fid, run, *_ in matches)
    expected_ids = {(r["function"], r["run"]) for r in rows}
    if set(counts) != expected_ids or any(count != 1 for count in counts.values()):
        raise ValueError("log does not contain exactly one result for each saved run")
    records = {(r["function"], r["run"]): r for r in rows}
    for fid, run, seed, fes, error in matches:
        row = records[int(fid), int(run)]
        if (int(seed) != row["seed"] or int(fes) != row["nfev"]
                or not math.isclose(float(error), row["error"], rel_tol=1e-11, abs_tol=1e-20)):
            raise ValueError("log record disagrees with JSON")
    result = dict(status="passed", functions=30, dimensions=10, independent_runs=600,
                  fes_per_run=100000, total_fes=sum(r["nfev"] for r in rows),
                  saved_solutions_reevaluated=rechecked, statistics_cells_checked=table_checks,
                  log_records_checked=len(matches), source_hashes_checked=True,
                  raw_record_hashes_checked=True, history_monotonicity_checked=True,
                  scope="Record integrity and consistency with opfunu 1.0.4; not official CEC equivalence or paper reproduction.")
    (args.output / "verification.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
