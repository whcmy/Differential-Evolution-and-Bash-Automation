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
from plot_confirmation import MAIN, ABLATION, DISPLAY
BASE=ROOT.parent/'backups/2026-11-16_before_report2_algorithm_improvement/project2_final/output/Project2_Report.docx'
ANALYSIS=ROOT/'improvement_v2/analysis'
FIGURES=json.loads((ROOT/'improvement_v2/baseline_report_figures.json').read_text())
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

    def section(self,cols,first=False):
        # Single-column body avoids balancing pages around wide evidence.
        super().section(1,first=first)

    def save(self):
        super().save()
        for name in ['template_fidelity.json','journal_body_manifest.json']:
            path=ROOT/'output'/name
            value=json.loads(path.read_text());value['body_columns']=1
            if 'intentional_changes' in value:
                value['intentional_changes']=['Only the first page is locked','Single-column body selected after rendered comparison','Full-width figures and tables','Black ruled numerical tables','No contents page or appendices']
            path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

    def h(self,text,level=1):
        self.section(2)
        p=self.p(text,f'Journal Heading {level}',keep=True)
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
        if len(headers)==2:
            for col,width in zip(table.columns,[WIDTH*.28,WIDTH*.72]):col.width=Inches(width)
        if len(headers)==7 and headers[:2]==['F','Algorithm']:
            widths=[.4,1.45]+[(WIDTH-1.85)/5]*5
            for col,width in zip(table.columns,widths):col.width=Inches(width)
        if len(headers)==7 and headers[:2]==['F','Algorithm']:
            best_rank={fid:min(float(row[-1]) for row in rows if row[0]==fid) for fid in {row[0] for row in rows}}
            for row,values in zip(table.rows[1:],rows):
                if float(values[-1])==best_rank[values[0]]:
                    for index in [3,6]:
                        for run in row.cells[index].paragraphs[0].runs:run.bold=True
        borders=OxmlElement('w:tblBorders')
        for edge in ['top','bottom','left','right','insideH','insideV']:
            e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single' if edge in ['top','bottom'] else 'nil');e.set(qn('w:sz'),'5');e.set(qn('w:color'),'222222');borders.append(e)
        table._tbl.tblPr.append(borders)
        self.table(table._tbl)
        for i,row in enumerate(self.doc.tables[-1].rows):
            row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
            if len(rows)<=12:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        paragraph.paragraph_format.keep_with_next=i<len(rows)

    def equation(self,text):
        self.section(1)
        p=self.doc.add_paragraph();p.style=self.doc.styles['Journal Body']
        omp=OxmlElement('m:oMathPara');om=OxmlElement('m:oMath')
        def math_run(parent,value):
            run=OxmlElement('m:r');t=OxmlElement('m:t');t.text=value;run.append(t);parent.append(run)
        offset=0
        for token in re.finditer(r'([A-Za-zπ])_([A-Za-z0-9]+)',text):
            math_run(om,text[offset:token.start()])
            sub=OxmlElement('m:sSub');base=OxmlElement('m:e');index=OxmlElement('m:sub')
            math_run(base,token[1]);math_run(index,token[2]);sub.append(base);sub.append(index);om.append(sub)
            offset=token.end()
        math_run(om,text[offset:]);omp.append(om);p._p.append(omp)
        self.md.append(text)


from report_text import method,abstract,conclusions


def confirmation(j,summary):
    ranks={r['algorithm']:r['mean_rank'] for r in summary['mean_ranks']}
    counts={r['comparison']:r for r in summary['comparisons']}
    j.h('6 Independent validation of DC-DE')
    j.h('6.1 Frozen design and independent observations',2)
    j.p('The selected implementation was frozen before the independent sample began. Master seed 20261118 generated 20 paired runs on each CEC2014 function for DE, DSPDE, fixed-NP DLS-DE, PEMS-DE, the original PGE-DE and DC-DE. Two additional DC-DE removals were also run with the same seeds. All eight distinct methods used dimension 10, NP 100 and exactly 100,000 objective evaluations including initialization. The independent experiment therefore contains 4,800 runs; none of the 750 development runs is counted in this sample. The DLS-DE baseline also supplies the no-crossover-mixture control, using the same records and canonical primary comparison.')
    j.p('The source hashes, full method list, seed derivation and statistical families were recorded before confirmation outcomes were inspected. The primary family contains 90 DC-DE comparisons against DE, DLS-DE and PGE-DE across 30 functions. The other-paper family contains 60 comparisons against DSPDE and PEMS-DE; the additional-removal family contains 60 comparisons against the two phase/direction controls. Each family uses two-sided paired Wilcoxon tests and Holm correction at 0.05, retaining the numerical tie rule in Section 1.2. A nonsignificant result is labelled not detected and is not treated as equivalence.')
    j.p('The preceding APE-DE confirmation used a separate master seed (20261117) and 4,800 runs. APE-DE ranked second among six full methods (mean rank 2.917), behind DLS-DE (2.450). Its complete records remain archived separately. That experiment finished after the DC-DE design was frozen; it contributes no observations to the following confirmation tables.')
    j.h('6.2 Performance relative to the predecessor and controls',2)
    a,b=counts['DE'],counts['TEAM']
    j.p(f"DC-DE has a mean rank of {ranks['DUAL']:.3f} in the six-method confirmation comparison, against {ranks['DE']:.3f} for DE and {ranks['TEAM']:.3f} for PGE-DE. Relative to DE, the primary corrected tests identify {a['wins']} wins and {a['losses']} losses; relative to PGE-DE they identify {b['wins']} wins and {b['losses']} losses. Figure 6 combines the mean ranks with paired function-level effects.")
    j.figure('revision_performance','Figure 0. Independent performance on CEC2014 10D. (a) Descriptive mean ranks of the six full algorithms, based on 20 independent runs per function. (b) Paired rank-biserial effects of DC-DE relative to every control across all 30 functions; positive values favour DC-DE. Dots identify Holm-corrected significance within the prespecified primary or paper-control family.')
    rows=[]
    for algo in MAIN:
        if algo=='DUAL':rows.append([DISPLAY[algo],f'{ranks[algo]:.3f}','—','—','—','—'])
        else:
            c=counts[algo];rows.append([DISPLAY[algo],f'{ranks[algo]:.3f}',c['wins'],c['not_detected'],c['losses'],c['family']])
    j.new_table('Table 25. Confirmation ranks and DC-DE versus each full-method control. W/ND/L counts are functions, not independent replicate counts.',
                ['Algorithm','Mean rank','DC wins','ND','DC losses','Test family'],rows)
    j.section(2)
    subset={r['algorithm']:r['mean_rank'] for r in summary['f01_f16_mean_ranks']}
    j.p(f"The F01–F16 probe-agreement subset gives mean ranks of {subset['DUAL']:.3f} for DC-DE, {subset['DE']:.3f} for DE and {subset['TEAM']:.3f} for PGE-DE. This probe-agreement sensitivity summary uses the unchanged coursework evaluator; the primary benchmark remains F01–F30.")
    j.figure('revision_distributions','Figure 0. Individual confirmation outcomes on the previously selected F11 and F29 diagnostic functions. All 20 paired seeds are shown for DE, PGE-DE and DC-DE, with grey lines linking matching seeds; small horizontal offsets separate seeds. Hollow coloured markers show observed final objective errors; values below 10⁻⁸ share that display floor. The two functions were selected by the preceding diagnostics before confirmation; the complete function profile remains in Figure 6 and the numerical tables.')
    j.h('6.3 Contribution of the selected strategy groups',2)
    p,c=counts['DUAL_no_phase'],counts['DUAL_no_learning']
    j.p(f"Removing two-phase F control gives {p['wins']} full-method wins and {p['losses']} full-method losses after ablation-family correction. Removing direction learning gives {c['wins']} wins and {c['losses']} losses. The removals preserve the remaining archive-backed backbone and evaluation budget.")
    j.p('The crossover-mixture addition has two corrected wins and no losses against its DLS-DE control. Neither phase nor direction removal yields a detected difference on any function. Within the four-method ablation ranking, removing direction learning has mean rank 2.017, compared with 2.217 for the full design. The component experiment supports the added crossover interface most directly.')
    j.figure('revision_ablation','Figure 0. Independent revision-family controls. (a) Descriptive mean ranks of DC-DE, its no-added-strategy DLS-DE baseline and two additional removals, computed within this four-method family. These ranks are distinct from the six-method ranks in Figure 6. (b) Counts of full-method wins, undetected differences and losses. The no-added-strategy DLS-DE contrast uses its canonical 90-test primary family; phase/direction removals use their 60-test family. Every cell is based on 20 paired observations.')
    rows=[]
    ar={r['algorithm']:r['mean_rank'] for r in summary['ablation_mean_ranks']}
    for algo in ABLATION:
        c=counts.get(algo);rows.append([DISPLAY[algo],f'{ar[algo]:.3f}']+([c['wins'],c['not_detected'],c['losses']] if c else ['—']*3))
    j.new_table('Table 26. Full-versus-removal confirmation summary within the four-method DC-DE family.',
                ['Method','Mean rank','Full wins','ND','Full losses'],rows)
    j.h('6.4 Complete confirmation statistics',2)
    j.p('The following tables summarize every final-method and ablation run by function. Objective error is max(0, f − f*), with clipping limited to numerical undershoot; the unchanged evaluator and optimum define f and f*, respectively. Best, Mean, sample Std and sample Variance use all 20 independent runs. Bold Mean/Rank cells mark the lowest mean-error group within each function. Rank is assigned from mean error within the specified comparison family, with the numerical tie rule retained. Exact values, source hashes and individual seeds accompany the report.')
    stats=read('confirmation_statistics.csv');abl=read('confirmation_ablation_statistics.csv')
    table_no=27
    for first in range(1,31,5):
        group=[r for r in stats if first<=int(r['function'])<=first+4]
        rows=[[f"F{int(r['function']):02d}",DISPLAY[r['algorithm']]]+[number(r[k]) for k in ['best','mean','std','variance']]+[f"{float(r['rank']):.1f}"] for r in group]
        j.new_table(f'Table {table_no}. Independent six-method statistics, F{first:02d}–F{first+4:02d}. Lower error and rank are better.',
                    ['F','Algorithm','Best','Mean','Std','Variance','Rank'],rows);table_no+=1
    for first in range(1,31,10):
        group=[r for r in abl if first<=int(r['function'])<=first+9]
        short={'DUAL':'DC-DE','DUAL_no_phase':'Without two-phase','DUAL_no_learning':'Without learning','DLSDE':'Without crossover'}
        rows=[[f"F{int(r['function']):02d}",short[r['algorithm']]]+[number(r[k]) for k in ['best','mean','std','variance']]+[f"{float(r['rank']):.1f}"] for r in group]
        j.new_table(f'Table {table_no}. Independent DC-DE ablation statistics, F{first:02d}–F{first+9:02d}. Ranks apply to this four-method family.',
                    ['F','Algorithm','Best','Mean','Std','Variance','Rank'],rows);table_no+=1
    assert table_no==36
    j.h('6.5 Best-run convergence across all thirty functions',2)
    j.p('Each method and function contributes the complete recorded history of its lowest-final-objective confirmation run, with run ID as the tie-break. The vertical axis is the original best-so-far objective, as required by the course; the horizontal axis is actual function evaluations. Best-run curves describe favorable trajectories and are interpreted together with all-run summaries rather than as evidence of typical performance.')
    for first in range(1,31,6):
        j.figure(f'revision_curves_{first:02d}_{first+5:02d}',f'Figure 0. Independent best-run convergence on F{first:02d}–F{first+5:02d}. Six methods, 20 confirmation runs per method and function; the lowest-final-objective run is shown with every logged checkpoint. CEC2014 10D, fixed NP 100, exactly 100,000 FEs. Curves use previous-observation steps on logarithmic objective axes, without smoothing or cross-run splicing. Green triangles identify DC-DE.')
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
    summary=json.loads((ANALYSIS/'confirmation_summary.json').read_text())
    verification=json.loads((ROOT/'improvement_v2/results/confirmation/verification.json').read_text())
    assert verification['passed'] and verification['records']==4800
    assert summary['first_descriptive_rank']
    j=Revision();ranks={r['algorithm']:r['mean_rank'] for r in summary['mean_ranks']}
    counts={r['comparison']:r for r in summary['comparisons']};de=counts['DE'];old=counts['TEAM']
    j.p('Dual crossover in differential evolution','Journal Title')
    j.p('Source reconstructions and independent validation of DC-DE','Journal Note')
    j.p('Abstract','Journal Heading 2',keep=True)
    j.p(abstract(summary,ranks,counts))
    j.p('Keywords: Differential evolution; strategy transfer; adaptive crossover; independent validation; CEC2014','Journal Note')
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
            conclusions(j,summary,ranks,counts)
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
    from compact_tables import apply
    apply(j)
    j.save()
    target=ROOT/'output/improvement_content_manifest.json'
    target.write_text(json.dumps(dict(author='殷明骏',independent_records=4800,development_records=750,
                    full_methods=6,revision_ablations=3,original_numerical_rows=810,
                    added_numerical_rows=300,confirmation_curve_functions=30,
                    confirmation_selected_runs=180,figure_sheets=j.figures,
                    original_report_preserved=str(BASE.relative_to(ROOT.parent)),
                    original_cover_preserved=True),ensure_ascii=False,indent=2)+'\n')
    print('Confirmation integrated into retained Word report')


if __name__=='__main__':main()
