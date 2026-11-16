"""Verify raw experiments, summarize ranks/statistics and plot actual best runs."""
import bootstrap
import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import numpy as np
from scipy.stats import rankdata, friedmanchisquare, mannwhitneyu

ROOT = Path(__file__).resolve().parent
LABELS = dict(dls_de="DLS-DE", no_learning="Without learning", no_two_phase="Without two-phase F",
              fixed_sigma="Fixed sigma F", fitness_weights="Fitness weights", binomial="Binomial crossover",
              de="Basic DE")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def save_csv(path, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def holm(pvalues):
    order = np.argsort(pvalues)
    adjusted = np.empty(len(order))
    running = 0.
    for i, idx in enumerate(order):
        running = max(running, min(1., (len(order) - i) * pvalues[idx]))
        adjusted[idx] = running
    return adjusted


def tolerant_ranks(values):
    """Tie numerical noise, also at nonzero composition-function error floors."""
    values = np.asarray(values, dtype=float)
    clustered = values.copy()
    anchor = None
    for idx in np.argsort(values):
        if anchor is None or not np.isclose(values[idx], anchor, rtol=1e-10, atol=1e-8):
            anchor = values[idx]
        clustered[idx] = anchor
    return rankdata(clustered, method="average")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", nargs="+", type=Path, default=[ROOT / "results"])
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    records, hashes, configs, validations = {}, {}, [], []
    from opfunu.cec_based import cec2014
    problems = {}
    for directory in args.results:
        manifest = read_json(directory / "manifest.json")
        config = manifest["config"]
        if "completed_utc" not in manifest:
            raise ValueError(f"incomplete experiment: {directory}")
        configs.append(config)
        for filename, digest in config["source_sha256"].items():
            if hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() != digest:
                raise ValueError(f"experiment code differs: {filename}")
        for algorithm in config["algorithms"]:
            for fid in config["functions"]:
                for run in range(1, config["runs"] + 1):
                    path = directory / algorithm / f"F{fid:02d}_run{run:02d}.json"
                    row = read_json(path)
                    key = (algorithm, fid, run)
                    if key in records:
                        raise ValueError(f"duplicate record: {key}")
                    assert (row["algorithm"], row["function"], row["run"]) == key
                    assert row["nfev"] == config["max_fes"]
                    expected_seed = int(np.random.SeedSequence([config["seed"], 2014, fid, run]).generate_state(1)[0])
                    assert row["seed"] == expected_seed
                    evaluator = config.get("evaluator", "opfunu")
                    problem_key = (evaluator, fid, config["dimension"])
                    if problem_key not in problems:
                        if evaluator == "minionpy_cpp":
                            import sys
                            sys.path.insert(0, str(ROOT / ".audit_vendor"))
                            import minionpy
                            assert minionpy.__version__ == config["evaluator_version"]
                            problems[problem_key] = minionpy.CEC2014Functions(fid, config["dimension"])
                        else:
                            problems[problem_key] = getattr(cec2014, f"F{fid}2014")(ndim=config["dimension"])
                    problem = problems[problem_key]
                    vector = np.array(row["best_x"])
                    assert len(vector) == config["dimension"]
                    lower, upper, optimum = ((-100., 100., fid * 100.) if evaluator == "minionpy_cpp" else
                                             (problem.lb, problem.ub, problem.f_global))
                    assert np.isfinite(vector).all() and ((vector >= lower) & (vector <= upper)).all()
                    value = float(problem([vector.tolist()])[0]) if evaluator == "minionpy_cpp" else float(problem.evaluate(vector))
                    assert np.isclose(value, row["best_fitness"], atol=1e-9, rtol=1e-12)
                    assert row["optimum"] == float(optimum)
                    assert np.isclose(row["error"], max(0., value - optimum), atol=1e-10)
                    h = np.asarray(row["history"])
                    assert h[0, 0] == config["population_size"] and h[-1, 0] == config["max_fes"]
                    assert np.all(np.diff(h[:, 0]) > 0) and np.all(np.diff(h[:, 1]) <= 0)
                    assert h[-1, 1] == row["best_fitness"]
                    assert row["diagnostics"]["initial_population"] == config["population_size"]
                    diag = row["diagnostics"]
                    assert diag["accepted"] >= diag["strict_improvements"] >= 0
                    if algorithm == "de":
                        assert diag["final_population"] == config["population_size"]
                    else:
                        assert diag["phase1_trials"] + diag["phase2_trials"] == config["max_fes"] - config["population_size"]
                        if config["max_fes"] > config["population_size"]:
                            assert diag["final_population"] == 4
                    if algorithm == "no_learning":
                        assert diag["learning_trials"] == diag["learning_records"] == 0
                    if algorithm == "no_two_phase":
                        assert diag["phase1_trials"] == 0
                    if algorithm == "fixed_sigma":
                        assert diag["final_sigma"] == .05
                    hashes[f"{directory.name}/{algorithm}/{path.name}"] = hashlib.sha256(path.read_bytes()).hexdigest()
                    records[key] = row
        validations.append(dict(directory=str(directory.resolve()), results=len(config["algorithms"]) * len(config["functions"]) * config["runs"], complete=True))
    # All comparison panels must use matching protocols.
    for config in configs[1:]:
        for key in ("dimension", "max_fes", "population_size", "runs", "seed", "functions", "gate", "versions"):
            if config[key] != configs[0][key]:
                raise ValueError(f"comparison protocol differs: {key}")
        if config.get("evaluator", "opfunu") != configs[0].get("evaluator", "opfunu"):
            raise ValueError("cannot pool different benchmark evaluators")
    algorithms = sorted({key[0] for key in records}, key=lambda s: (s != "dls_de", s == "de", s))
    functions = configs[0]["functions"]
    runs = configs[0]["runs"]
    summary, ranks_by_function, groups = [], [], {}
    for fid in functions:
        means = []
        for algorithm in algorithms:
            rows = [records[(algorithm, fid, r)] for r in range(1, runs + 1)]
            groups[(algorithm, fid)] = rows
            errors = np.array([r["error"] for r in rows])
            means.append(float(errors.mean()))
            summary.append(dict(function=fid, algorithm=algorithm, runs=runs,
                                best=float(errors.min()), median=float(np.median(errors)),
                                mean=float(errors.mean()), worst=float(errors.max()),
                                std=float(errors.std(ddof=1)), variance=float(errors.var(ddof=1)),
                                rank=0., mean_seconds=float(np.mean([r["seconds"] for r in rows])),
                                learning_trials=sum(r["diagnostics"]["learning_trials"] for r in rows)))
        # Preserve raw means; avoid spurious ranks from floating-point floor noise.
        ranks = tolerant_ranks(means)
        ranks_by_function.append(ranks.tolist())
        for row, rank in zip(summary[-len(algorithms):], ranks):
            row["rank"] = float(rank)
    save_csv(args.output / "summary_error.csv", summary)
    flat = [{k: row[k] for k in ("algorithm", "function", "run", "seed", "nfev", "best_fitness", "optimum", "error", "seconds")} for row in records.values()]
    save_csv(args.output / "runs.csv", flat)
    mean_ranks = np.mean(ranks_by_function, axis=0)
    ranking = sorted([dict(algorithm=a, mean_rank=float(r)) for a, r in zip(algorithms, mean_ranks)], key=lambda row: row["mean_rank"])
    save_csv(args.output / "ranking.csv", ranking)
    test_rows = []
    for algorithm in algorithms:
        if algorithm == "dls_de":
            continue
        subset = []
        for fid in functions:
            a = np.array([r["error"] for r in groups[("dls_de", fid)]])
            b = np.array([r["error"] for r in groups[(algorithm, fid)]])
            a[a < 1e-8] = 0.; b[b < 1e-8] = 0.
            test = mannwhitneyu(a, b, alternative="two-sided", method="asymptotic")
            subset.append(dict(function=fid, comparator=algorithm, p_raw=float(test.pvalue),
                               p_holm=0., outcome="", practically_equal=bool(np.isclose(a.mean(), b.mean(), rtol=1e-10, atol=1e-8)),
                               mean_dls=float(a.mean()), mean_comparator=float(b.mean())))
        for row, adjusted in zip(subset, holm([r["p_raw"] for r in subset])):
            row["p_holm"] = float(adjusted)
            row["outcome"] = ("tie" if adjusted >= .05 or row["practically_equal"] else
                              "win" if row["mean_dls"] < row["mean_comparator"] else "loss")
        test_rows.extend(subset)
    if test_rows:
        save_csv(args.output / "statistical_tests.csv", test_rows)
    paper = {int(r["function"]): r for r in csv.DictReader((ROOT / "reference/paper_cec2014_10d.csv").open(encoding="utf-8"))}
    comparison = []
    if configs[0]["dimension"] == 10:
        for row in summary:
            if row["algorithm"] != "dls_de":
                continue
            p = paper[row["function"]]
            pm = float(p["paper_mean"])
            rm = row["mean"]
            both_tiny = max(pm, rm) < 1e-8
            factor = None if min(pm, rm) == 0 else max(pm, rm) / min(pm, rm)
            comparison.append(dict(function=row["function"], reproduced_mean=rm, reproduced_std=row["std"],
                                   paper_mean=pm, paper_std=float(p["paper_std"]), reproduced_runs=runs,
                                   paper_runs=51, symmetric_factor=factor,
                                   within_factor_10=bool(both_tiny or (factor is not None and factor <= 10))))
        save_csv(args.output / "paper_comparison.csv", comparison)
    friedman = None
    if len(algorithms) >= 3 and len(functions) >= 3:
        # Use per-function ranks; equivalent to ordering per-function means with ties above.
        columns = np.array(ranks_by_function).T
        ftest = friedmanchisquare(*columns)
        if np.isfinite(ftest.pvalue):
            friedman = dict(statistic=float(ftest.statistic), pvalue=float(ftest.pvalue))
    test_summary = {a: {o: sum(r["comparator"] == a and r["outcome"] == o for r in test_rows)
                        for o in ("win", "tie", "loss")} for a in algorithms if a != "dls_de"}
    data = dict(config=configs[0], algorithms=algorithms, functions=functions, result_count=len(records),
                summary=summary, ranking=ranking, paper_comparison=comparison,
                statistics=test_summary, friedman=friedman,
                paper_within_factor10=sum(r["within_factor_10"] for r in comparison),
                validations=validations)
    data["diagnostics_totals"] = {a: dict(
        learning_trials=sum(r["diagnostics"]["learning_trials"] for r in records.values() if r["algorithm"] == a),
        learning_records=sum(r["diagnostics"]["learning_records"] for r in records.values() if r["algorithm"] == a),
        runs_with_learning=sum(r["diagnostics"]["learning_trials"] > 0 for r in records.values() if r["algorithm"] == a))
        for a in algorithms}
    save_json(args.output / "report_data.json", data)
    save_json(args.output / "analysis_environment.json", dict(python=platform.python_version(),
              versions={p: importlib.metadata.version(p) for p in ("numpy", "scipy", "matplotlib", "opfunu")},
              ranking_tolerance=dict(atol=1e-8, rtol=1e-10),
              source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    save_json(args.output / "raw_sha256.json", hashes)
    save_json(args.output / "verification.json", dict(valid=True, checked_records=len(records),
              optimization_evaluations=sum(r["nfev"] for r in records.values()),
              audit="all final vectors reevaluated; seeds, bounds, budget, trajectory, source hashes checked",
              course_full=functions == list(range(1, 31)) and runs == 20 and configs[0]["dimension"] == 10 and configs[0]["max_fes"] == 100000))
    if not args.no_plots:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
        plot_dir = args.output / "figures"
        plot_dir.mkdir(exist_ok=True)
        chosen = []
        overview, axes = plt.subplots(6, 5, figsize=(18, 18), squeeze=False)
        for fid in functions:
            fig, axs = plt.subplots(1, 2, figsize=(7.5, 4.2))
            for algorithm in algorithms:
                best = min(groups[(algorithm, fid)], key=lambda row: (row["error"], row["run"]))
                h = np.asarray(best["history"])
                chosen.append(dict(function=fid, algorithm=algorithm, run=best["run"], seed=best["seed"], error=best["error"]))
                kwargs = dict(label=LABELS[algorithm], linewidth=1.3, drawstyle="steps-post")
                axs[0].plot(h[:, 0], h[:, 1], **kwargs)
                axs[1].plot(h[:, 0], np.maximum(0., h[:, 1] - best["optimum"]), **kwargs)
                if fid <= 30:
                    axes.flat[fid - 1].plot(h[:, 0], np.maximum(0., h[:, 1] - best["optimum"]), **kwargs)
            axs[0].set(yscale="log", xlabel="Function evaluations", ylabel="Best function value")
            axs[1].set(yscale="symlog", xlabel="Function evaluations", ylabel="Best error")
            axs[1].set_yscale("symlog", linthresh=1e-8)
            for ax in axs:
                ax.grid(True, alpha=.2)
                ax.ticklabel_format(style="sci", axis="x", scilimits=(0, 0))
            fig.suptitle(f"CEC2014 F{fid:02d}  {configs[0]['dimension']}D  best final run per algorithm")
            fig.legend(*axs[0].get_legend_handles_labels(), loc="lower center", ncol=3, fontsize=8)
            fig.tight_layout(rect=(0, .23, 1, .92))
            fig.savefig(plot_dir / f"F{fid:02d}.png", dpi=160)
            plt.close(fig)
            if fid <= 30:
                axes.flat[fid - 1].set_title(f"F{fid:02d}")
                axes.flat[fid - 1].set_yscale("symlog", linthresh=1e-8)
                axes.flat[fid - 1].grid(True, alpha=.2)
        for idx in range(30):
            if idx + 1 not in functions:
                axes.flat[idx].set_visible(False)
        overview.legend(*axs[0].get_legend_handles_labels(), loc="lower center", ncol=4)
        overview.suptitle("CEC2014 best-run error trajectories  horizontal axis: FEs", fontsize=16)
        overview.tight_layout(rect=(0, .04, 1, .97))
        overview.savefig(plot_dir / "overview_error.png", dpi=140)
        plt.close(overview)
        save_csv(args.output / "best_curve_runs.csv", chosen)
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.barh([LABELS[r["algorithm"]] for r in ranking][::-1], [r["mean_rank"] for r in ranking][::-1], color="#315c80")
        ax.set_xlabel("Average rank across 30 functions  lower is better")
        fig.tight_layout()
        fig.savefig(plot_dir / "ranking.png", dpi=170)
        plt.close(fig)
    print(json.dumps(dict(verified=len(records), ranking=ranking, statistics=test_summary,
                          paper_within_factor10=data["paper_within_factor10"]), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
