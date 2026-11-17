# DC-DE experiments and report revision

Author and last editor: 殷明骏.

DC-DE combines the preserved fixed-population DLS-DE backbone with an adaptive
exponential/binomial crossover mixture. The internal runner name is `DUAL`.
`DLC` is the unselected complementary-learning development candidate.
The original common-protocol solvers in `../code/` remain unchanged.

`confirmation_contract.json` fixes all 30 CEC2014 10D functions, NP 100,
100,000 actual function evaluations including initialization, 20 paired runs,
eight distinct methods and master seed 20261118. It records optimizer and
benchmark hashes. DLS-DE is also the shared no-added-crossover control.
The 90/60/60 test families were frozen before confirmation began.

The five-seed development comparison uses 300 new records and retained controls.
DC-DE ranks first among eight development methods (3.133); the independent
result is recorded only after the complete 4,800-run matrix is verified.
Earlier APE-DE work and its separate 4,800-run confirmation remain in
`../improvement/`; they are not pooled with this sample.

Run from this directory using the study numerical environment. A new output
directory and a recorded fresh seed are required for a new experiment. Resume
is allowed only with identical source hashes and configuration.

```bash
../.venv/bin/python run_confirmation.py --algorithms DE DSPDE DLSDE PEMSDE TEAM DUAL DUAL_no_phase DUAL_no_learning --runs 20 --seed 20261118 --workers 24 --output results/confirmation --resume
../.venv/bin/python ../improvement/verify_records.py results/confirmation --expected 4800
../.venv/bin/python analyze_confirmation.py
```

The report and figures use `build_report.py`, `report_text.py` and
`plot_confirmation.py`. Only a complete, verified confirmation with strictly
lowest six-method mean rank can enter the final report. `finish_report.py`
renders Word and restores vector figures at identical bounds. The exact protocol
cover is preserved. `audit_final_report.py` independently checks raw statistics,
all 1,110 printed statistical records, selected histories, cover, metadata and page bounds.
`audit_figures.py` checks the 16 embedded vector sheets. Visual inspection and
current-file hash checks precede final packaging.

The body is single column after rendered comparison. Figure colours/markers and
thin black ruled tables follow the supplied local papers. No numerical records
or frozen algorithm settings are modified by layout work.
