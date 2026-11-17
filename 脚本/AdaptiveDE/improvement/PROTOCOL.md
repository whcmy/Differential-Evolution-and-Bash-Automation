# DC-DE study algorithm revision

Author: 殷明骏

The original code, 20-run experiments and Automation application are frozen.
Revision sources and every new experiment live in this directory. No old
result is replaced and no result is discarded for being unfavorable.

## Evidence and proposed mechanisms

The existing TEAM_no_peg control improves four functions after the original
Holm correction and has a lower within-family mean rank (1.950 versus 2.533).
The escape and two-phase removals have no corrected per-function differences.
The deterministic shared potential guide therefore has weak transfer evidence;
the density escape module adds complexity without a detected benefit.

APE-DE replaces the common weighted guide with an independently sampled elite
member (top 11%). With probability 0.25(1-FEs/budget), an improving member from
the better half of the population provides the guide instead. Each draw remains
an actual individual; there is no population-wide shared centroid. The second
strategy group uses DLS-inspired early two-phase F control and success-history
F/CR adaptation, with a six-cell memory. Historical replaced parents form a
randomly bounded archive of 1.6NP. Out-of-bounds coordinates use parent-bound
midpoints. These supporting backbone choices are stated explicitly. No density
escape module, benchmark identity, known optimum or function-specific parameter
is used. This is an empirical common_benchmark revision, without a novelty claim.

## Development and validation separation

Development: all CEC2014 F01-F30, 10 dimensions, fixed NP=100, exactly 100000
objective evaluations including initialization, five seeds per function. Master
seed 20261109 matches the already observed development baselines. Three revision
variants are tested: APE, APE_no_potential and APE_no_control. Old comparison
records are development evidence, not a held-out confirmation sample.

The development comparison will determine whether the proposed full revision
merits confirmation. Any further source change must be recorded before fresh
confirmation. The selected source hash, settings, comparison methods, seeds
and statistical families will be frozen in a separate validation contract before
any validation result is opened. Confirmation uses master seed 20261117 and
20 independent runs per function, including fresh matched baseline runs. The
historical seeds and pilot runs do not increase this sample size.

## Analysis and reporting

Retain every function, including evaluator-sensitive functions. Report Best,
Mean, sample SD, sample variance and mean-based within-function rank; preserve
the required best-run objective/FEs curves. Show original PGE-DE explicitly as
the predecessor. Compare paired seeds using two-sided Wilcoxon signed-rank
tests with the original numerical tie convention, and Holm correction over
the declared comparison family. Mean ranks are descriptive, not by themselves
proof of statistical superiority. Report corrected wins, ties and losses and
paired effect sizes. Analyze F01-F16 separately as an evaluator-agreement
sensitivity subset; it does not replace the complete protocol benchmark.

The final report must distinguish development from confirmation, preserve the
native-paper reproduction and source ablation evidence, explain all algorithm
changes, and state both gains and remaining losses. No favorable conclusion
is guaranteed by this protocol. A revision is useful only if the experiments
support improved behavior relative to the predecessor and basic DE; any claim
of superiority to the strongest paper method needs its own evidence.
