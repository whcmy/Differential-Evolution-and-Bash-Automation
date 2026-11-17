"""Read-only probe of opfunu against a separately packaged C++ evaluator."""
import bootstrap
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".audit_vendor"))
import hashlib
import json
import csv
import importlib.metadata
import numpy as np
import minionpy
from opfunu.cec_based import cec2014


def main():
    out = ROOT / "reference"
    rows = []
    rng = np.random.default_rng(2014)
    random_points = rng.uniform(-100, 100, size=(20, 10))
    for fid in range(1, 31):
        f = getattr(cec2014, f"F{fid}2014")(ndim=10)
        ref = minionpy.CEC2014Functions(fid, 10)
        points = np.concatenate((random_points, [np.zeros(10), f.x_global]))
        a = np.array([f.evaluate(x) for x in points])
        b = np.array(ref(points.tolist()))
        mismatch = ~np.isclose(a, b, rtol=1e-10, atol=1e-8)
        rows.append(dict(function=fid, points=len(points), mismatches=int(mismatch.sum()),
                         max_absolute_difference=float(np.abs(a-b).max()),
                         max_relative_difference=float(np.max(np.abs(a-b)/np.maximum(1., np.abs(b)))),
                         opfunu_at_zero=float(a[-2]), reference_at_zero=float(b[-2]),
                         opfunu_at_known_optimum=float(a[-1]), reference_at_known_optimum=float(b[-1])))
    with (out / "benchmark_pointwise_audit.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0])
        writer.writeheader(); writer.writerows(rows)
    f29 = cec2014.F292014(ndim=10)
    actual = [f29.g0.f_matrix, f29.g1.f_matrix, f29.g2.f_matrix]
    structural = dict(F29_component_rotation_matches_own_M29_block=[bool(np.array_equal(m, f29.f_matrix[i*10:(i+1)*10])) for i, m in enumerate(actual)],
                      official_cf07_lines="reference/official_cec14_test_func.cpp:1137-1150",
                      opfunu_lines=".vendor/opfunu/cec_based/cec2014.py:1188-1197",
                      official_source_url="https://github.com/P-N-Suganthan/CEC2014/blob/master/cec14-c-code.zip")
    data = dict(opfunu=importlib.metadata.version("opfunu"), minionpy=minionpy.__version__,
                seed=2014, dimension=10, random_points=20, additional_points=["zero", "opfunu.x_global"],
                rtol=1e-10, atol=1e-8, functions_with_mismatches=[r["function"] for r in rows if r["mismatches"]],
                structural=structural,
                source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                               [out / "cec14-c-code.zip", out / "official_cec14_test_func.cpp", ROOT / ".vendor/opfunu/cec_based/cec2014.py"]},
                limitation="Finite point probes are not a proof of global equivalence; the C++ evaluator is MinionPy's packaged reference, not the paper authors' MATLAB run.")
    (out / "benchmark_audit.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
