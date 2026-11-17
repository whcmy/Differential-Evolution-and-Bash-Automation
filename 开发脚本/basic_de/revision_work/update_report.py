"""Integrate the validation evidence into the protocol report. Author: 殷明骏."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'build_report.py'
s=p.read_text()
s=s.replace("'A separate audit of 660 benchmark probes identifies evaluator differences on 13 functions and places the published DE-VCR comparison in its implementation context. '","'We added 600 matched-seed runs on the original CEC2014 evaluator and 560 runs of a published basic-DE protocol on its 28-function non-rotated study suite. '")
s=s.replace("'Saved solutions and independent summary recomputation connect the analysis to the retained experiments, establishing a baseline for subsequent strategy comparisons.'", "'The source-matched control places 27 of 28 mean errors within one published standard deviation plus tabulation rounding; F21 remains outside this descriptive band. The original opfunu implementation differs on 13 functions in 6,120 probes. All 1,160 added solutions pass independent reevaluation.'")
s=s.replace("'Figure 1 connects this design to the 600 saved records.'", "'Figure 1 connects this design to the 600 saved records. A second experiment isolates evaluator effects, and a third reproduces a published basic-DE control under its own benchmark and parameter settings [6,7]. These experiments distinguish algorithm reproduction from comparisons between improved and basic DE.'")
s=s.replace("    r.h('3 Results and analysis',newpage=True)","""    r.h('2.5 Validation experiments',2,toc=False)
    r.p('The DE-VCR study [3] supplies the basic DE equations and the visual reference for this report, but its Table 20 contains improved algorithms. Its DE-VCR column is therefore removed as the reproduction target. A published DE/rand/1/bin column from Caraffini and Neri [6,7] provides the same-algorithm control.')
    r.table(['Condition','protocol experiment','Evaluator replay','Literature control'],[
        ['Algorithm','Basic DE/rand/1/bin','Same frozen optimizer','Published basic DE/rand/1/bin'],
        ['Benchmark','Standard CEC2014','Standard CEC2014 C source','Non-rotated CEC2014RotInvStudy'],
        ['Functions and dimension','30; D = 10','30; D = 10','28; D = 10; source omits F8/F10'],
        ['Population; F; CR','100; 0.5; 0.9','100; 0.5; 0.9','10; 0.7; 0.3'],
        ['Budget including initialization','100,000 FEs','100,000 FEs','50,000 FEs'],
        ['Runs per function','20 original runs','20; same original seeds','20 new runs; published n = 30'],
        ['Repair and donors','Clipping; exclude target','Same as baseline experiment','Toroidal; donors may include target'],
        ['Purpose','Required protocol baseline','Isolate evaluator sensitivity','Compare the same published algorithm']
    ],[.25,.25,.25,.25],size=9,caption='Table 2. Three experiments with separate scientific roles.')
    r.p('The evaluator replay executes the unchanged Python optimizer on the retained original CEC2014 C source [5]. The Linux build removes an unused Windows header and corrects five input-scanning format specifiers; benchmark equations and data remain unchanged. Initialization, seeds, budgets and boundary repair match the baseline experiment. The 600 new runs consume 60 million FEs.')
    r.p('For the literature control, the authors’ SOS source [7] specifies NP = D, F = 0.7, CR = 0.3 and 5,000D evaluations. We implement the source’s strict generational DE update in Python and call its unchanged Java benchmark with rotation disabled. Three donors are mutually distinct but may include the target, and toroidal repair follows crossover. This source-specific control is separate from the baseline DE implementation. F8 and F10 return NaN in the study source and have no published result; all other 28 functions receive 20 runs, consuming 28 million FEs.')
    r.p('The published SOS table reports population SD, dividing by n. The comparison uses the same definition; the baseline table continues to report sample SD and variance. Mean discrepancies are summarized with a descriptive band of max(10⁻⁸, published SD), plus half a unit in the last printed mean digit. The rounding allowance matters when published means have only three significant figures. This band describes numerical proximity; it is not an equivalence test.')
    r.p('Validation uses 204 inputs per standard function: 200 seeded uniform points, the origin, both box corners and the known shift vector. All 1,160 added final solutions are independently reevaluated. Record checks verify unique run pairs, bounds, exact FE budgets and monotone histories. Source hashes confirm that the original 600 records and optimizer are unchanged. Probe and solution-check evaluations are recorded separately from optimization budgets.')

    r.h('3 Results and analysis',newpage=True)""")
# Renumber the original early tables before adding the new result sections.
s=s.replace("'Table 2 reports all six", "'Table 3 reports all six").replace("caption='Table 2.","caption='Table 3.").replace("caption='Table 3. Illustrative", "caption='Table 4. Illustrative")
s=s.replace('given in Table 2.', 'given in Table 3.')
start=s.index("    r.h('3.6 Benchmark and literature comparison'")
end=s.index("    r.h('4 Conclusions')",start)
new='''    r.h('3.6 Evaluator consistency and its effect on optimization',2,newpage=True)
    validation=json.loads((ROOT/'consistency/verification.json').read_text())
    def evidence(name):
        with (ROOT/'consistency'/name).open() as f:return list(csv.DictReader(f))
    ev=evidence('evaluator_summary.csv');comp=evidence('paper_comparison.csv');probes=evidence('pointwise_validation.csv')
    r.p('The expanded pointwise audit confirms the same 13 mismatched functions: F17–F27, F29 and F30. The remaining 17 functions agree at all 204 tested inputs within atol = 10⁻⁸ and rtol = 10⁻¹⁰. This is finite-input agreement, rather than a claim that the two implementations are globally identical. All 600 replay solutions reproduce their stored objective under the original CEC2014 evaluator.')
    r.fig('05_evaluator','Figure 9. Evaluator discrepancies propagate into optimization. a Each grey point is one of 600 paired runs with identical optimizer, seed and budget; blue marks show medians and IQRs. The ratio is log10[(official error + 10⁻⁸)/(opfunu error + 10⁻⁸)]; zero denotes equal final error. b Pointwise mismatch counts among 204 fixed inputs per function. Changed trajectories optimize different implemented objectives, so these ratios do not rank two algorithms.')
    r.p('F29 provides the clearest practical effect: mean error falls from 4.687 × 10⁶ with opfunu to 221.8 with the original evaluator. F30 changes from 4,471.8 to 464.9. Conversely, F23 changes from 237.4 to 329.5. The evaluator can therefore move the apparent outcome in either direction; a correction cannot be represented by a uniform adjustment to saved errors.')
    r.table(['Function','opfunu Mean','opfunu Std','Original Mean','Original Std'],
        [[f"F{int(x['function']):02d}"]+[scientific(x[k]) for k in ['opfunu_mean','opfunu_std','official_mean','official_std']] for x in ev],
        [.12,.22,.22,.22,.22],groups=[0 if i<3 else 1 if i<16 else 2 if i<22 else 3 for i in range(30)],size=9,
        caption='Table 5. Matched-seed evaluator replay on all 30 standard functions. Each column summarizes 20 runs; both SD columns use n − 1.')
    r.p('The replay completes a common-evaluator baseline for every standard function. The original opfunu baseline results remain in Table 3, while Table 5 and its saved solutions support comparisons requiring the original CEC2014 objective. The pointwise differences remain present in unmodified opfunu 1.0.4; no claim of evaluator equivalence is made for those 13 functions.')
    r.h('3.7 Reproduction of a published basic-DE control',2,newpage=True)
    r.p('The comparison now uses the DE/rand/1/bin column in extended Table 1 of Caraffini and Neri [6,7]. Algorithm, parameters, dimension, evaluation budget, repair rule and non-rotated study evaluator match the public experiment source. Published results summarize 30 runs and the new Python control summarizes 20. The modified study benchmark is identified explicitly; its non-rotated results are not pooled with standard CEC2014 results.')
    r.fig('06_matched_paper','Figure 10. Same-algorithm literature comparison on all 28 applicable functions. a Published and reproduced mean errors, with a display transform log10(mean error + 10⁻⁸). b Absolute mean discrepancy divided by max(10⁻⁸, published population SD) plus half the last published mean digit. The dashed line is the descriptive band boundary; orange identifies F21 outside it. F8 and F10 are absent in both source and published table.')
    r.table(['Function','Python Mean','Python SD(n)','Paper Mean','Paper SD(n)','Gap / band'],
        [[f"F{int(x['function']):02d}"]+[scientific(x[k]) for k in ['mean','population_std','paper_mean','paper_std']]+[f"{float(x['absolute_gap'])/float(x['descriptive_tolerance']):.3f}"] for x in comp],
        [.10,.19,.19,.19,.19,.14],size=9,
        caption='Table 6. Complete same-algorithm comparison. SD(n) uses denominator n; paper means and SDs are the published values, not generated observations.')
    r.p('The reproduced and published means are close at the scale of the reported run variability on 25 of 28 functions without rounding allowance. Accounting for three-significant-figure publication rounding gives 27 of 28. F23 converges to 315.5008, which rounds to the published 3.16 × 10²; F26 has mean 100.1963, which rounds to 1.00 × 10². Treating these printed means as exact real numbers would create artificial discrepancies relative to their small SDs.')
    r.p('Representative means are 0.02350 versus 0.02120 on F4, 13.498 versus 14.600 on F5, 0.4129 versus 0.4150 on F20, and 390.39 versus 407.00 on F30. These comparisons support numerical proximity of the source-matched basic-DE means across most of the study suite. They do not show that basic DE reproduces DE-VCR.')
    r.p('F21 remains discrepant: the local mean is 6.169 versus 0.775 in the paper. One local run ends at 118.448, while the local median is 0.2682; the sample SD is 26.429. F11 also has a population SD of 4.425 versus the published 23.10 despite a nearby mean. Independent random streams and 20 versus 30 runs can reveal different rare outcomes. Thus matching most means does not establish equality of the full outcome distributions.')
    for block,scope in [(1,'F1–F16, excluding F8 and F10'),(2,'F17–F30')]:
        r.h('3.7.'+str(block)+' Convergence of the literature control',2,newpage=True,toc=False)
        r.fig('paper_curves_'+str(block),'Figure '+str(10+block)+'. Convergence of the Python literature control on '+scope+'. Blue curves and bands show median absolute error and IQR over 20 runs; orange dashed curves show the run with the lowest final error. All 50,000 FEs contribute to optimization, and every logged checkpoint is drawn. Values below 10⁻⁸ share a display floor; numerical tables retain exact errors.')
        r.p('The small population and lower crossover rate permit accurate non-rotated coordinate search on the first functions, while hybrid and composition functions retain seed-dependent outcomes. These trajectories document the matched literature protocol; comparison with the baseline curves also changes the benchmark, parameters and budget, so it is not an isolated test of any one strategy.' if block==1 else 'F21 and F22 show how a favorable best run can coexist with a large mean caused by rare poor runs. The F23 and F26 plateaus are stable and nonzero. Retaining all 20 histories makes these differences visible alongside the published mean and spread.')
'''
s=s[:start]+new+s[end:]
start=s.index("    r.h('4 Conclusions')")
end=s.index("    r.h('References')",start)
s=s[:start]+'''    r.h('4 Conclusions')
    r.p('The 600-run baseline experiment establishes a reproducible Python DE/rand/1/bin baseline on all 30 CEC2014 10D functions, with complete final-error statistics and convergence histories. Added matched-seed runs show that opfunu objective differences materially affect several outcomes, particularly F29 and F30. The original-source replay provides a separately validated common-evaluator baseline for all 30 functions.')
    r.p('The literature comparison now targets published basic DE under its actual source settings. Across all 28 applicable non-rotated study functions, 27 reproduced means lie within one published SD plus tabulation rounding; 25 satisfy the unexpanded band. F21 and differences in rare-run variability bound this result. The evidence supports broad numerical proximity for the matched basic-DE control, while the improved DE-VCR results serve only as background. All original records are preserved and all 1,160 added solutions pass independent reevaluation.')
''' +s[end:]
s=s.replace("'[5] Liang JJ", "'[5] Liang JJ")
s=s.replace("Independent pointwise comparison retained with the study.'", "Independent pointwise comparison retained with the study.',\n        '[6] Caraffini F, Neri F. A study on rotation invariance in differential evolution. Swarm and Evolutionary Computation 50 (2019), 100436. doi:10.1016/j.swevo.2018.08.013. Extended results, Table 1.',\n        '[7] Caraffini F, Neri F. Raw data and extended results for: a study on rotation invariance in differential evolution. Mendeley Data, version 1 (2019). doi:10.17632/psp65d2nbc.1. Public SOS experiment and benchmark source: github.com/facaraff/SOS; retained commit cf7c793dce5b5bd04a916797dc221ed4be7751ce.'")
s=s.replace('Table 2.', 'Table 2.')
p.write_text(s)
# Let the finishing routine handle the actual figure count.
f=p.parent/'finish_report.py';q=f.read_text().replace('len(replaced)==len(figures)==8','len(replaced)==len(figures)')
f.write_text(q)
