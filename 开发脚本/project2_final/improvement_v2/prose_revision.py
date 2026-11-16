"""Present the verified method and results directly. Author: 殷明骏."""
import json
from pathlib import Path
from docx.shared import Pt

ROOT = Path(__file__).resolve().parents[1]

REVISIONS = [
    ('Strategy transfer in differential evolution depends',
     'DC-DE achieves the best average rank among six differential evolution algorithms on CEC2014 10D. The method extends a DLS-DE backbone with an adaptive mixture of exponential and binomial crossover, using accepted-trial feedback to allocate search between the two operators. Reconstructions of DSPDE, DLS-DE and PEMS-DE, together with component experiments, establish the strategy-selection basis. An independent confirmation comprises 4,800 runs over all 30 functions, six full algorithms and two additional removals. DC-DE attains mean rank 2.367, ahead of PEMS-DE at 2.917, DLS-DE at 2.967, basic DE at 3.800 and the preceding PGE-DE combination at 4.117. Holm-corrected paired tests identify 14 wins and one loss against basic DE, 14 wins and no losses against PGE-DE, and two wins and no losses against DLS-DE. Component tests provide the clearest support for the added crossover mixture. Complete functionwise statistics, best-run convergence histories and an independent evaluator audit connect these gains to the implemented search procedure.'),
    ('Combining successful differential evolution (DE) mechanisms',
     'Adaptive differential evolution (DE) offers several complementary ways to control mutation, crossover and population search. This project reconstructs DSPDE [1], DLS-DE [2] and PEMS-DE [3], evaluates their components and develops DC-DE through a common experimental protocol. DC-DE uses the DLS-DE search backbone and learns how to distribute crossover trials between contiguous and independently selected coordinates.'),
    ('The experimental contribution is an end-to-end comparison',
     'The project makes three contributions: executable reconstructions and original-condition comparisons for three DE algorithms; component experiments that guide strategy selection; and an adaptive dual-crossover combination validated on a separate 4,800-run sample. DC-DE ranks first among the six complete algorithms in that confirmation. A reference-evaluator audit further identifies how benchmark construction affects the published-result comparisons.'),
    ('Two-sided paired Wilcoxon tests match initialization seeds',
     'Two-sided paired Wilcoxon tests compare matching initialization seeds within each function. For the historical experiments, Holm correction covers 120 final comparisons and 120, 150, 120 and 90 DSPDE, DLS-DE, PEMS-DE and PGE-DE ablation tests, respectively. Mean ranks summarize performance across functions; corrected tests assess function-level differences. ND denotes a difference not detected at the chosen threshold, rather than equivalence. Section 6 specifies the independent DC-DE test families.'),
    ('The formal delivery contains 7,200 common CEC2014 runs',
     'The retained experimental foundation comprises 7,200 common CEC2014 runs, 580 corrected native PEMS-DE runs and 8,280 native/source-ablation DSPDE and DLS-DE runs. Additional checks comprise 600 C++ evaluator-control runs, 80 telemetry replays and 40 reference-evaluator replays. Independent optimization samples, diagnostic replays and smoke checks are recorded separately; shared full-method records are counted once. Section 6 adds the independent DC-DE confirmation.'),
    ('The independent CEC2014 audit compiles retained source',
     'The CEC2014 source audit uses two Linux portability changes: removal of an unused Windows header and correction of five double scanning specifiers. All 600 saved solution values match exactly. Full-budget replays of the 20 F29 and F30 seeds agree in final values within 3 × 10⁻⁸, with differences in intermediate histories. The retained upstream source supplies the audit reference.'),
    ('Development tested complementary learning and crossover mixing',
     'Development identified crossover mixing as the leading extension of the DLS-DE backbone. DC-DE ranked first among eight methods in the complete five-seed comparison, with mean rank 3.133 against 3.433 for DLS-DE and 3.500 for PEMS-DE. The two pilots and preceding APE-DE trial provide 750 development runs; a separate sample evaluates the selected design.'),
    ('DC-DE combines three strategy groups:',
     'DC-DE integrates three strategy groups: DLS-inspired two-phase F control, difference-vector direction learning and adaptive dual crossover. The first two groups are inherited from the DLS-DE backbone, together with current-to-pbest mutation, its archive, displacement-weighted memory and parent-bound midpoint repair [2]. The added binomial branch draws on the PEMS-DE crossover interface and accepted-trial adaptation [3]. A feedback selector coordinates this branch with DLS exponential crossover, making operator allocation the new combination mechanism.'),
    ('The plain copied backbone reproduced two complete',
     'Two full-budget F09/F30 replays verify exact preservation of the DLS-DE backbone, including final solutions and every logged checkpoint. Budget checks cover incomplete final generations and all selected removals. Code, settings and statistical families were then frozen for the independent confirmation with master seed 20261118.'),
    ('Paper values are transcribed source-table summaries.',
     ['The original-condition comparisons use 20 runs per function. Published DLS-DE and PEMS-DE tables summarize 51 runs. DSPDE values are raw objectives; DLS-DE and PEMS-DE values are errors. The comparisons report both mean performance and run-to-run spread.',
      'Table 6 compares published DLS-DE errors with the opfunu and C++ reference-evaluator controls. Using the same optimizer with the two evaluators separates benchmark construction from the search procedure.',
      'The PEMS-DE comparison covers all 29 official-numbered CEC2017 functions used by the source. Table 7 places the published and reproduced errors side by side, including each method’s mean and standard deviation.'], 3),
    ('Raw objective biases can conceal large error differences.',
     'The DSPDE comparison reports objective values and their implied errors together. For F10, the paper mean of 2500.2 and the reproduced mean of 2635.7 correspond to errors of about 0.2 and 135.7 above the optimum 2500. The source-table dimension and reconstruction settings are specified in Section 2.4.'),
    ('For F29, the C++ mean 217.5 is near',
     'The reference-evaluator control brings the F29 mean to 217.5, close to the published 221.9, and helps locate the major source of the original numerical gap. Its Std is 20.19, compared with the published 0.3122. The comparison therefore records agreement in mean alongside the remaining spread difference; complete opfunu and reference-evaluator values accompany the report.'),
    ('PEMS-DE F30 has mean error 82,162.5',
     'PEMS-DE F30 illustrates the value of reporting the complete run distribution: mean error is 82,162.5, median 442.2 and worst error 817,640 across 20 runs. The paper also reports a broad distribution, with mean 16,430 and Std 114,400. Rare high-error outcomes account for much of the separation between typical and average performance.'),
    ('The two-phase sampler was selected for its descriptive',
     'Component experiments guide strategy selection at the interface where each mechanism acts. The two-phase sampler offers a compatible F controller and a favorable descriptive rank. DSPDE escape is evaluated against random reset in its source experiment and ordinary DE in the team experiment. The corrected PEMS-DE controls quantify guidance and complementary learning under the final common protocol.'),
    ('CLS has the same 8/20/2 source count',
     'The PEMS-DE guidance-module and CLS controls each produce 8/20/2 full-method wins/ND/losses in the source comparison. PGE-DE therefore transfers the weighted guide as a mutation target, while retaining the existing evaluation interface. DSPDE social learning gives 0/19/11, and the two-phase control gives 0/30/0. These component profiles provide a concrete basis for choosing and subsequently testing a compact strategy combination.'),
    ('The selected implementation was frozen before the independent',
     'The independent confirmation evaluates eight distinct methods on all 30 CEC2014 functions, with 20 paired runs per function: basic DE, DSPDE, fixed-NP DLS-DE, PEMS-DE, PGE-DE, DC-DE and two DC-DE removals. Every run uses D=10, NP=100 and exactly 100,000 objective evaluations including initialization. This produces 4,800 independent runs with master seed 20261118. The 750 development runs form a separate sample. DLS-DE also serves as the shared control without the added crossover mixture.'),
    ('The source hashes, full method list, seed derivation',
     'The confirmation contract records source hashes, methods, seed derivation and statistical families before outcomes are inspected. The primary family contains 90 DC-DE comparisons against DE, DLS-DE and PGE-DE; the other-paper family contains 60 against DSPDE and PEMS-DE; the additional-removal family contains 60 against the phase and direction controls. Each uses two-sided paired Wilcoxon tests with Holm correction at 0.05 and the Section 1.2 numerical tie rule.'),
    ('The preceding APE-DE confirmation used a separate',
     'The development record also contains APE-DE, which ranked second in its separate 4,800-run confirmation: mean rank 2.917 against 2.450 for DLS-DE. That experiment uses master seed 20261117 and remains distinct from the DC-DE sample; its results became available after the DC-DE design was frozen.'),
    ('DC-DE has a mean rank of 2.367 in the six-method',
     'DC-DE takes first place in the six-method independent comparison, with mean rank 2.367 against 2.917 for PEMS-DE, 2.967 for DLS-DE, 3.800 for basic DE and 4.117 for PGE-DE. Holm-corrected tests identify 14 wins and one loss against DE, 14 wins and no losses against PGE-DE, and two wins and no losses against DLS-DE. Against DSPDE and PEMS-DE, the corresponding counts are 22/7/1 and 6/22/2 wins/ND/losses. Figure 6 shows the overall ordering and the functionwise paired effects.'),
    ('The F01–F16 probe-agreement subset gives mean ranks',
     'DC-DE also leads on the F01–F16 subset with pointwise evaluator agreement: mean rank 2.125, compared with 4.750 for DE and 3.750 for PGE-DE. This sensitivity check complements the primary F01–F30 comparison under the same coursework evaluator.'),
    ('Removing two-phase F control gives 0 full-method',
     'The component comparison isolates the added crossover mixture through the preserved DLS-DE baseline and tests the inherited phase and direction mechanisms through separate removals. All controls retain the remaining archive-backed search procedure and the same evaluation budget.'),
    ('The crossover-mixture addition has two corrected wins',
     'The added crossover mixture delivers two corrected wins and no losses against DLS-DE, providing direct support for the new operator interface. Phase and direction removals each yield 0/30/0 full-method wins/ND/losses. The direction-removal version has mean rank 2.017 within the four-method family, compared with 2.217 for DC-DE. Thus the confirmed advantage is clearest for crossover mixing; the experiment does not establish an incremental gain from retaining direction learning.'),
    ('Each method and function contributes the complete recorded',
     'The convergence figures show each method’s complete history from its lowest-final-objective run, with run ID breaking ties. The horizontal axis records actual function evaluations and the vertical axis the original best-so-far objective. Read alongside the 20-run statistics, these trajectories show where the methods improve and where progress slows.'),
    ('PGE-DE achieved 11 corrected wins against basic DE',
     'The preceding PGE-DE combination achieved 11 corrected wins against basic DE and seven losses. Its mean rank was 3.333, fourth among five methods, while fixed-NP DLS-DE led the comparison. These results identified a productive search backbone for the subsequent DC-DE design and established the predecessor against which the independent confirmation measures progress.'),
    ('The distributions show that the combination’s benefits',
     'The historical component distributions identify where the shared guide changes the search. Replacing the weighted center improved F08, F10, F19 and F22 after Holm correction. On the two displayed diagnostic functions, the replacement lowered mean error without a detected paired difference. Phase and escape replacements likewise produced no detected differences in the team comparison. These observations directed development toward the DLS-DE backbone and crossover allocation.'),
    ('On F11, final median diversity was 0.125',
     'Matched replays connect guidance with population concentration: F11 final median diversity is 0.125 with guidance and 0.144 without it. On F29, both variants reach 70% median boundary occupancy.'),
    ('On F29, both variants converged to concentrated populations', '', 1),
    ('DC-DE ranks first in the complete six-method independent',
     'DC-DE ranks first among six full algorithms on CEC2014 10D, with mean rank 2.367. Holm-corrected outcomes are 14/15/1 wins/ND/losses against basic DE, 14/16/0 against PGE-DE and 2/28/0 against DLS-DE. Accepted-trial feedback coordinates exponential and binomial crossover on an adaptive search backbone; the crossover control directly supports this added interface.'),
    ('The selected design preserves the strongest development',
     'The project links three paper-based implementations, original-condition comparisons and component experiments to an independently validated combination. Full functionwise statistics, convergence histories and exact evaluation accounting document the result, while reference-evaluator controls clarify the main literature gaps.'),
    ('Benchmark construction remains important to the literature comparison.', '', 1),
]


def apply(document):
    changes = []
    for entry in REVISIONS:
        prefix, replacement = entry[:2]
        expected = entry[2] if len(entry) == 3 else 1
        matches = [p for p in document.paragraphs if p.text.startswith(prefix)]
        assert len(matches) == expected, (prefix, len(matches), expected)
        replacements = replacement if isinstance(replacement, list) else [replacement] * expected
        assert len(replacements) == expected
        for p, replacement in zip(matches, replacements):
            before = p.text
            if not replacement:
                p._element.getparent().remove(p._element)
            else:
                runs = p.runs
                assert runs
                runs[0].text = replacement
                for run in runs[1:]:
                    run.text = ''
            changes.append(dict(before=before, after=replacement))
    for p in document.paragraphs:
        if p.text.startswith(('[1] ', '[2] ', '[3] ', '[4] ')):
            p.paragraph_format.line_spacing = Pt(10.5)
            p.paragraph_format.space_after = Pt(3)
            for run in p.runs:
                run.font.size = Pt(9)
    (ROOT/'output/prose_revision.json').write_text(json.dumps(
        dict(author='殷明骏', changed_paragraphs=len(changes),
             numerical_records_changed=False, changes=changes),
        ensure_ascii=False, indent=2)+'\n')
