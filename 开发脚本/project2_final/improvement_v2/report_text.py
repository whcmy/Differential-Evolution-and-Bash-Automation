"""Evidence-bound method and outcome prose. Author: 殷明骏."""


def method(j):
    j.h('2.5 Dual crossover with operator feedback',2)
    j.p('Development tested complementary learning and crossover mixing on the DLS-DE backbone. DC-DE ranked first among eight methods on the complete five-seed comparison (mean rank 3.133), ahead of DLS-DE (3.433) and PEMS-DE (3.500). The complementary-learning candidate was not selected. The two pilots and earlier APE-DE trial supply 750 retained development runs, separate from confirmation.')
    j.p('DC-DE combines three strategy groups: DLS-inspired two-phase F control, difference-vector direction learning, and adaptive dual crossover. It preserves the fixed-NP DLS current-to-pbest backbone, archive, displacement-weighted parameter memory and parent-bound midpoint repair [2]. The second crossover branch uses a PEMS-inspired binomial interface and adaptation from accepted trials [3]; its operator selector is an explicit combination design.')
    j.figure('revision_mechanism','Figure 0. The dual crossover interface. (a) Exponential crossover inherits a contiguous circular block of mutant coordinates, with CR determined by the DLS dimension-probability memory. (b) Binomial crossover selects coordinates independently and forces one mutant-derived coordinate. The shown masks are explanatory examples, not measured trial masks. Ordinary accepted-trial rates update the branch mixture; direction-learning override trials are excluded from that credit.')
    j.section(2)
    j.p('Both branches use the same current-to-pbest mutation and archive. Differential donors exclude the target and each other. The best 11% of the current population supplies a randomly sampled p-best vector; z is drawn from the population/archive union.')
    j.equation('vᵢ = xᵢ + Fᵢ(gᵢ − xᵢ + xᵣ₁ − zᵣ₂)                    (4)')
    j.section(2)
    j.p('The binomial branch is selected independently for each target with probability π, initially 0.5. Its CR is sampled from a normal distribution with scale 0.1 and clipped to [0,1], with a mean initialized to 0.5. Strict improvements in ordinary binomial trials update that mean toward the fitness-gain-weighted realized fraction of mutant-derived coordinates. The exponential branch retains the source dimension-based CR rule.')
    j.p('For each branch, its smoothed acceptance rate is (accepted ordinary trials + 1)/(eligible ordinary trials + 2) within that generation. The binomial and exponential rates enter the probability update below. Direction-learning overrides belong to neither crossover credit set. The next binomial probability uses')
    j.equation('π′ = clip[0.9π + 0.1 s_b/(s_b + s_e), 0.1, 0.9]           (5)')
    j.section(2)
    j.p('The retained DLS controller uses its success-rate/sine F rule in the first 30% of the budget and positive Cauchy sampling thereafter. Displacement-weighted memory adapts F and the sampling width; accepted displacements also update the dimension-probability memory. Direction-learning eligibility and its shared-generation gate follow the source convention in Section 2.1.')
    j.new_table('Table 4. DC-DE settings frozen before independent confirmation.',
                ['Setting','Value'],[
                    ['Population and budget','NP 100; 100,000 FEs including initialization'],
                    ['Backbone','Fixed-NP DLS current-to-pbest; p 0.11; archive ratio 1.6'],
                    ['Parameter control','H 6; first-phase fraction 0.3; adaptive Cauchy width'],
                    ['Direction learning','Source convention: ST 30; shared gate rand > 0.3'],
                    ['Initial binomial CR mean','0.5; normal sampling scale 0.1; clipping to [0,1]'],
                    ['CR mean update','0.9 old mean + 0.1 gain-weighted realized crossover fraction'],
                    ['Branch probability','Initial 0.5; smoothed acceptance feedback; bounds [0.1,0.9]'],
                    ['Override credit','Direction-learning trials excluded from branch-selector training'],
                    ['Boundary / selection','Parent-bound midpoint; ties accepted as in DLS-DE'],
                    ['No-added-strategy control','The preserved fixed-NP DLS-DE implementation']])
    j.section(2)
    j.p('The plain copied backbone reproduced two complete F09/F30 control runs exactly, including solutions and every recorded checkpoint. Budget tests include incomplete final generations and cover all selected removals. The implementation and full test families were frozen before the independent sample using master seed 20261118 began.')


def abstract(summary,ranks,counts):
    de,old,dls=counts['DE'],counts['TEAM'],counts['DLSDE']
    return (f'Strategy transfer in differential evolution depends on the compatibility of the selected operators. '
            f'We reconstruct DSPDE, DLS-DE and PEMS-DE, retain their component controls and examine the original PGE-DE combination. '
            f'Development comparisons motivate DC-DE, which combines DLS parameter control and direction learning with an adaptive exponential/binomial crossover mixture. '
            f'The frozen design is evaluated in 4,800 independent CEC2014 runs covering six full methods and two additional removals. '
            f'Across all 30 ten-dimensional functions, DC-DE has the lowest mean rank, {ranks["DUAL"]:.3f}, compared with {ranks["DLSDE"]:.3f} for DLS-DE, {ranks["DE"]:.3f} for DE and {ranks["TEAM"]:.3f} for the predecessor. '
            f'Corrected paired tests identify {de["wins"]} wins and {de["losses"]} losses against DE, {old["wins"]} wins and {old["losses"]} losses against PGE-DE, and {dls["wins"]} wins and {dls["losses"]} losses against DLS-DE. '
            f'A separate evaluator audit identifies discrepancies on 13 functions relative to the reference implementation.')


def conclusions(j,summary,ranks,counts):
    de,old,dls=counts['DE'],counts['TEAM'],counts['DLSDE']
    j.p(f'DC-DE ranks first in the complete six-method independent comparison, with mean rank {ranks["DUAL"]:.3f}. The corrected function-level outcomes are {de["wins"]}/{de["not_detected"]}/{de["losses"]} wins/undetected differences/losses against DE, {old["wins"]}/{old["not_detected"]}/{old["losses"]} against PGE-DE and {dls["wins"]}/{dls["not_detected"]}/{dls["losses"]} against DLS-DE. These results describe the fixed CEC2014 10D protocol; the per-function tests determine the scope of statistically supported advantages.')
    j.p('The selected design preserves the strongest development backbone and adapts the allocation between two crossover interfaces. The no-added-strategy DLS-DE control and the phase/direction-learning removals separate the contributions of the three strategy groups. The unsuccessful complementary-learning trial and earlier APE-DE revision remain part of the design record.')
    j.p('Benchmark construction remains important to the literature comparison. The original records and independent experiments retain the unchanged coursework evaluator, while the separate source audit identifies discrepancies on 13 functions. Saved solutions, exact evaluation budgets, source hashes and complete best-run histories connect the reported results to the preserved experiments.')
