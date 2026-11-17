# Experimental protocol and benchmark configuration

This note records the settings used by the retained optimization experiments. The reports provide the corresponding results, evaluator comparisons and statistical tests.

## Baseline validation

The Python DE/rand/1/bin baseline evaluates all 30 CEC2014 functions in ten dimensions. Each function has 20 independent runs with population size 100, F = 0.5, CR = 0.9, bounds [-100, 100] and a budget of 100,000 objective evaluations including initialization. Initialization is uniform, boundary repair clips coordinates, replacement requires strict improvement, and donors come from the preceding generation. The 600 baseline runs retain final solutions and convergence histories.

The evaluator replay uses the original CEC2014 C evaluator under matched seeds and optimizer settings. A separate literature control follows the published non-rotated basic-DE protocol on its 28 applicable functions. These comparisons retain their distinct benchmark definitions and budgets.

## Adaptive differential evolution

DSPDE, DLS-DE and PEMS-DE reconstructions retain their recorded original-condition experiments. The common comparison uses CEC2014 10D, population size 100, 100,000 objective evaluations and 20 independent runs per function and method.

The independent DC-DE confirmation comprises six full algorithms and two removal configurations across 30 functions, with 20 runs per condition: 4,800 runs in total. The master seed is 20261118. DC-DE combines the DLS-DE search backbone with accepted-trial feedback for allocating exponential and binomial crossover. Rank comparisons are descriptive; paired Wilcoxon tests use Holm correction within the stated comparison families at 0.05.

## Automated optimization experiments

Three recorded cron executions sweep population sizes 50, 100 and 150 over all 30 CEC2014 functions in ten dimensions. Each function uses 100,000 objective evaluations. The master seeds are 2026111601, 2026111602 and 2026111603, producing 270 saved solutions and nine suite scores.

A suite score is the arithmetic mean of absolute fitness errors across the 30 functions. Batch validation checks function coverage, seeds, budgets, monotone histories, saved solutions, exact score tokens and extracted summaries. The source snapshot map links the renamed code to the archived execution hashes. Historical timestamps and numerical records retain their recorded values; workspace paths in the published presentation use normalized labels.
