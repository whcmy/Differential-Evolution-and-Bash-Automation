# Report 1 consistency revision

Author: 殷明骏

The original 600 course runs and their executed optimizer sources remain frozen.

A. Evaluator isolation: replay the unchanged `de.py` on the official CEC2014 C source, with identical 600 seeds, NP=100, F=.5, CR=.9 and 100,000 FEs. Recompute all new solutions. Test 204 input points per function (200 uniform, zero, two box corners and the known shift), retaining all 6,120 probes. This tests finite inputs and does not assert global opfunu equivalence.

B. Same-algorithm literature control: Caraffini and Neri (2019), doi:10.1016/j.swevo.2018.08.013; extended Table 1, dataset doi:10.17632/psp65d2nbc.1. Use their non-rotated CEC2014RotInvStudy evaluator and published SOS experiment settings: D=10, NP=10, F=.7, CR=.3, budget=5000D. Source excludes F8/F10, so all 28 applicable functions receive 20 new independent Python runs. Published results have 30 runs. SOS source uses mutually distinct donors without excluding the target, toroidal repair after crossover and strict generational replacement. These details are reproduced only in the new control; they do not alter the frozen course algorithm. Retained upstream source commit: cf7c793dce5b5bd04a916797dc221ed4be7751ce. Source license is retained.

The same-algorithm control intentionally uses the paper's modified, non-rotated suite. It is separate from the required standard 30-function course experiment. It does not validate the numerical DE-VCR column.

Comparison: mean, population SD (same as SOS DataBox.computeSTD), all six course summary statistics with sample SD/variance retained separately. The descriptive mean band is max(1e-8, published SD), expanded by half the last published mean digit for tabulation rounding. Also retain the count without rounding correction. This is a scale-of-discrepancy summary, not a statistical equivalence test or a tuned optimization parameter. All 28 rows and outliers remain visible.

New optimization budget: 60,000,000 + 28,000,000 = 88,000,000 FEs. Post-run solution checks and benchmark probes are accounted separately.

Figures follow the supplied paper's serif manuscript, restrained blue/orange lines, full-width convergence matrices, black axes, white tables and fine horizontal rules. The course cover and member fields are preserved. New figures answer evaluator sensitivity and same-algorithm reproducibility; no synthetic optimization data are introduced.
