# First-rank confirmation plan

Author: 殷明骏

This plan was written before candidate selection. The executed
confirmation_contract.json subsequently froze DC-DE and its settings before
the first independent result. STATUS.md records execution progress.

The target is first descriptive mean rank in the complete CEC2014 F01-F30
comparison, 10 dimensions, fixed NP 100 and exactly 100000 objective evaluations,
20 independent paired seeds per function. The main table contains the selected
candidate, basic DE, DSPDE, DLS-DE, PEMS-DE and the original PGE-DE. Native-source
reproductions remain separate from fixed-NP controls. No function or unfavorable
run is excluded, no baseline is weakened and the numerical tie rule is unchanged.

Fresh master seed: 20261118, provided that it is unused at contract creation.
The selected candidate additionally receives no-phase and no-direction-learning
controls. The existing DLS-DE baseline is also the exact no-added-strategy
control for either candidate; this identity is checked against the plain copied
backbone. Its records are shared between comparison tables, never counted as
additional independent observations. This gives 8 distinct methods and 4800
records in total.

Tests: two-sided paired Wilcoxon signed-rank tests, the retained numerical tie
convention and Holm correction at alpha .05. Primary family: selected candidate
versus DE, DLS-DE and original PGE-DE over 30 functions (90 tests). Other paper
controls: versus DSPDE and PEMS-DE (60 tests). Additional removals: versus
no-phase and no-direction-learning (60 tests). The full-versus-no-added-strategy
contrast is the canonical primary DLS-DE comparison and is reused by attribution,
not tested again under a more permissive family.

Report all 30 function statistics, Best/Mean/sample SD/sample Variance/Rank,
all-run distributions and every required best-run objective/FEs curve. First
mean rank is a descriptive benchmark result; statistically supported superiority
is claimed only for detected contrasts. The final report distinguishes earlier
design/development experiments from the last untouched confirmation sample.
