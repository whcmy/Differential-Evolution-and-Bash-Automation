"""Integrate confirmation into the retained report template. Author: 殷明骏."""
from pathlib import Path
import csv
import json
import re
import sys
import zipfile
from copy import deepcopy
from lxml import etree
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from build_journal_docx import Journal, visible, WIDTH
from analyze_validation import MAIN, ABLATION
from plot_validation import DISPLAY
BASE=ROOT.parent/'backups/2026-11-16_before_report2_algorithm_improvement/project2_final/output/Project2_Report.docx'
ANALYSIS=ROOT/'improvement/analysis'
FIGURES=json.loads((ROOT/'improvement/baseline_report_figures.json').read_text())
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm':'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}


def read(name):
    with (ANALYSIS/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))


def number(value):
    x=float(value)
    return '0' if x==0 else f'{x:.3e}'


class Revision(Journal):
    def __init__(self):
        super().__init__();self.bookmark=2000

    def h(self,text,level=1):
        self.section(2)
        p=self.p(text,f'Journal Heading {level}')
        self.bookmark+=1;name=f'revision_{self.bookmark}'
        start=OxmlElement('w:bookmarkStart');start.set(qn('w:id'),str(self.bookmark));start.set(qn('w:name'),name)
        end=OxmlElement('w:bookmarkEnd');end.set(qn('w:id'),str(self.bookmark))
        p._p.insert(0,start);p._p.append(end)
        self.titles.append(dict(title=text,anchor=name,level=level))

    def new_table(self,caption,headers,rows):
        self.section(1);self.p(caption,'Journal Caption',keep=True)
        temp=Document();table=temp.add_table(rows=1,cols=len(headers))
        for cell,text in zip(table.rows[0].cells,headers):
            cell.text=str(text)
            for r in cell.paragraphs[0].runs:r.bold=True
        header=OxmlElement('w:tblHeader');table.rows[0]._tr.get_or_add_trPr().append(header)
        for values in rows:
            for cell,text in zip(table.add_row().cells,values):cell.text=str(text)
        if len(headers)==7 and headers[:2]==['F','Algorithm']:
            widths=[.4,1.45]+[(WIDTH-1.85)/5]*5
            for col,width in zip(table.columns,widths):col.width=Inches(width)
        borders=OxmlElement('w:tblBorders')
        for edge in ['top','bottom','left','right','insideH','insideV']:
            e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single' if edge in ['top','bottom'] else 'nil');e.set(qn('w:sz'),'5');e.set(qn('w:color'),'222222');borders.append(e)
        table._tbl.tblPr.append(borders)
        self.table(table._tbl)

    def equation(self,text):
        self.section(2)
        p=self.doc.add_paragraph();p.style=self.doc.styles['Journal Body']
        omp=OxmlElement('m:oMathPara');om=OxmlElement('m:oMath');run=OxmlElement('m:r');t=OxmlElement('m:t');t.text=text
        run.append(t);om.append(run);omp.append(om);p._p.append(omp)
        self.md.append(text)


def method(j):
    j.h('2.5 Revised potential and elite guidance',2)
    j.p('The original PGE-DE is retained as the predecessor. Its potential-guidance removal improved four functions after correction, while the escape removal produced no detected difference. These development observations motivated a smaller combination of stochastic potential/elite guidance and two-phase success-history parameter control [2,3]. The revision is denoted APE-DE; it is a coursework design rather than a reproduction of a published method.')
    j.figure('revision_mechanism','Figure 0. Guide interfaces in the predecessor and revision. (a) The predecessor gives all targets a shared weighted guide. (b) APE-DE samples actual elite or improving population members independently, with a historical archive supplying differential alternatives. The coordinates and arrows are explanatory schematics, not measured trajectories or proof of a diversity gain.')
    j.section(2)
    j.p('For each target, an elite guide is sampled uniformly from the best 11% of the current population. With probability 0.25(1−r), where r is the consumed evaluation fraction, it is replaced by an independently sampled improving member from the better half of the population. The potential pool is empty in the initial generation, when every guide comes from the elite pool. No shared centroid is used.')
    j.equation('vᵢ = xᵢ + Fᵢ(gᵢ − xᵢ + xᵣ₁ − zᵣ₂)                    (4)')
    j.p('The vector z is drawn from the current population and an archive of replaced parents. Differential donors exclude the target and each other. Binomial crossover forces one mutant coordinate. Out-of-bounds trial coordinates move to the midpoint between the parent and the violated bound. Strict improvements replace their parents; archive retention is random and limited to 1.6NP.')
    j.p('During the first 30% of the budget, F follows the retained DLS-inspired success-rate and sinusoidal rule, bounded to [0.35, 0.65]. Later values come from a positive Cauchy distribution centered on a sampled success-history cell, with scale 0.1 and a cap of 1. CR is sampled from a clipped normal distribution with scale 0.1. Successful fitness gains weight the F Lehmer mean and CR arithmetic mean; both memories contain six cells initialized to 0.5. These F/CR adaptation details are revision choices, not a claim of exact source-algorithm identity.')
    j.new_table('Table 4. Fixed APE-DE settings selected before independent confirmation.',
                ['Setting','Value'],[
                    ['Population and budget','NP 100; 100,000 actual FEs, including initialization'],
                    ['Elite pool','Top max(2, round(0.11NP)) members'],
                    ['Potential eligibility','Positive previous-generation improvement; fitness no worse than median'],
                    ['Potential sampling probability','0.25(1 − consumed FEs / budget)'],
                    ['Parameter memory','Six cells; initial F and CR means 0.5'],
                    ['Early / late F','First 30%: success-rate rule; remainder: positive Cauchy, scale 0.1'],
                    ['CR','Clipped normal, memory center and scale 0.1'],
                    ['Archive and repair','Random retention to 1.6NP; parent-bound midpoint'],
                    ['Selection and update','Strict improvement; frozen generation parents'],
                    ['Removed module','No density-based probabilistic escape']])
    j.section(2)
    j.p('Development used five already observed seeds on all 30 functions (450 new runs across the full method and two removals). APE-DE had the third-lowest mean rank among nine development methods: its mean errors were lower on 19 functions than DE and on 18 than PGE-DE. These results selected the implementation; they do not contribute to the independent sample or establish confirmatory significance.')


def confirmation(j,summary):
    ranks={r['algorithm']:r['mean_rank'] for r in summary['mean_ranks']}
    counts={r['comparison']:r for r in summary['comparisons']}
    j.h('6 Independent validation of APE-DE')
    j.h('6.1 Frozen design and independent observations',2)
    j.p('The selected implementation was frozen before the independent sample began. Master seed 20261117 generated 20 paired runs on each CEC2014 function for DE, DSPDE, fixed-NP DLS-DE, PEMS-DE, the original PGE-DE and APE-DE. Two APE-DE removals were also run with the same seeds. All eight methods used dimension 10, NP 100 and exactly 100,000 objective evaluations including initialization. The independent experiment therefore contains 4,800 runs; none of the 450 development runs is counted in this sample.')
    j.p('The source hashes, full method list, seed derivation and statistical families were recorded before confirmation outcomes were inspected. The primary family contains 60 APE-DE comparisons against DE and PGE-DE across 30 functions. The paper-control family contains 90 comparisons against DSPDE, DLS-DE and PEMS-DE; the ablation family contains 60 comparisons against the two removals. Each family uses two-sided paired Wilcoxon tests and Holm correction at 0.05, retaining the numerical tie rule in Section 1.2. A nonsignificant result is labelled not detected and is not treated as equivalence.')
    j.h('6.2 Performance relative to the predecessor and controls',2)
    a,b=counts['DE'],counts['TEAM']
    j.p(f"APE-DE has a mean rank of {ranks['APE']:.3f} in the six-method confirmation comparison, against {ranks['DE']:.3f} for DE and {ranks['TEAM']:.3f} for PGE-DE. Relative to DE, the primary corrected tests identify {a['wins']} wins and {a['losses']} losses; relative to PGE-DE they identify {b['wins']} wins and {b['losses']} losses. Figure 6 shows every function-level comparison, including the unfavorable outcomes. Mean rank describes this complete benchmark and does not by itself establish a pairwise superiority claim.")
    j.figure('revision_performance','Figure 0. Independent performance on CEC2014 10D. (a) Descriptive mean ranks of the six full algorithms, based on 20 independent runs per function. (b) Paired rank-biserial effects of APE-DE relative to every control across all 30 functions; positive values favour APE-DE. Dots identify Holm-corrected significance within the prespecified primary or paper-control family. No function is omitted.')
    rows=[]
    for algo in MAIN:
        if algo=='APE':rows.append([DISPLAY[algo],f'{ranks[algo]:.3f}','—','—','—','—'])
        else:
            c=counts[algo];rows.append([DISPLAY[algo],f'{ranks[algo]:.3f}',c['wins'],c['not_detected'],c['losses'],c['family']])
    j.new_table('Table 25. Confirmation ranks and APE-DE versus each full-method control. W/ND/L counts are functions, not independent replicate counts.',
                ['Algorithm','Mean rank','APE wins','ND','APE losses','Test family'],rows)
    j.section(2)
    subset={r['algorithm']:r['mean_rank'] for r in summary['f01_f16_mean_ranks']}
    j.p(f"The F01–F16 evaluator-agreement subset gives mean ranks of {subset['APE']:.3f} for APE-DE, {subset['DE']:.3f} for DE and {subset['TEAM']:.3f} for PGE-DE. This sensitivity summary separates the previously identified evaluator-disagreement group; it does not replace the required 30-function benchmark or add a new confirmatory test. The saved objectives retain the unmodified coursework evaluator.")
    j.figure('revision_distributions','Figure 0. Individual confirmation outcomes on the previously selected F11 and F29 diagnostic functions. All 20 paired seeds are shown for DE, PGE-DE and APE-DE, with grey lines linking matching seeds. Hollow coloured markers show observed final absolute errors; values below 10⁻⁸ share that display floor. The two functions were selected by the preceding diagnostics before confirmation; the complete function profile remains in Figure 6 and the numerical tables.')
    j.h('6.3 Contribution of the selected strategy groups',2)
    p,c=counts['APE_no_potential'],counts['APE_no_control']
    j.p(f"Removing stochastic potential guidance gives {p['wins']} full-method wins and {p['losses']} full-method losses after ablation-family correction. Removing parameter control gives {c['wins']} wins and {c['losses']} losses. The removals preserve the remaining archive-backed backbone and evaluation budget. These comparisons support only the contributions detected under this protocol; a nonsignificant removal does not prove a mechanism necessary or redundant.")
    j.figure('revision_ablation','Figure 0. Independent revision-family controls. (a) Descriptive mean ranks of full APE-DE and its two removals, computed within this three-method family. These ranks are distinct from the six-method ranks in Figure 6. (b) Counts of full-method wins, undetected differences and losses after Holm correction over the 60 ablation comparisons. Every cell is based on 20 paired observations.')
    rows=[]
    ar={r['algorithm']:r['mean_rank'] for r in summary['ablation_mean_ranks']}
    for algo in ABLATION:
        c=counts.get(algo);rows.append([DISPLAY[algo],f'{ar[algo]:.3f}']+([c['wins'],c['not_detected'],c['losses']] if c else ['—']*3))
    j.new_table('Table 26. Full-versus-removal confirmation summary within the APE-DE family.',
                ['Method','Mean rank','Full wins','ND','Full losses'],rows)
    j.h('6.4 Complete confirmation statistics',2)
    j.p('The following tables retain every final-method and ablation observation through complete per-function summaries. Best, Mean, sample Std and sample Variance use all 20 independent runs. Rank is assigned from mean error within the specified comparison family, with the numerical tie rule retained. Exact values, source hashes and individual seeds accompany the report.')
    stats=read('validation_statistics.csv');abl=read('validation_ablation_statistics.csv')
    table_no=27
    for first in range(1,31,5):
        group=[r for r in stats if first<=int(r['function'])<=first+4]
        rows=[[f"F{int(r['function']):02d}",DISPLAY[r['algorithm']]]+[number(r[k]) for k in ['best','mean','std','variance']]+[f"{float(r['rank']):.1f}"] for r in group]
        j.new_table(f'Table {table_no}. Independent six-method statistics, F{first:02d}–F{first+4:02d}. Lower error and rank are better.',
                    ['F','Algorithm','Best','Mean','Std','Variance','Rank'],rows);table_no+=1
    for first in range(1,31,10):
        group=[r for r in abl if first<=int(r['function'])<=first+9]
        short={'APE':'APE-DE','APE_no_potential':'Without potential','APE_no_control':'Without control'}
        rows=[[f"F{int(r['function']):02d}",short[r['algorithm']]]+[number(r[k]) for k in ['best','mean','std','variance']]+[f"{float(r['rank']):.1f}"] for r in group]
        j.new_table(f'Table {table_no}. Independent APE-DE ablation statistics, F{first:02d}–F{first+9:02d}. Ranks apply to this three-method family.',
                    ['F','Algorithm','Best','Mean','Std','Variance','Rank'],rows);table_no+=1
    assert table_no==36
    j.h('6.5 Best-run convergence across all thirty functions',2)
    j.p('Each method and function contributes the complete recorded history of its lowest-final-objective confirmation run, with run ID as the tie-break. The vertical axis is the original best-so-far objective, as required by the course; the horizontal axis is actual function evaluations. Best-run curves describe favorable trajectories and are interpreted together with all-run summaries rather than as evidence of typical performance.')
    for first in range(1,31,6):
        j.figure(f'revision_curves_{first:02d}_{first+5:02d}',f'Figure 0. Independent best-run convergence on F{first:02d}–F{first+5:02d}. Six methods, 20 confirmation runs per method and function; the lowest-final-objective run is shown with every logged checkpoint. CEC2014 10D, fixed NP 100, exactly 100,000 FEs. Curves use previous-observation steps on logarithmic objective axes, without smoothing or cross-run splicing. Green triangles identify APE-DE.')
    j.section(2)


def remap_text(s):
    if 'Table 7 dimension remains unresolved' in s:return s
    s=re.sub(r'\bTable (\d+)\b',lambda m:'Table '+str(int(m[1])+(1 if int(m[1])>=4 else 0)+(11 if int(m[1])>=24 else 0)),s)
    if s.startswith('6 '):s=s.replace('6 Comparative performance','7 Historical comparison of the predecessor',1)
    elif re.match(r'^6\.',s):s='7'+s[1:]
    elif s.startswith('7 '):s=s.replace('7 Mechanistic interpretation','8 Historical mechanistic interpretation',1)
    elif s.startswith('8 '):s='9'+s[1:]
    if 'all 30 functions in Section 6.4' in s:
        s='The historical seed distributions describe the preceding sample. Independent best-run curves for all 30 functions appear in Section 6.5; the historical curve records remain in the submission archive.'
    return s


def main():
    summary=json.loads((ANALYSIS/'validation_summary.json').read_text())
    verification=json.loads((ROOT/'improvement/results/validation/verification.json').read_text())
    assert verification['passed'] and verification['records']==4800
    j=Revision();ranks={r['algorithm']:r['mean_rank'] for r in summary['mean_ranks']}
    counts={r['comparison']:r for r in summary['comparisons']};de=counts['DE'];old=counts['TEAM']
    j.p('Improving strategy transfer in differential evolution','Journal Title')
    j.p('Source reconstructions and independent validation of APE-DE','Journal Note')
    j.p('Abstract','Journal Heading 2')
    j.p(f"Strategy combination in differential evolution requires evidence that transferred modules improve the receiving algorithm. We reproduce DSPDE, DLS-DE and PEMS-DE, retain their source controls and evaluate the original PGE-DE combination. Development ablations motivate APE-DE, which replaces a shared potential guide with independently sampled potential/elite members and adds success-history F/CR control to an archive-backed search. The frozen revision is tested in 4,800 independent CEC2014 runs covering six full methods and two revision controls. Across 30 ten-dimensional functions, APE-DE has mean rank {ranks['APE']:.3f}, compared with {ranks['DE']:.3f} for basic DE and {ranks['TEAM']:.3f} for the predecessor. Corrected paired tests identify {de['wins']} wins and {de['losses']} losses against DE, and {old['wins']} wins and {old['losses']} losses against PGE-DE. Complete source reproduction, ablation and confirmation statistics distinguish supported gains from remaining losses and evaluator-sensitive outcomes.")
    j.p('Keywords: Differential evolution; strategy transfer; potential and elite guidance; independent validation; CEC2014','Journal Note')
    with zipfile.ZipFile(BASE) as z:nodes=list(etree.fromstring(z.read('word/document.xml')).find(qn('w:body')))
    started=False;figure_index=0;skip_caption=False;skip_curves=False;skip_conclusion=False
    for i,node in enumerate(nodes):
        s=visible(node)
        if not started:
            if s!='1 Introduction':continue
            started=True
        image=bool(node.findall('.//a:blip',NS))
        if image:
            name=FIGURES[figure_index];figure_index+=1;skip_caption=True
            caption=next(visible(n) for n in nodes[i+1:] if visible(n).startswith('Figure '))
            if not skip_curves:j.figure(name,caption)
            continue
        if skip_caption and s.startswith('Figure '):skip_caption=False;continue
        if s=='3 Original-condition reproduction':method(j)
        if s=='6 Comparative performance':confirmation(j,summary)
        if s.startswith('6.4 Convergence'):skip_curves=True;continue
        if s=='7 Mechanistic interpretation':skip_curves=False
        if skip_curves:continue
        if s=='8 Conclusions':
            j.h('9 Conclusions');skip_conclusion=True
            j.p(f"The independent experiment gives APE-DE a mean rank of {ranks['APE']:.3f}, with {de['wins']}/{de['not_detected']}/{de['losses']} corrected wins/undetected differences/losses against basic DE and {old['wins']}/{old['not_detected']}/{old['losses']} against PGE-DE. These results quantify the revision against both a basic control and its predecessor; they do not establish universal dominance over the three paper algorithms.")
            j.p('The revision follows the development evidence: stochastic guides replace a common centroid, success-history control adapts F and CR, and archive-backed differences and midpoint repair support the search. Independent removals separate the detected contributions of the two selected strategy groups. The complete retained source controls explain why mechanisms effective in their original backbone need not transfer unchanged.')
            j.p('The evaluator audit remains essential to interpreting literature discrepancies. The original records and the independent sample use the unchanged coursework objective; 13 functions differ in the separate source audit. Complete results, saved solutions, code hashes and best-run histories bound the conclusions to the measured setting.')
            continue
        if s=='References':skip_conclusion=False
        if skip_conclusion:continue
        if node.tag==qn('w:tbl'):j.table(node);continue
        if node.tag!=qn('w:p'):continue
        if not s:
            if node.findall('.//m:oMath',NS):j.clone_p(node)
            continue
        s=remap_text(s)
        if re.match(r'^\d+(?:\.\d+)? ',s) or s in ['Guide and memory definitions','Function families','References']:
            if s=='2.2 Three strategy interfaces':s='2.2 Predecessor strategy interfaces'
            if s=='2.3 Executable procedure':s='2.3 Predecessor executable procedure'
            j.section(2);j.heading(node,s)
        elif re.match(r'^Table \d+\.',s):j.p(s,'Journal Caption',keep=True)
        else:
            j.clone_p(node,'Journal Note' if len(s)<600 and (s.startswith('CEC2014,') or s.startswith('CEC2022,') or s.startswith('Native DLS-DE')) else 'Journal Body',s)
    assert figure_index==12 and len(j.figures)==16
    j.save()
    target=ROOT/'output/improvement_content_manifest.json'
    target.write_text(json.dumps(dict(author='殷明骏',independent_records=4800,development_records=450,
                    full_methods=6,revision_ablations=2,original_numerical_rows=810,
                    added_numerical_rows=270,confirmation_curve_functions=30,
                    confirmation_selected_runs=180,figure_sheets=j.figures,
                    original_report_preserved=str(BASE.relative_to(ROOT.parent)),
                    original_cover_preserved=True),ensure_ascii=False,indent=2)+'\n')
    print('Confirmation integrated into retained Word report')


if __name__=='__main__':main()
