"""Template-based English report. Author: 殷明骏, 202483890029."""
from pathlib import Path
from copy import deepcopy
import csv
import hashlib
import json
import re
import sys
import tempfile
import zipfile
from lxml import etree
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from docx.enum.text import WD_TAB_ALIGNMENT
import report_components as c
from clean_metadata import clean_docx
from paper_layout import enable_paper_body, preserve_cover
from journal_layout import enable_journal_layout

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'
DOC = OUT / 'Project1_Report.docx'
REFERENCE = ROOT / 'source/template/Project2_Report_reference.docx'
Report, mr, sub, frac = c.Report, c.mr, c.sub, c.frac

def read(name):
    with (OUT / name).open(encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def scientific(x):
    return '0' if float(x) == 0 else f'{float(x):.3e}'

def save(r):
    r.close_layout()
    preserve_cover(r,ROOT,c.WIDTH)
    for p, label, target in r.contents:
        section = next(x for x in c.TITLES if x['title'] == target)
        for child in list(p._p):
            if child.tag != qn('w:pPr'):
                p._p.remove(child)
        link = OxmlElement('w:hyperlink')
        link.set(qn('w:anchor'), section['anchor'])
        rr = OxmlElement('w:r')
        rp = OxmlElement('w:rPr')
        ff = OxmlElement('w:rFonts')
        ff.set(qn('w:ascii'), 'Times New Roman')
        ff.set(qn('w:hAnsi'), 'Times New Roman')
        rp.append(ff)
        sz = OxmlElement('w:sz')
        sz.set(qn('w:val'), '19')
        rp.append(sz)
        rr.append(rp)
        tt = OxmlElement('w:t')
        tt.text = label
        rr.append(tt)
        link.append(rr)
        p._p.append(link)
        rr = OxmlElement('w:r')
        rr.append(OxmlElement('w:tab'))
        p._p.append(rr)
        field = OxmlElement('w:fldSimple')
        field.set(qn('w:instr'), 'PAGEREF ' + section['anchor'] + ' \\h')
        rr = OxmlElement('w:r')
        rr.append(deepcopy(rp))
        tt = OxmlElement('w:t')
        tt.text = str(r.pages.get(target, ''))
        rr.append(tt)
        field.append(rr)
        p._p.append(field)
    cp = r.doc.core_properties
    cp.author = cp.last_modified_by = '殷明骏'
    cp.title = 'Project 1 Basic Differential Evolution'
    cp.subject = ''
    cp.keywords = ''
    cp.comments = ''
    editable = {'word/document.xml','word/styles.xml','word/settings.xml', 'word/_rels/document.xml.rels', '[Content_Types].xml', 'docProps/core.xml'}
    with tempfile.TemporaryDirectory(dir=ROOT / 'report_work') as t:
        built = Path(t) / 'report.docx'
        r.doc.save(built)
        with zipfile.ZipFile(REFERENCE) as original, zipfile.ZipFile(built) as generated, zipfile.ZipFile(DOC, 'w', zipfile.ZIP_DEFLATED) as final:
            for name in original.namelist():
                if re.fullmatch(r'word/(header|footer)\d+\.xml', name):
                    editable.add(name)
                final.writestr(name, generated.read(name) if name in editable else original.read(name))
            for name in generated.namelist():
                if name not in original.namelist():
                    final.writestr(name, generated.read(name))
    clean_docx(DOC)
    with zipfile.ZipFile(REFERENCE) as a, zipfile.ZipFile(DOC) as b:
        preserved = [n for n in a.namelist() if n not in editable]
        assert all(a.read(n) == b.read(n) for n in preserved)
        aa = etree.fromstring(a.read('word/document.xml'))
        bb = etree.fromstring(b.read('word/document.xml'))
        ns = {'w': c.W}
        ap = aa.find('w:body', ns)
        bp = bb.find('w:body', ns)
        for i in range(15):
            before = etree.tostring(ap[i], method='c14n')
            after = etree.tostring(bp[i], method='c14n')
            if i == 2:
                after = after.replace(b'Project 1 Basic Differential Evolution', b'Project 2 Differential Evolution')
            assert before == after, ('Opening changed outside experiment-name slot', i)
        assert len(bp.findall('.//w:sectPr',ns))>1, 'Journal sections missing'
        visible = ''.join(bb.itertext())
        identity = json.loads((ROOT / 'source/report_identity.json').read_text())
        for name in [identity['tutor_chinese']] + [m['chinese'] for m in identity['members']]:
            visible = visible.replace(name, '')
        assert not re.search(r'[\u3400-\u9fff]', visible)
        assert 'Project 2' not in visible
    (OUT / 'template_fidelity.json').write_text(json.dumps(dict(author='殷明骏', student_id='202483890029',
        reference_sha256=hashlib.sha256(REFERENCE.read_bytes()).hexdigest(), source_opening_preserved=True,
        permitted_opening_change='Experiment name and replacement of preview by user-specified contributions', section_geometry_preserved=False, cover_geometry_preserved=True, body_geometry='User-authorized full-width displays and two-column interpretation',
        preserve_only_parts=preserved, all_preserve_only_parts_identical=True), ensure_ascii=False, indent=2))
    (OUT / 'report_contents.json').write_text(json.dumps([dict(label=l,target=t) for _,l,t in r.contents],indent=2)+'\n')
    (OUT / 'report_sections.json').write_text(json.dumps(c.TITLES, indent=2))
    (OUT / 'report_figures.json').write_text(json.dumps(c.FIGURES, indent=2))
    text='\n\n'.join(c.TEXT)
    formulas={1:r'$v_i = x_{r1} + F(x_{r2} - x_{r3})$',
              2:r'$e_r = |b_r - f^*|,\quad r=1,\ldots,20$',
              3:r'$\bar e = \frac{\sum_{r=1}^{20} e_r}{20},\quad s^2 = \frac{\sum_{r=1}^{20}(e_r-\bar e)^2}{19}$'}
    for number,formula in formulas.items():
        text=re.sub(r'^Equation '+str(number)+r': .*$',lambda m:'Equation '+str(number)+': '+formula,text,flags=re.M)
    (OUT / 'Project1_Report.md').write_text(text, encoding='utf-8')

def main(pages=None):
    c.TITLES.clear(); c.TEXT.clear(); c.FIGURES.clear()
    r=Report(pages)
    stats=read('summary_error.csv');by_id={x['function']:x for x in stats}
    raw=[json.loads(p.read_text()) for p in sorted((ROOT/'results').glob('F*_run*.json'))]
    identity=json.loads((ROOT/'source/report_identity.json').read_text())
    c.TEXT.extend(['# NUIST Experiment Report','Course name: Embedded System',
        'Experiment name: Project 1 Basic Differential Evolution','Date: 2026-11-09',
        'Tutor: '+identity['tutor_chinese']+' / '+identity['tutor_english'],
        'College: '+identity['college_english'],'Class: '+identity['class_english']])
    c.TEXT.extend('Name: '+m['chinese']+' / '+m['english']+'   Student ID: '+m['student_id'] for m in identity['members'])
    r.h('Contributions',2,toc=False)
    r.p('Mingjun Yin completed the experiment and prepared the report.','Report Note')
    r.p('Hongrui Ding contributed to data collection and plotting.','Report Note')
    r.p('Lühao Zhang refined the visual presentation and report layout.','Report Note')
    enable_paper_body(r)
    enable_journal_layout(r)
    r.h('Abstract',newpage=True,toc=False)
    r.p('Basic differential evolution exhibits distinct accuracy and variability patterns across the CEC2014 suite. '
        'We evaluated generational DE/rand/1/bin on all 30 functions in ten dimensions, using 20 independent runs per function and exactly 100,000 objective evaluations per run. '
        'Across 600 runs, 80 reached an absolute error of at most 10⁻⁸, including every run on F01 to F03. '
        'F04 split between accurate convergence and nonzero-error outcomes, whereas large-error tails raised the F30 mean. '
        'Complete functionwise statistics, seed distributions and convergence histories distinguish typical accuracy, repeatable residual error and occasional favorable runs. '
        'A separate audit of 660 benchmark probes identifies evaluator differences on 13 functions and places the published DE-VCR comparison in its implementation context. '
        'Saved solutions and independent summary recomputation connect the analysis to the retained experiments, establishing a baseline for subsequent strategy comparisons.','Paper Abstract')
    r.p('Keywords: Differential evolution; CEC2014; benchmark evaluation; stochastic variability; reproducibility','Paper Keywords')
    r.h('1 Introduction')
    r.p('Basic differential evolution searches with a population updated by mutation, crossover and greedy selection. '
        'We evaluate generational DE/rand/1/bin on all 30 CEC2014 functions in ten dimensions [1,2]. '
        'Twenty independent runs per function reveal typical accuracy, seed variability and convergence under a common evaluation budget. '
        'Figure 1 connects this design to the 600 saved records.')
    r.fig('00_workflow','Figure 1. A complete, fixed-budget experiment. a Each cell represents one retained function/run pair; all 600 are present. '
        'b Initialization consumes 100 FEs, followed by 999 generations of 100 trials. Every run reaches 100,000 FEs and saves its final solution and history.')
    r.h('2 Methods')
    r.h('2.1 Experimental protocol',2,toc=False)
    r.table(['Parameter', 'Setting'], [
        ['Algorithm', 'DE/rand/1/bin'], ['Objective implementation', 'Unmodified opfunu 1.0.4 CEC2014 F1 to F30'],
        ['Dimension and bounds', 'D = 10; each coordinate in [−100, 100]'], ['Population size', 'NP = 100, fixed'],
        ['Scale factor and crossover', 'F = 0.5; CR = 0.9'], ['Evaluation budget', '100,000 actual FEs per run, including initialization'],
        ['Independent runs', '20 per function; 600 runs in total'], ['Initialization', 'Uniform within the search box'],
        ['Boundary repair', 'Coordinatewise clipping before crossover'], ['Replacement', 'Strict improvement; ties retain the parent'],
        ['Population update', 'All donor vectors come from the preceding generation'], ['Random streams', 'PCG64; base seed 20261026'],
        ['Experiment date', '26 October 2026']
    ], [.32, .68], size=10, caption='Table 1. Experimental conditions fixed before the retained runs.')
    r.p('NP, F and CR follow the course parameter example [2]; the 10,000D budget follows the supplied paper [3]. '
        'Clipping and strict generational replacement define this control. The 600 runs consumed 60,000,000 FEs without threshold-based early stopping.','Report Note')

    r.h('2.2 Differential evolution update', 2, newpage=True, toc=False)
    r.fig('00_de_update','Figure 2. How one DE update transforms a population member. '
        'a An illustrative two-dimensional projection shows the donor difference, its scaled translation from the base vector and boundary clipping. '
        'b The trial inherits coordinates from its parent or clipped mutant; the outlined coordinate is forced to come from the mutant. '
        'c Strict selection accepts improvement and otherwise retains the parent. The geometry and mask are explanatory schematics, not recorded trajectories.')
    r.p('Each run initializes 100 vectors uniformly within the search box. For target i, three mutually distinct donors exclude i and come from the preceding generation. Their difference defines a search direction, scaled by F and translated from the base vector:')
    r.equation([sub('v','i'),mr(' = '),sub('x','r1'),mr(' + F('),sub('x','r2'),mr(' − '),sub('x','r3'),mr(')')],1)
    r.p('The mutant is clipped coordinatewise before binomial crossover. Each coordinate uses the mutant with probability CR, and one uniformly selected coordinate is mandatory. A trial replaces its parent only when its objective is lower. All trials are constructed before replacement, preserving a common donor generation.')
    r.p('Initialization consumes 100 FEs; 999 complete generations consume the remaining 99,900. Fixed F and CR isolate the basic mutation and crossover operators.','Report Note')

    r.h('2.3 Outcome measures',2,toc=False)
    r.p('Each run contributes its best objective value at the final evaluation budget. '
        'For function k, the declared optimum is f* = 100k, and the reported absolute error is')
    r.equation([sub('e', 'r'), mr(' = |'), sub('b', 'r'), mr(' − f*|,     r = 1, …, 20')], 2)
    r.p('The arithmetic mean and sample variance use all 20 independent final errors. '
        'The sums in Equation 3 run over these 20 observations. '
        'Std is the square root of the sample variance.')
    r.equation([mr('ē = '), frac('∑ eᵣ', '20'), mr(',   s² = '), frac('∑ (eᵣ − ē)²', '19')], 3)
    r.p('Best and Worst are the minimum and maximum; Median is the average of the 10th and 11th sorted errors. Threshold counts use an error of at most 10⁻⁸. Numerical summaries retain exact small errors.','Report Note')
    r.h('2.4 Record verification and reproduction', 2, toc=False)
    r.p('Independent recomputation verified 600 saved solutions and 360 summary cells. The runtime was Python 3.12.3, NumPy 1.26.4 and opfunu 1.0.4. PCG64 seeds derive from SeedSequence([20261026, function number, run number]), independently of scheduling.')
    r.p('Checks covered unique run pairs, FE accounting, monotone histories, final fitness agreement and source/per-run hashes. Resume requires matching configuration and sources. Numerical-library rounding can change F28 reevaluation near Schwefel period boundaries; original vectors and fitness values are retained.')

    r.h('3 Results and analysis',newpage=True)
    r.h('3.1 High accuracy is concentrated in a few functions',2)
    r.fig('01_accuracy','Figure 3. Accuracy and repeatability across CEC2014. '
        'a Medians and interquartile ranges of final absolute errors, with 20 independent runs per function. '
        'b Counts at an error of at most 10⁻⁸. Alternating pale bands distinguish unimodal, basic multimodal, hybrid and composition groups. '
        'Errors below 10⁻¹² use a logarithmic display floor; numerical statistics retain exact values.')
    r.p('Of the 600 runs, 80 reached the interpretation threshold. F01, F02 and F03 reached it in all 20 runs. '
        'F04 and F06 reached it in 6 and 13 runs, respectively; F17 contributed one additional run. '
        'Threshold attainment was therefore concentrated in a small subset of functions.')
    r.p('The remaining functions span repeatable residual errors and variable outcomes. '
        'F26 had a median error of about 100.14 and a sample standard deviation of only 0.0251, '
        'so its runs consistently ended near the same nonzero residual. '
        'F23 showed a similar pattern. A narrow distribution alone does not establish accurate convergence.')
    r.h('3.1.1 Convergence across the benchmark',2,toc=False)
    r.fig('04_heatmap','Figure 4. Convergence across the benchmark. '
        'a,b Median absolute errors for F01–F15 and F16–F30 share one logarithmic colour scale; brighter cells indicate higher errors. '
        'Each cell summarizes all 20 independent runs. '
        'Recorded checkpoints are not interpolated; errors ≤10⁻¹² share a display floor.')
    r.p('The common colour scale separates the near-zero trajectories on F01 to F03 from persistent residual errors across much of the suite. '
        'F11 continues to improve while F26 settles near a stable nonzero level. The detailed curves distinguish these behaviours within each function.')
    r.h('3.2 Complete experimental statistics',2,newpage=True)
    r.p('Table 2 reports all six required statistics for every function after 100,000 FEs. '
        'Each row summarizes 20 independent runs; Std and variance use denominator 19. '
        'Values are rounded to four significant figures, with full precision retained in the accompanying numerical files.','Report Note')
    r.table(['Function','Best','Median','Mean','Worst','Std','Variance'],
        [[x['function']]+[scientific(x[k]) for k in ['best','median','mean','worst','std','variance']] for x in stats],
        [.11]+[.1483333333]*6,groups=[0 if i<3 else 1 if i<16 else 2 if i<22 else 3 for i in range(30)],size=9.5,
        caption='Table 2. Complete final absolute-error statistics for CEC2014 10D.')
    r.p('F01 to F03 are unimodal, F04 to F16 basic multimodal, F17 to F22 hybrid, and F23 to F30 composition functions. '
        'The table preserves functionwise scales. For example, the very small dispersion on F26 accompanies a persistent residual, '
        'whereas the large F30 variance reflects strong seed sensitivity.','Report Note')
    r.h('3.3 Split outcomes and tails separate mean from median',2,newpage=True)
    r.fig('02_variability','Figure 5. Split outcomes and tails separate the mean from the median. '
        'a All 20 final errors for F04 and F06, separated vertically to avoid overlap. Counts at the 10⁻¹² display floor are explicit; the dashed line marks 10⁻⁸. '
        'b,c All 20 errors for F30 and F22 ordered from smallest to largest, on independent linear scales. Solid reference lines mark medians and dashed lines mark means.')
    r.table(['Function','Median','Mean','Worst'],[[fid]+[scientific(by_id[fid][k]) for k in ['median','mean','worst']] for fid in ['F04','F06','F22','F30']],
        [.16,.28,.28,.28],size=10,caption='Table 3. Contrasting final-error distributions.')
    r.p('F04 and F06 illustrate split outcomes. On F04, six runs reached the threshold while many remaining runs ended near an error of 34.78. '
        'On F06, 13 near-zero outcomes pulled the median below the mean. These distributions explain why a single center statistic can conceal distinct outcomes.')
    r.p('F22 and F30 show upper tails. The worst F30 error was about 49,019, around 21.2 times its median of 2,312. '
        'This tail raised both the mean and the sample standard deviation. All four cases were selected descriptively from the retained results.')
    r.h('3.4 Late progress distinguishes improvement from plateaus',2,newpage=True)
    r.fig('03_convergence','Figure 6. Late-budget improvement is function dependent. '
        'a Percentage reduction in median error from 49,100 to 100,000 FEs, relative to the median at 49,100; this is the last logged point before 50,000 FEs. '
        'b,c Late-window error histories for F11 and F26. Lines show medians and best final runs, bands show IQRs over 20 independent runs; the y axes are logarithmic and independently scaled.')
    r.p('The additional budget produces different gains across functions. On F11, median error decreases from 1.252 × 10³ at 49,100 FEs to 1.090 × 10³ at 100,000 FEs, a 13.0% reduction. '
        'F22 improves from 17.15 to 0.929 over the same interval. A fixed stopping budget therefore captures some functions while progress is still visible.')
    r.p('F26 changes by only 0.0462%, from 100.187 to 100.141, while F23 and F27 are almost unchanged. '
        'These are persistent residual plateaus within the observed budget. '
        'Full raw-objective curves follow, with each final median error reported in Table 2.')
    for i,first in enumerate(range(1,31,15)):
        title='3.5 Complete convergence curves' if i==0 else f'Convergence curves F{first:02d} to F{first+14:02d}'
        r.h(title,2,newpage=True)
        r.fig(f'curves_{first:02d}_{first+14:02d}',f'Figure {7+i}. Objective histories for F{first:02d}–F{first+14:02d}. '
            'Blue lines and bands show medians and IQRs across all 20 runs; orange dashed lines show the best final run. '
            'Every panel uses its own logarithmic scale and reports the declared optimum f*; final error statistics are given in Table 2. '
            'Markers identify recorded checkpoints; all logged points contribute to the traces. Visible optima are dotted.')
        r.p(('F01 to F03 approach their optima, whereas the best final run separates from the median on F04 and F06. All 20 independent histories contribute to each median and IQR; every logged checkpoint is drawn.' if i==0 else 'F16 completes the basic multimodal group, F17–F22 are hybrid and F23–F30 are composition functions. Persistent residuals on F23 and F26 contrast with the wide seed variability on F27 and F30.'))
    r.h('3.6 Benchmark and literature comparison',2,newpage=True)
    r.p('The supplied DE-VCR paper reports CEC2014 10D results in Table 20 [3]. '
        'Table 4 places its published means and standard deviations beside the complete basic-DE results. '
        'The comparison conditions in Table 5 define how these values can be interpreted.')
    r.h('3.6.1 Complete published comparison',2)
    r.p('The DE-VCR columns are transcribed from Table 20 [3], based on 51 runs. '
        'The basic-DE columns use the 20 runs per function in this experiment. '
        'Asterisks mark functions with pointwise evaluator differences.','Report Note')
    comparisons=read('paper_context.csv')
    r.table(['Function','Basic DE mean','Basic DE Std','DE-VCR mean','DE-VCR Std'],
        [[x['function']+('*' if int(x['function'][1:]) in list(range(17,28))+[29,30] else '')]+[scientific(x[k]) for k in ['basic_de_mean','basic_de_std','paper_de_vcr_mean','paper_de_vcr_std']] for x in comparisons],
        [.12,.22,.22,.22,.22],groups=[0 if i<3 else 1 if i<16 else 2 if i<22 else 3 for i in range(30)],size=9.5,caption='Table 4. Complete final-error comparison context.')
    r.p('* F17 to F27, F29 and F30 differed in the pointwise evaluator audit. '
        'The table preserves all values without asserting a matched algorithm ranking.','Report Note')
    r.h('3.6.2 Comparison conditions',2,toc=False)
    r.table(['Condition','This experiment','DE-VCR paper'],[
        ['Algorithm','Basic DE/rand/1/bin','Improved DE-VCR'],['Benchmark and dimension','CEC2014, 10D','CEC2014, 10D'],
        ['Budget per run','100,000 FEs','100,000 FEs'],['Independent runs','20','51'],
        ['Implementation','Python and opfunu 1.0.4','MATLAB R2024a'],['Reported spread','Sample Std and variance','Published Std'],
        ['Boundary and update rules','Clipping; strict generational selection','Not established as matching this control']],
        [.30,.35,.35],size=10,caption='Table 5. Conditions affecting the published comparison.')
    r.p('The published table reports improved variants. Its values therefore provide context for basic DE rather than a matched basic-DE reproduction target. '
        'The implemented control follows the paper’s basic procedure: distinct donors, differential mutation, binomial crossover with one mandatory coordinate, and greedy selection.')
    r.h('Benchmark implementation',2,toc=False)
    r.p('A separate reference-source audit compared 22 points per function, or 660 probes in total, '
        'and found pointwise differences on 13 functions: F17 to F27, F29 and F30 [5].')
    with (ROOT/'reference/cec2014_audit/cec2014_pointwise.csv').open(encoding='utf-8-sig') as f:
        probes={int(x['function']):x for x in csv.DictReader(f)}
    r.table(['Function','Mismatched probes','Largest absolute difference'],
        [[f'F{fid:02d}',probes[fid]['mismatches']+'/22',scientific(probes[fid]['max_abs_difference'])] for fid in [17,29,30]],
        [.18,.36,.46],size=10,caption='Table 6. Representative pointwise evaluator differences.')
    r.p('The experiment retains the course-requested opfunu evaluator and its original 600 runs. '
        'Evaluator differences may contribute to literature gaps, especially on F29. These probes are separate from the optimization runs.')
    r.h('4 Conclusions')
    r.p('Basic DE/rand/1/bin reaches high accuracy on F01 to F03 under the fixed evaluation budget, '
        'while other functions reveal persistent residual errors, split outcomes or pronounced seed variability. '
        'The F26 residual and F30 upper tail show why typical accuracy, dispersion and convergence history must be read together.')
    r.p('Late-budget progress is also function dependent: from 49,100 to 100,000 FEs, median error falls by 13.0% on F11 and only 0.0462% on F26. '
        'Complete functionwise statistics and residual trajectories therefore complement final accuracy in this baseline. '
        'Saved-solution checks and the evaluator audit define the recorded implementation and the conditions for subsequent strategy comparisons.')
    r.h('References')
    refs=[
        '[1] Course materials. Project Introduction. Project description 1 and report requirements.',
        '[2] Course materials. Test condition. Project 1 benchmark, parameter example and required statistics.',
        '[3] Zhao L, Sun L, Song Z, Zhang Q, Matsveichuk N, Sotskov Y. Differential evolution with a variance contribution ratio-based diversity enhancement mechanism for numerical optimization. Swarm and Evolutionary Computation 104 (2026), 102359. doi:10.1016/j.swevo.2026.102359. Section 4 and Table 20.',
        '[4] opfunu contributors. opfunu version 1.0.4. CEC2014 implementation. https://pypi.org/project/opfunu/1.0.4/.',
        '[5] Liang JJ and CEC2014 benchmark contributors. CEC2014 C test-function source and input data. Retained official archive from github.com/P-N-Suganthan/CEC2014. Independent pointwise comparison retained with the project.'
    ]
    for text in refs:
        para=r.p(text,'Paper Reference')
        para.paragraph_format.keep_with_next=False
        para.paragraph_format.keep_together=True
    r.doc.paragraphs[-1].paragraph_format.keep_with_next=False
    save(r)
    print('Created revised report with contributions, process diagrams and all results in the main text')


if __name__=='__main__':
    main(json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv)>1 else None)
