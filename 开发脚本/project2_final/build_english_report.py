"""Verified English report, retaining bilingual personal names only."""
import csv
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'output'
LABEL = {'DE': 'DE', 'DSPDE': 'DSPDE', 'DLSDE': 'DLS-DE (fixed NP)', 'PEMSDE': 'PEMS-DE', 'TEAM': 'PGE-DE'}


def read_csv(name):
    with (OUT/name).open(encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def main():
    summary = json.loads((OUT/'analysis_summary.json').read_text())
    assert summary['new_formal_runs'] == 7780
    assert len(list((OUT/'curves').glob('F??.pdf'))) == 30
    for name in ['coursework_validation.json', 'pems_native_validation.json', 'selected_replay.json']:
        assert json.loads((OUT/name).read_text())['passed'], name
    identity = json.loads((ROOT/'protocol/report_identity.json').read_text())
    lines = ['# NUIST Experiment Report', '',
             'Course name: '+identity['course_english'],
             'Experiment name: Project 2 Differential Evolution',
             'Date: '+datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d'),
             f"Tutor: {identity['tutor_chinese']} / {identity['tutor_english']}",
             'College: '+identity['college_english'],
             'Class: '+identity['class_english'], '']
    lines += [f"Name: {m['chinese']} / {m['english']}    Student ID: {m['student_id']}" for m in identity['members']]
    lines.append('')
    def head(s):
        lines.extend(['## '+s, ''])
    def p(s):
        lines.extend([s, ''])
    def table(rows, columns, numeric=()):
        lines.extend(['| '+' | '.join(label for key, label in columns)+' |', '| '+' | '.join(['---']*len(columns))+' |'])
        for row in rows:
            values = []
            for key, _ in columns:
                v = row[key]
                if key in numeric:
                    v = f'{float(v):.4e}'
                elif key in ('rank', 'mean_rank'):
                    v = f'{float(v):.3f}'
                values.append(str(v))
            lines.append('| '+' | '.join(values)+' |')
        lines.append('')

    head('1. Experimental objectives and protocol')
    p('This project reproduces DSPDE, DLS-DE and PEMS-DE, evaluates their component strategies, and combines three selected strategies into PGE-DE. The final controlled experiment compares basic DE, the three paper algorithms and PGE-DE on CEC2014. The study evaluates the combination without assuming that combining individually useful strategies must improve performance.')
    p(f"The delivery contains {summary['new_formal_runs']:,} new formal runs: 7,200 CEC2014 coursework runs and 580 corrected PEMS-DE reproduction runs on the official-numbered CEC2017 reference suite. It also retains {summary['legacy_runs']:,} historical single-paper runs. The same full-algorithm records are reused across final-comparison and ablation tables only when their configurations are identical; they are not counted twice. The 360 small-budget interface runs are excluded from formal statistics.")
    p('Two experimental tracks are reported separately. The original-condition track retains native population mechanisms and paper-specific budgets. The coursework track uses unmodified opfunu 1.0.4 CEC2014, functions F1-F30, D=10, bounds [-100,100], fixed NP=100, exactly 100,000 function evaluations (FEs), and 20 independent runs per function. Initialization and every additional search evaluation count toward the budget.')
    table([
        dict(algorithm='DE', native_np='100', native_fes='100000', controlled_np='100 fixed'),
        dict(algorithm='DSPDE', native_np='50', native_fes='75000', controlled_np='100 fixed'),
        dict(algorithm='DLS-DE', native_np='182 to 4', native_fes='100000', controlled_np='100 fixed'),
        dict(algorithm='PEMS-DE', native_np='60', native_fes='100000', controlled_np='100 fixed'),
        dict(algorithm='PGE-DE', native_np='Not applicable', native_fes='Not applicable', controlled_np='100 fixed')
    ], [('algorithm','Algorithm'),('native_np','Native NP'),('native_fes','Native FEs'),('controlled_np','Controlled NP')])
    p('For the common population-size requirement, DLS-DE is explicitly evaluated as a fixed-NP control: its linear population reduction is disabled in the final comparison, while its other mechanisms are retained. Its native 182-to-4 reproduction and ablations remain separate. The fixed-NP control is not described as the paper-default algorithm. Across algorithms, their own crossover, acceptance and boundary rules are retained: DLS-DE uses parent-bound midpoint repair and accepts ties; DE, DSPDE and PGE-DE use clipping and strict improvement; PEMS-DE uses clipping and accepts ties.')
    p('Each algorithm receives the same initialization seed for a given function and run index. Subsequent random-number consumption can differ. Independent runs, rather than generations or saved checkpoints, define n=20. Basic DE is generational DE/rand/1/bin with F=0.5 and CR=0.9. A final partial generation evaluates only the remaining targets.')
    p('Error is max(0, best objective minus the declared optimum). Best, Mean, sample Std, sample Variance and Rank are reported for every formal function/algorithm group; complete CSV files additionally retain Median and Worst. Std and Variance use denominator n-1. Mean-error ties use absolute tolerance 1e-8 and relative tolerance 1e-10 and receive average ranks. Final five-algorithm ranks are computed separately from ablation ranks.')
    p('Additional comparisons use two-sided paired Wilcoxon signed-rank tests within each function, matching the same initialization seeds. Differences within the numerical tie tolerance are set to zero; an all-zero comparison has P=1. Holm correction is applied separately to the final-comparison family of 120 tests, DSPDE ablations (120), DLS-DE ablations (150), PEMS-DE ablations (120), and team ablations (90). Raw and adjusted P values, test statistics, nonzero pair counts, mean/median differences and rank-biserial effects are retained. Failure to detect a difference does not establish equivalence.')

    head('2. Algorithms and strategy combination')
    p('2.1 DSPDE. DSPDE dynamically reassigns elite, ordinary and inferior roles according to current fitness. Elite candidates use Linnik perturbations; ordinary candidates use social learning. Inferior candidates use a mixture of elite and global Gaussian population models to detect low-density regions and apply an anti-density-gradient step with noise or mirror resampling [1].')
    p('The reconstruction uses Ng=max(6, round(0.618*NP/3)), elite mixture weight 0.7, covariance regularization 1e-6, gradient-branch probability 0.7, density threshold 0.2*(1-0.9q), and step size 0.1*(1-0.9q). Linnik alpha=1 and v=0.5 are disclosed reconstruction choices because the paper does not specify their numerical values. The inconsistent escape equation is interpreted using its accompanying prose. Original-condition results use CEC2022, NP=50 and 75,000 FEs; the paper-comparison dimension remains an unresolved source detail.')
    p('DSPDE ablations change one intervention at a time: without_escape replaces model-based inferior escape with uniform random resets; without_linnik replaces elite updates with basic DE; without_social replaces ordinary updates with basic DE; frozen_roles fixes initial role membership while current ranks and model estimates continue to change.')
    p('2.2 DLS-DE. DLS-DE combines current-to-pbest mutation and an external archive with direction learning from promising unsuccessful trials, exponential crossover, successful-displacement weighting, adaptive sigma, two-phase F sampling and linear population reduction [2]. Native settings are NP=182 to 4, H=6, p=0.11, archive ratio 1.6, lambda=0.1, stagnation threshold 30, tau=0.3 and initial sigma=0.05. The learning gate follows Algorithm 5, rand>tau; the conflicting prose interpretation is documented.')
    p('The five native DLS-DE ablations remove direction learning, remove two-phase F sampling, fix sigma, replace displacement weighting with fitness-improvement weighting, or replace exponential crossover with binomial crossover. The remaining configuration stays unchanged. The existing 4,200 native coursework solutions were all reevaluated successfully under the delivered NumPy 2.3.5 dependency; the ten discrepancies previously observed under NumPy 1.26.4 disappeared after dependency matching.')
    p('2.3 PEMS-DE. PEMS-DE constructs potential scores from relative fitness improvements, partitions the population dynamically, and forms a fitness-weighted potential guide and an elite guide. Multi-stage mutation learning (MML), elite reinforcement (ERS), complementary learning (CLS), and success-history F/CR adaptation complete the method [3]. Default settings are NP=6D, initial mu_F=mu_CR=0.5, ERS coefficient 0.3, global stagnation threshold 5, individual threshold 20, learning rate 0.1, memory reset period 20, and elite proportion decreasing from 0.25 to 0.05.')
    p('The corrected implementation follows the individual loop in Algorithm 4. Parent donors are frozen at generation g, but successful-parameter sets and the archive are updated immediately after each individual; later targets can use those updates. Sampling widths can therefore change within a generation. Parameter means update at generation end, and memory/archive sets reset every 20 generations. Mutation and CLS calls stop at the exact remaining budget. CLS replaces stagnant individuals unconditionally, while the historical best is stored separately. The earlier batch-update implementation is not assumed statistically equivalent.')
    p('PEMS-DE original-condition reproduction uses the unchanged CEC2017-py reference supplied with the delivery through an opfunu interface adapter, with official F1 and F3-F30 numbering. Direct use of opfunu 1.0.4 CEC2017 class numbers is inappropriate: it provides 29 classes with a shifted numbering sequence. The reference objective is disclosed separately from the unmodified opfunu CEC2014 coursework objective. Previous delivery CSVs are excluded from the corrected formal statistics.')
    p('PEMS-DE ablations remove PEG, MML, ERS or CLS individually. Without PEG, guiding vectors fall back to the historical best. Without MML, one current-to-weighted-guide mutation with an archive direction is used throughout the run. Removing ERS retains ordinary binomial crossover; removing CLS disables only the stagnant-individual replacement.')
    p('2.4 PGE-DE. The team combination uses three source strategies: PEMS-DE potential guidance, DLS-DE two-phase F sampling, and DSPDE probabilistic escape. The configuration was frozen before team formal results were available. Its fixed-NP current-to-guide/1/bin backbone uses CR=0.9 and an H=6 success-history memory. It does not additionally adopt population reduction, an external archive, learned direction vectors, exponential crossover, adaptive sigma, ERS or CLS.')
    p('Potential guidance follows PEMS-DE equations 6-9: rank individuals by their relative fitness improvements, select ceil(cos(q*pi/3)*ceil(0.382*NP)) potential members, and form their fitness-weighted center. Mutation is v_i=x_i+F_i*[(guide-x_i)+(x_r1-x_r2)], followed by binomial crossover and clipping. The no-PEG team ablation instead uses a random p-best guide with p=0.11.')
    p('During the first 30% of the budget, F_i=clip(0.35+0.4*SR/(0.1+SR)+sin(2*pi*u)*(mean(M_F)-min(M_F)),0.35,0.65). Later, positive Cauchy samples use a randomly selected memory center and fixed sigma=0.05, capped at 1. Strictly improving ordinary candidates update the memory using improvement-weighted Lehmer means. Fixed sigma and improvement weighting are explicit transfer conventions, rather than claims that the whole DLS-DE adaptation mechanism has been reproduced. The no-phase ablation uses late-phase Cauchy sampling throughout.')
    p('Probabilistic escape identifies the current worst Ng targets and fits elite/global Gaussian models. Below the density threshold, an inferior target receives the DSPDE gradient/noise branch with probability 0.7 or the mirror branch otherwise. This replaces its existing candidate and still consumes only one evaluation. Escape-generated successes do not train F memory because those candidates were not generated by the sampled F. The no-escape ablation retains the ordinary DE candidates. The update order is guidance and roles, F sampling, normal mutation/crossover, escape replacement, repair and evaluation, selection, memory update, and trace recording.')

    head('3. Experimental results and analysis')
    p('3.1 Original-condition comparisons. DSPDE Table 7 reports raw objective values; DLS-DE Table 12 and PEMS-DE Table 2 report errors. DLS-DE and PEMS-DE paper summaries use 51 runs, whereas the coursework uses 20. These comparisons are descriptive because published mean/Std pairs do not provide the individual observations required for an equivalence test. Complete paired columns and differences appear in Appendix A.')
    p('The lower/equal/higher counts describe differences from published summaries. Lower reproduced means alone do not establish reproduction accuracy, and the largest absolute gaps also depend on the function scale.')
    for stem, label in [('dsp','DSPDE'),('dls','DLS-DE'),('pems','PEMS-DE')]:
        rows = read_csv(stem+'_paper_comparison.csv')
        lower = sum(float(r['mean_difference']) < -(1e-8+1e-10*abs(float(r['paper_mean']))) for r in rows)
        higher = sum(float(r['mean_difference']) > 1e-8+1e-10*abs(float(r['paper_mean'])) for r in rows)
        close = len(rows)-lower-higher
        p(f'{label}: the reproduced mean was lower on {lower} functions, within numerical tolerance on {close}, and higher on {higher}.')
        largest = max(rows,key=lambda r:abs(float(r['mean_difference'])))
        p(f"The largest absolute mean gap for {label} occurred on F{int(largest['function']):02d}: paper Mean {float(largest['paper_mean']):.4e} and Std {float(largest['paper_std']):.4e}; reproduced Mean {float(largest['reproduced_mean']):.4e} and Std {float(largest['reproduced_std']):.4e}; mean difference {float(largest['mean_difference']):.4e}.")
        if stem == 'pems':
            measured = next(r for r in read_csv('pems_native_statistics.csv') if int(r['function'])==int(largest['function']))
            if float(measured['worst']) > 10*max(float(measured['median']),1e-8):
                p(f"For that PEMS-DE function, the 20-run median error was {float(measured['median']):.4e} and the worst error was {float(measured['worst']):.4e}. The large upper-tail run values make the mean sensitive to the particular sample of runs; the Mean and Std must be read together.")
    p('The discrepancies must be interpreted against the disclosed source details: DSPDE has unresolved author-parameter and dimension settings; DLS-DE composition functions differ between opfunu and reference implementations; PEMS-DE uses the corrected individual-update order. Published summary tables alone cannot identify which implementation detail causes a discrepancy.')
    p('3.2 Single-paper ablations. The following counts compare each full method with its removal variant. Wins and losses are significant only after the stated family-wise Holm correction; ND means no difference detected, not equivalence. Mean-direction counts are descriptive and do not substitute for those tests.')
    for family, label in [('dsp_ablation','DSPDE'),('dls_ablation','DLS-DE'),('pems_ablation','PEMS-DE')]:
        p(label+' component results:')
        rows = [dict(variant=r['comparison'], wins=r['reference_wins'], nd=r['no_difference_detected'], losses=r['reference_losses'], mean_better=r['mean_better'], mean_worse=r['mean_worse']) for r in summary['comparisons'][family]]
        table(rows, [('variant','Removal variant'),('wins','Wins'),('nd','ND'),('losses','Losses'),('mean_better','Mean better'),('mean_worse','Mean worse')])
    for family, ref, removed, mechanism in [
        ('dsp_ablation','DSPDE','without_escape','DSPDE probabilistic escape'),
        ('dls_ablation','dls_de','no_two_phase','DLS-DE two-phase F sampling'),
        ('pems_ablation','PEMSDE','PEMS_no_peg','PEMS-DE potential guidance')
    ]:
        ranks = {r['algorithm']:float(r['mean_rank']) for r in summary['summaries'][family]['average_ranks']}
        effect = next(r for r in summary['comparisons'][family] if r['comparison']==removed)
        p(f"For {mechanism}, the full method's average rank was {ranks[ref]:.3f}, compared with {ranks[removed]:.3f} after removal; lower ranks are better within that ablation family. The full method had {effect['reference_wins']} significant wins and {effect['reference_losses']} significant losses against removal.")
    p('The selected strategies change the guide location, F sampling and inferior-candidate generation. Their distinct interfaces permit a combination without competing archives or population schedules. Pre-existing single-paper experiments informed the candidate selection. The corrected PEMS-DE and team experiments reported here evaluate that frozen choice.')
    p('3.3 Final five-algorithm comparison. Every algorithm uses the same CEC2014 objective implementation, D=10, fixed NP=100, 100,000 FEs and 20 runs. Average rank is the mean of 30 within-function mean-error ranks. It summarizes these fixed benchmark problems and is not itself a significance test.')
    ranking = [dict(algorithm=LABEL[r['algorithm']], mean_rank=r['mean_rank']) for r in summary['summaries']['final']['average_ranks']]
    table(ranking, [('algorithm','Algorithm'),('mean_rank','Average rank')])
    for r in summary['comparisons']['final']:
        p(f"PGE-DE versus {LABEL[r['comparison']]}: {r['reference_wins']} significant wins, {r['no_difference_detected']} ND outcomes and {r['reference_losses']} significant losses across 30 functions after Holm correction over the 120 final comparisons.")
    ranking_raw = sorted(summary['summaries']['final']['average_ranks'], key=lambda r:r['mean_rank'])
    team_rank = next(r['mean_rank'] for r in ranking_raw if r['algorithm']=='TEAM')
    p(f"PGE-DE obtained an average rank of {team_rank:.3f}. The lowest average rank was obtained by {LABEL[ranking_raw[0]['algorithm']]} ({ranking_raw[0]['mean_rank']:.3f}).")
    stats = read_csv('final_statistics.csv')
    lookup = {(int(r['function']),r['algorithm']):r for r in stats}
    differences = [(f,float(lookup[f,'TEAM']['mean'])-float(lookup[f,'DE']['mean'])) for f in range(1,31)]
    p('The following improvement and deterioration examples are selected by absolute mean difference to illustrate heterogeneity. Errors from differently scaled functions are not pooled into an overall score.')
    for label, candidates in [('Improvement',sorted([r for r in differences if r[1]<-1e-8],key=lambda r:r[1])[:2]),
                              ('Deterioration',sorted([r for r in differences if r[1]>1e-8],key=lambda r:-r[1])[:2])]:
        for fid, difference in candidates:
            p(f"{label} example F{fid:02d}: DE mean error {float(lookup[fid,'DE']['mean']):.4e}, PGE-DE mean error {float(lookup[fid,'TEAM']['mean']):.4e}, difference {difference:.4e}.")
    p('3.4 Team ablations. Each removal changes one mechanism in the frozen PGE-DE backbone. The family contains 90 tests. These interventions estimate conditional contributions within this implementation; their effects cannot be added to establish a causal interaction or guarantee transfer to another backbone.')
    for r in summary['comparisons']['team_ablation']:
        p(f"PGE-DE versus {r['comparison']}: {r['reference_wins']} significant wins, {r['no_difference_detected']} ND outcomes and {r['reference_losses']} significant losses after Holm correction.")
    team_ranks = {r['algorithm']:float(r['mean_rank']) for r in summary['summaries']['team_ablation']['average_ranks']}
    team_best = min(team_ranks,key=team_ranks.get)
    p(f"Within the four-way team ablation, the full PGE-DE rank was {team_ranks['TEAM']:.3f}; the lowest rank was {team_ranks[team_best]:.3f} for {team_best}. Comparing this ordering with each source-paper ablation shows whether a mechanism's benefit transfers to the combined backbone. Differences across these settings also change the surrounding operators, so they do not isolate a formal interaction effect.")
    guidance_source = next(r for r in summary['comparisons']['pems_ablation'] if r['comparison']=='PEMS_no_peg')
    guidance_team = next(r for r in summary['comparisons']['team_ablation'] if r['comparison']=='TEAM_no_peg')
    p(f"Potential guidance shows the clearest transfer failure: full PEMS-DE had {guidance_source['reference_wins']} significant wins and {guidance_source['reference_losses']} losses against its no-PEG variant, whereas full PGE-DE had {guidance_team['reference_wins']} wins and {guidance_team['reference_losses']} losses against removing guidance. In the team backbone, removing this mechanism improved the average rank from {team_ranks['TEAM']:.3f} to {team_ranks['TEAM_no_peg']:.3f}. The different mutation and selection context matters when transferring a guide.")
    undetected_components = []
    for key, mechanism in [('TEAM_no_phase','two-phase F sampling'),('TEAM_no_escape','probabilistic escape')]:
        effect = next(r for r in summary['comparisons']['team_ablation'] if r['comparison']==key)
        if effect['reference_wins']==effect['reference_losses']==0:
            undetected_components.append(mechanism)
    if undetected_components:
        p('For '+ ' and '.join(undetected_components)+', none of the 30 comparisons per component reached significance after Holm correction. Their mean/rank directions are descriptive; these runs provide insufficient evidence to establish a benefit from these components.')

    head('4. Conclusions and limitations')
    p('The project completed three DE reconstructions, original-condition comparisons, component ablations and a common five-algorithm evaluation of the three-strategy PGE-DE combination.')
    against_de = next(r for r in summary['comparisons']['final'] if r['comparison']=='DE')
    final_ranks = {r['algorithm']:float(r['mean_rank']) for r in ranking_raw}
    p(f"The lowest average rank belonged to {LABEL[ranking_raw[0]['algorithm']]} ({ranking_raw[0]['mean_rank']:.3f}). PGE-DE ranked {team_rank:.3f}, compared with DE at {final_ranks['DE']:.3f}, and had {against_de['reference_wins']} significant wins and {against_de['reference_losses']} losses against DE across functions. Thus the combination improved some functions but did not obtain an overall rank advantage. Its potential-guidance removal result identifies the main candidate for a separately tested revision.")
    p('The evidence is limited to the selected ten-dimensional benchmark settings and 20 runs per condition. It does not establish performance at other dimensions or on all real applications. The fixed-NP DLS-DE control changes its native reduction mechanism, the PEMS-DE original-condition reference objective differs from the unmodified opfunu coursework objective, and some DSPDE source details remain unresolved. Internal implementation/data consistency is distinct from pointwise equivalence to official CEC kernels or exact replication of author MATLAB programs.')
    p('Numerical dependencies are part of reproducibility. All 4,200 native DLS-DE coursework solutions passed reevaluation under NumPy 2.3.5, resolving the ten earlier cross-version discrepancies. The 4,080 retained DSPDE records passed reevaluation in their NumPy 1.26.4 environment. Historical results were preserved rather than overwritten with values computed in another environment. New runs store complete solutions, actual FEs, seeds, histories, code/data hashes and dependency versions; selected full-budget runs were replayed exactly.')
    p('The coursework contribution is a three-strategy implementation with measured source and team ablations. Further work should examine the functions where removal improves performance, then test any revised mechanism on separate runs or benchmark settings.')

    head('References')
    for reference in [
        '[1] Qu C, Yuan J, Zhang L, Zhang X, Huang Z. DSPDE: A synergistic integration of dynamic stratification and probabilistic escape for enhanced differential evolution optimization. Swarm and Evolutionary Computation 104 (2026), 102380. DOI: 10.1016/j.swevo.2026.102380.',
        '[2] Chen J, Meng Z. An Adaptive Differential Evolution Algorithm with Exponential Crossover Based on a Learning Strategy Within the Difference Vector. Swarm and Evolutionary Computation 100 (2026), 102247. DOI: 10.1016/j.swevo.2025.102247.',
        '[3] Sahu D, Gupta S. Adaptive differential evolution with potential-elite guidance and multi-stage learning for numerical optimization and feature selection. Swarm and Evolutionary Computation 107 (2026), 102435. DOI: 10.1016/j.swevo.2026.102435.'
    ]:
        p(reference)
    for title, filename in [('A1. DSPDE original-condition comparison','dsp_paper_comparison.csv'),
                            ('A2. DLS-DE original-condition comparison','dls_paper_comparison.csv'),
                            ('A3. PEMS-DE corrected original-condition comparison','pems_paper_comparison.csv')]:
        head(title)
        p('Our summaries use 20 independent runs. Difference is Our Mean minus Paper Mean. DSPDE compares original objective values; DLS-DE and PEMS-DE compare errors. Paper means and standard deviations are source-table summaries, not synthetic individual observations.')
        table(read_csv(filename), [('function','F'),('reproduced_best','Our Best'),('paper_mean','Paper Mean'),('reproduced_mean','Our Mean'),('paper_std','Paper Std'),('reproduced_std','Our Std'),('mean_difference','Difference')],
              numeric=['reproduced_best','paper_mean','reproduced_mean','paper_std','reproduced_std','mean_difference'])
    for title, stem, condition in [
        ('B. Final five-algorithm comparison','final','CEC2014; D=10; fixed NP=100; 100000 FEs; n=20.'),
        ('C. PEMS-DE coursework ablations','pems_ablation','CEC2014; D=10; fixed NP=100; 100000 FEs; n=20.'),
        ('D. PGE-DE single-strategy ablations','team_ablation','CEC2014; D=10; fixed NP=100; 100000 FEs; n=20.'),
        ('E. DSPDE original coursework ablations','dsp_ablation','Unmodified opfunu CEC2014; D=10; NP=50; 75000 FEs; n=20.'),
        ('F. DLS-DE native ablations','dls_ablation','Unmodified opfunu CEC2014; D=10; NP=182 to 4 (DE fixed 182); 100000 FEs; n=20.')
    ]:
        values = read_csv(stem+'_statistics.csv')
        for first in range(1,31,5):
            head(title+f' F{first:02d}-F{first+4:02d}')
            p(condition+' Rank is computed within this table only. Std and Variance use n-1. Complete precision, Median, Worst and individual results are retained in CSV/JSON.')
            rows = [dict(r,label=f"F{int(r['function']):02d}/{r['algorithm']}") for r in values if first<=int(r['function'])<first+5]
            table(rows,[('label','F / Algorithm'),('best','Best'),('mean','Mean'),('std','Std'),('variance','Variance'),('rank','Rank')],numeric=['best','mean','std','variance'])
    markdown = '\n'.join(lines)
    allowed = [identity['tutor_chinese']]+[m['chinese'] for m in identity['members']]
    probe = markdown
    for name in allowed:
        probe = probe.replace(name,'')
    assert not re.search(r'[\u3400-\u9fff]',probe)
    (OUT/'Project2_Report.md').write_text(markdown,encoding='utf-8')
    bundled = '/home/yinwhcmy/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3'
    renderer = '/home/yinwhcmy/.codex/plugins/cache/openai-primary-runtime/documents/26.1105.12137/skills/documents/render_docx.py'
    subprocess.run([bundled,str(ROOT/'build_template_docx.py')],check=True)
    rendered = ROOT/'template_work'/('final_english_'+datetime.now().strftime('%H%M%S'))
    subprocess.run([bundled,renderer,str(OUT/'Project2_Report.docx'),'--output_dir',str(rendered),'--emit_pdf'],check=True)
    reader = PdfReader(rendered/'Project2_Report.pdf')
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.add_metadata({'/Title':'Project2 Differential Evolution Experiment Report','/Author':'殷明骏',
                         '/Creator':'殷明骏','/Producer':'殷明骏','/Subject':'202483890029'})
    (OUT/'pdf').mkdir(exist_ok=True)
    with (OUT/'pdf/Project2_Report.pdf').open('wb') as f:
        writer.write(f)
    info = dict(author='殷明骏',student_id='202483890029',language='English except bilingual personal names',
                total_pages=len(reader.pages),figures=30,source='same retained-template DOCX as final Word deliverable',
                source_render=str(rendered.relative_to(ROOT)),members=identity['members'])
    (OUT/'report_build.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
    old_preview = OUT/'Project2实验报告.docx'
    if old_preview.exists():
        old_preview.replace(ROOT/'template_work/Project2_Header_Preview.docx')
    print(json.dumps(info,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
