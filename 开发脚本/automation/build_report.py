"""Rebuild the Automation body in the reference paper styles. Author: 殷明骏."""
from pathlib import Path
from copy import deepcopy
import csv,hashlib,json,math,re,statistics,zipfile
from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Mm,Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from lxml import etree
from clean_metadata import clean_docx
import report_components as c
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output';WIDTH=174/25.4

def text(n):return ''.join(t.text or '' for t in n.iter(qn('w:t')))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class Paper:
    def __init__(self):
        self.doc=Document(ROOT/'source/DCDE_Study_reference.docx');body=self.doc._element.body
        self.cover=etree.fromstring((ROOT/'source/cover_preserved.xml').read_bytes())
        for node in self.cover.iter(qn('w:t')):
            if node.text: node.text=node.text.replace('2026-11-10','2026-11-16')
        # Replace only the former overview block with the confirmed contributions.
        list(self.cover[15].iter(qn('w:t')))[0].text='Author contributions'
        contribution=self.cover[16]
        list(contribution.iter(qn('w:t')))[0].text='Mingjun Yin (殷明骏) completed the experiments and wrote the experimental report.'
        second=deepcopy(contribution)
        list(second.iter(qn('w:t')))[0].text='Hongrui Ding (丁鸿睿) improved the report’s layout and visual presentation.'
        self.cover.append(second)
        for n in list(body):
            if n.tag!=qn('w:sectPr'):body.remove(n)
        for i,n in enumerate(self.cover):body.insert(i,deepcopy(n))
        self.cols=0;self.titles=[];self.figures=[];self.md=['# Optimization Research','Author: 殷明骏','## Author contributions',text(contribution),text(second)];self.figure_no=0
        for name,size,bold in [('Paper Body',11,False),('Paper Note',9,False),('Paper Caption',9,False),('Paper Heading 1',12,True),('Paper Heading 2',11,False),('Paper Title',16,True),('Paper Code',8,False)]:
            s=self.doc.styles[name] if name in self.doc.styles else self.doc.styles.add_style(name,1)
            s.font.name='DejaVu Sans Mono' if name=='Paper Code' else 'Times New Roman';s.font.size=Pt(size);s.font.bold=bold;s.font.color.rgb=RGBColor(0,0,0)
            pf=s.paragraph_format;pf.first_line_indent=Pt(0);pf.left_indent=Pt(0);pf.right_indent=Pt(0);pf.line_spacing=1.12;pf.space_before=Pt(0);pf.space_after=Pt(4);pf.widow_control=True;pf.keep_together=False
            snap=OxmlElement('w:snapToGrid');snap.set(qn('w:val'),'0');s._element.get_or_add_pPr().append(snap)
            if 'Heading' in name:pf.keep_with_next=True;pf.space_before=Pt(9);pf.space_after=Pt(4)
            if name=='Paper Heading 2':s.font.italic=True
            if name=='Paper Code':pf.line_spacing=1.05;pf.space_after=Pt(1)
        self.section(1,first=True)
        sec=self.doc.sections[-1];sec.header.is_linked_to_previous=False;sec.footer.is_linked_to_previous=False
        for p in sec.header.paragraphs:
            p.clear();p.style=self.doc.styles['Paper Note'];p.alignment=WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.tab_stops.add_tab_stop(Mm(174),__import__('docx').enum.text.WD_TAB_ALIGNMENT.RIGHT)
            for n in list(p._p.get_or_add_pPr().findall(qn('w:pBdr'))):p._p.get_or_add_pPr().remove(n)
            r=p.add_run('Optimization Research\tOptimization experiment automation');r.font.name='Times New Roman';r.font.size=Pt(7.5);r.italic=True
        for p in sec.footer.paragraphs:
            p.clear();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            f=OxmlElement('w:fldSimple');f.set(qn('w:instr'),'PAGE');p._p.append(f)
    def section(self,cols,first=False):
        cols=1
        if self.cols==cols:return
        sec=self.doc.add_section(WD_SECTION_START.NEW_PAGE if first else WD_SECTION_START.CONTINUOUS)
        sec.page_width=Mm(210);sec.page_height=Mm(297);sec.left_margin=sec.right_margin=Mm(18);sec.top_margin=sec.bottom_margin=Mm(18);sec.header_distance=sec.footer_distance=Mm(8);sec.different_first_page_header_footer=False
        col=sec._sectPr.find(qn('w:cols'));col.attrib.clear();col.set(qn('w:num'),str(cols));col.set(qn('w:space'),'340');col.set(qn('w:equalWidth'),'1')
        for n in list(col):col.remove(n)
        for n in list(sec._sectPr.findall(qn('w:docGrid'))):sec._sectPr.remove(n)
        self.cols=cols
    def p(self,s,style='Paper Body',keep=False):
        p=self.doc.add_paragraph(s,style);p.paragraph_format.keep_with_next=keep
        if style=='Paper Body':p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
        self.md.append(s);return p
    def h(self,s,level=1,page=False):
        p=self.p(s,f'Paper Heading {level}',True);p.paragraph_format.page_break_before=page
        aid=700+len(self.titles);a=OxmlElement('w:bookmarkStart');a.set(qn('w:id'),str(aid));a.set(qn('w:name'),f'paper_{aid}');b=OxmlElement('w:bookmarkEnd');b.set(qn('w:id'),str(aid));p._p.insert(0,a);p._p.append(b)
        self.titles.append(dict(title=s,level=level,anchor=f'paper_{aid}'));return p
    def caption(self,s):
        p=self.p(s,'Paper Caption');p.clear();first,rest=s.split('.',1);p.add_run(first+'.').bold=True;p.add_run(('\n'+rest.strip()) if s.startswith('Table ') else rest);return p
    def fig(self,name,caption,page=False):
        self.section(1);self.figure_no+=1
        p=self.doc.add_paragraph(style='Paper Note');p.paragraph_format.space_before=Pt(5);p.paragraph_format.space_after=Pt(3);p.paragraph_format.keep_with_next=True
        p.paragraph_format.page_break_before=page
        p.add_run().add_picture(str(OUT/'figures'/f'{name}.png'),width=Inches(WIDTH))
        self.caption(f'Figure {self.figure_no}. '+caption);self.figures.append(name);self.md.append(f'![Figure {self.figure_no}](figures/{name}.png)')
    def table(self,headers,rows,ratios,caption,size=8.5,bold_cells=None):
        self.section(1);self.caption(caption).paragraph_format.keep_with_next=True
        t=self.doc.add_table(rows=1,cols=len(headers));t.autofit=False
        for col,v in zip(t.columns,ratios):col.width=Inches(WIDTH*v)
        pr=t._tbl.tblPr
        old=pr.find(qn('w:tblBorders'))
        if old is not None:pr.remove(old)
        borders=OxmlElement('w:tblBorders')
        for edge in ['top','bottom','left','right','insideH','insideV']:
            n=OxmlElement('w:'+edge);n.set(qn('w:val'),'single' if edge in ['top','bottom'] else 'nil');n.set(qn('w:sz'),'5');n.set(qn('w:color'),'222222');borders.append(n)
        pr.append(borders);mar=OxmlElement('w:tblCellMar')
        for edge,val in [('top',32),('bottom',32),('left',45),('right',45)]:
            n=OxmlElement('w:'+edge);n.set(qn('w:w'),str(val));n.set(qn('w:type'),'dxa');mar.append(n)
        pr.append(mar)
        for i,row in enumerate([headers]+rows):
            cells=t.rows[0].cells if i==0 else t.add_row().cells
            tr=t.rows[i]._tr.get_or_add_trPr();tr.append(OxmlElement('w:cantSplit'))
            if i==0:tr.append(OxmlElement('w:tblHeader'))
            for j,(cell,value,ratio) in enumerate(zip(cells,row,ratios)):
                cell.width=Inches(WIDTH*ratio);p=cell.paragraphs[0];p.paragraph_format.line_spacing=1;p.paragraph_format.space_before=Pt(0);p.paragraph_format.space_after=Pt(0);p.paragraph_format.keep_with_next=(i==0);p.paragraph_format.widow_control=True
                p.alignment=WD_ALIGN_PARAGRAPH.LEFT if j==0 or len(headers)==2 else WD_ALIGN_PARAGRAPH.RIGHT
                snap=OxmlElement('w:snapToGrid');snap.set(qn('w:val'),'0');p._p.get_or_add_pPr().append(snap)
                if len(rows)<=30:p.paragraph_format.keep_with_next=i<len(rows)
                r=p.add_run(str(value));r.font.name='Times New Roman';r.font.size=Pt(size);r.bold=(i==0 or (bold_cells is not None and (i-1,j) in bold_cells));r.font.color.rgb=RGBColor(0,0,0)
                if i==0:
                    b=OxmlElement('w:tcBorders');n=OxmlElement('w:bottom');n.set(qn('w:val'),'single');n.set(qn('w:sz'),'3');n.set(qn('w:color'),'222222');b.append(n);cell._tc.get_or_add_tcPr().append(b)
        self.md.extend(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |',*['| '+' | '.join(map(str,row))+' |' for row in rows]])
        return t
    def code(self,title,s):
        self.section(1);self.caption(title).paragraph_format.keep_with_next=True
        lines=s.splitlines()
        for i,line in enumerate(lines):
            p=self.p(line,'Paper Code',i<len(lines)-1)
            p.paragraph_format.keep_together=True
    def equation(self):
        p=self.doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.LEFT;p.paragraph_format.space_after=Pt(5)
        from docx.enum.text import WD_TAB_ALIGNMENT
        p.paragraph_format.tab_stops.add_tab_stop(Mm(87),WD_TAB_ALIGNMENT.CENTER)
        p.paragraph_format.tab_stops.add_tab_stop(Mm(174),WD_TAB_ALIGNMENT.RIGHT)
        p.add_run('\t')
        m=etree.Element('{'+c.M+'}oMath')
        for piece in [c.mr('S = '),c.frac('1','30'),c.sub_sup('∑','j = 1','30'),c.mr('|'),c.sub('f','j'),c.mr('('),c.sub('x','j,best'),c.mr(') − '),c.sub_sup('f','j','*'),c.mr('|')]:m.append(piece)
        p._p.append(m);p.add_run('\t(1)');self.md.append('S = (1/30) Σⱼ |fⱼ(xⱼ,best) − fⱼ*|')
    def screenshot(self,name,caption,width=110,page=False):
        p=self.doc.add_paragraph(style='Paper Note');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_before=Pt(1);p.paragraph_format.space_after=Pt(2);p.paragraph_format.keep_with_next=True;p.paragraph_format.page_break_before=page
        p.add_run().add_picture(str(ROOT/'rerun_20261116/evidence/screenshots'/f'{name}.png'),width=Mm(width))
        self.caption(caption)
    def save(self):
        cp=self.doc.core_properties;cp.author=cp.last_modified_by='殷明骏';cp.title='Automation Bash Automation and Experiment Analysis';cp.subject=cp.keywords=cp.comments=''
        self.doc.save(OUT/'Automation_Study.docx');clean_docx(OUT/'Automation_Study.docx')
        with zipfile.ZipFile(OUT/'Automation_Study.docx') as z:
            nodes=list(etree.fromstring(z.read('word/document.xml')).find(qn('w:body')))
            canon=lambda n:etree.tostring(n,method='c14n',exclusive=True)
            assert [canon(n) for n in nodes[:len(self.cover)]]==[canon(n) for n in self.cover]
        for filename,value in [('report_figures.json',self.figures),('report_sections.json',self.titles),('report_contents.json',[])]:
            (OUT/filename).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
        (OUT/'Automation_Study.md').write_text('\n\n'.join(self.md)+'\n')
        (OUT/'template_fidelity.json').write_text(json.dumps(dict(author='殷明骏',cover_identity_fields_unchanged=True,cover_experiment_date="2026-11-16",cover_overview_replaced_with_contributions=True,body_columns=1,body_margin_mm=18,body_rebuild_user_authorized=True),ensure_ascii=False,indent=2)+'\n')

def main():
    data=json.loads((OUT/'analysis/results.json').read_text());assert data['complete'] and data['record_count']==270
    with (OUT/'analysis/records.csv').open() as f:records=list(csv.DictReader(f))
    p=Paper();p.p('Bash automation and experiment analysis','Paper Title')
    p.p('A verified population-size sweep of DC-DE on CEC2014','Paper Note')
    p.h('Abstract')
    p.p('This experiment implements a Bash pipeline for repeated optimization, structured result extraction and scheduled execution around the final DC-DE application from AdaptiveDE. Population sizes of 50, 100 and 150 are evaluated on all 30 CEC2014 functions in ten dimensions, with 100,000 objective evaluations per function. Three system-cron executions yield 270 independently validated solutions and nine suite scores. Population 100 gives the lowest three-seed suite mean, whereas population 50 achieves the lowest mean error on the largest number of functions when ties are counted. F29 accounts for more than 99% of pooled absolute error for every population, explaining the difference between these two summaries. Saved solutions, exact log tokens and execution receipts link every reported score to its parameters and source records.')
    p.p('Keywords: Bash; differential evolution; structured logging; cron; reproducible experiments','Paper Note')
    p.section(2);p.h('1 Introduction')
    p.p('Repeated optimization requires consistent parameter settings, comparable summaries and an execution record that can be checked after the run. Automation connects these tasks through a Bash wrapper around the DC-DE optimizer from the final AdaptiveDE implementation [1,2]. The experiment varies population size through the existing command-line interface and retains the full numerical evidence for each invocation.')
    p.p('The workflow combines a parameterized for loop, append-only batch logs, grep/awk score extraction and system-cron launches. Validation recomputes saved solutions before a batch is marked successful. Figure 1 shows the path from a scheduled launch to the verified summary.')
    p.fig('00_automation_workflow','Automation and validation sequence. Each cron execution runs three population settings on F01–F30. Independent solution checks and exact-token summary checks precede the success marker. Arrows describe program flow, without representing measured time.')
    p.section(2);p.h('2 Experimental design')
    p.p('All configurations use the same ten-dimensional benchmark, search bounds and objective-evaluation budget (Table 1). Population size remains fixed within each run. DC-DE retains its DLS-based parameter memory, direction learning and adaptive exponential/binomial crossover. The optimizer is copied unchanged; the copied runner adds a population-size option for this sweep.')
    p.p('Each scheduled execution uses one master seed across all three population settings and the retained per-function seed derivation. The three master seeds define three replicate batches. The 30 functions contribute to a suite score, rather than forming 30 independent replicate scores.')
    p.table(['Setting','Specification'],[['Algorithm','AdaptiveDE DC-DE (code identifier DUAL)'],['Benchmark','Unmodified opfunu 1.0.4 CEC2014, F01–F30'],['Search space','D = 10; bounds [−100, 100]'],['Population sizes','50, 100 and 150; fixed within each run'],['Objective budget','100,000 calls per function, including initialization'],['Algorithm settings','Adaptive exponential/binomial crossover; DLS memory and direction learning'],['Master seeds','2026111601, 2026111602 and 2026111603'],['Workload','3 batches × 3 populations × 30 functions = 270 runs']],[.25,.75],'Table 1. Controlled settings and complete experimental workload.',9)
    p.section(2);p.h('2.1 Outcome measure',2)
    p.p('For each population and master seed, the required score is the mean absolute error over all 30 functions:')
    p.equation()
    p.p('Here, fⱼ(xⱼ,best) is the saved final fitness and fⱼ* is the declared optimum. The calculation uses math.fsum on the absolute errors. It produces one scalar per parameter configuration and execution. Table 3 reports all nine scores and their sample standard deviations across the three seeds.')
    p.h('3 Bash implementation')
    p.p('run_experiments.sh enables strict Bash error handling, resolves paths relative to the script and rejects invalid arguments before optimization starts. A for loop passes the population size, seed and evaluation budget to the copied AdaptiveDE entry point. Standard output and standard error append to the same experiment.log using >> and 2>&1.')
    p.code('Listing 1. Parameter loop and per-configuration score verification. The complete executable script accompanies the report.',r'''for NP in "${POPULATIONS[@]}"; do
  "$PYTHON" "$ROOT/code/run_dcde.py" \
    --algorithms DUAL --runs 1 \
    --population-size "$NP" \
    --max-fes "$BUDGET" \
    --seed "$SEED" --workers "$WORKERS" \
    --output "$OUTPUT/np$NP" >> "$LOG" 2>&1
  "$PYTHON" "$ROOT/verify_batch.py" score \
    "$OUTPUT/np$NP" --run-id "$RUN" >> "$LOG" 2>&1
done''')
    p.section(2);p.h('3.1 Isolating repeated executions',2)
    p.p('Every batch uses a new output directory. Reusing an existing directory returns a nonzero status before any optimization, preventing old success lines from entering a new summary. An exclusive flock prevents overlapping scheduled invocations. Run identifiers record the population size, budget and seed in RUN_START; RESULT records identify individual functions.')
    p.h('3.2 Parsing structured results',2)
    p.p('A SUITE_RESULT line contains whitespace-separated key=value fields, including the score in scientific notation. grep selects only lines beginning with the exact event name. awk reads named fields rather than fixed token positions. The complete parser rejects missing or duplicate fields, invalid numerical notation and any result count other than three.')
    p.code('Listing 2. Score extraction through the required grep/awk pipeline. Additional validation remains in the submitted script.',r'''echo 'Automation mean absolute errors across CEC2014 F01-F30' \
  > "$OUTPUT/summary_report.txt"
grep '^SUITE_RESULT ' "$LOG" | awk '
  { for (i=2; i<=NF; i++) {
      split($i, pair, "="); v[pair[1]]=pair[2]
    }
    print v["run_id"], v["population"], v["budget"], \
          v["seed"], v["functions"], v["score"]
  }
' >> "$OUTPUT/summary_report.txt"''')
    p.section(2);p.p('verify_batch.py reconstructs the expected summary rows from the saved JSON records. It checks the score token against both the original log and the recomputed value. Scores are logged with 17 decimal places in scientific notation; shorter values in the report are display rounding only. The first population-50 score is 1.77162013832697034e+05 in both the log and the extracted summary.')
    p.h('4 Scheduled execution')
    p.p('System crontab launches the same Bash pipeline hourly during a bounded testing period. Absolute paths and quoted filenames accommodate the space in the workspace path. The cron expression is 20 * * * *, and redirected scheduler output is retained in cron/scheduled.log within the rerun directory. The exact installed entry appears in the execution evidence.')
    p.p('All three receipts contain the Linux ancestor chain identifying the real cron daemon. Planned launches and actual execution times are reported separately (Table 2 and Figure 2). The starts at 20:20:01, 21:20:02 and 22:20:01 differ from their planned minute boundaries by only 1–2 seconds. The two actual intervals are 3,601 and 3,599 seconds, confirming the hourly cadence. A temporary sleep/idle inhibitor prevents the resume delay observed in the earlier experiment.')
    p.fig('02_scheduled_execution','Scheduled and measured execution times on 16 November 2026. (a) Planned launch markers and actual execution intervals; launch delays are 1, 2 and 1 seconds. (b) Elapsed batch time from each original receipt; all three batches contain 90 validated records. Time is local to Asia/Shanghai.')
    timing=json.loads((OUT/'analysis/timing_audit.json').read_text())['executions']
    p.table(['Run','Planned','Actual start','Actual end','Delay','Records'],[[str(r['sequence']),r['planned_start'][11:19],r['actual_start'][11:19],r['actual_end'][11:19],f"{int(r['delay_seconds'])} s",'90'] for r in timing],[.07,.18,.20,.20,.17,.18],'Table 2. Original launch and completion times; date and timezone match Figure 2.',9)
    p.section(2);p.p('After three successful executions, the wrapper removes only its tagged Automation crontab entry and preserves unrelated jobs. A three-hour deadline bounds the testing schedule. A late launch beyond 60 seconds or a failed batch stops the test and retains its evidence; no manual catch-up is counted. Each batch has a 30-minute timeout. The sleep/idle inhibitor is released automatically after completion. Original, installed and final crontab snapshots are retained.')
    p.h('5 Population-size effects')
    p.p('Population 100 gives the lowest arithmetic mean of the three suite scores: 1.686687e+05. Population 50 follows at 1.778079e+05 and population 150 at 1.858846e+05. Figure 3a retains all individual seed scores, with lines joining configurations that share a master seed. Table 3 supplies their exact tabulated summaries.')
    p.fig('01_population_comparison','Population-size effects under the fixed budget. (a) Grey traces connect all nine scores by master seed; coloured markers and error bars show the three-seed mean ± sample SD for each population. (b) Number of functions with the lowest three-seed mean error; ties count for every tied population, using absolute tolerance 10⁻⁸ and relative tolerance 10⁻¹⁰. Four three-way ties contribute to all three counts. These are descriptive comparisons of three replicate batches.')
    suite_rows=[]
    for pop in [50,100,150]:
        a=[s['score'] for s in data['suites'] if s['population']==pop];pool=next(r for r in data['pooled'] if r['population']==pop)
        suite_rows.append([str(pop),*[f'{x:.6e}' for x in a],f"{pool['mean']:.6e}",f"{pool['sample_std']:.6e}",f"{100*pool['largest_share']:.2f}%"])
    p.table(['NP','Run 1','Run 2','Run 3','Mean','Sample SD','F29 share'],suite_rows,[.05,.165,.165,.165,.165,.165,.125],'Table 3. Suite scores over F01–F30 for master seeds 2026111601, 2026111602 and 2026111603, with mean, sample SD and F29’s pooled contribution.',8)
    p.section(2);p.h('5.1 Scale and functionwise coverage',2)
    p.p('F29 contributes 99.57%, 99.62% and 99.66% of pooled absolute error for populations 50, 100 and 150, respectively. The suite mean therefore largely follows F29. Counting each function equally produces a different ordering: population 50 has the lowest mean error on 16 functions, population 100 on 15, and population 150 on 11, including ties (Figure 3b).')
    p.p('The full error profile in Figure 4 exposes this scale difference and keeps every function visible. On F17, populations 100 and 150 both attain mean errors of about 6.93810e−02, compared with 4.01034e−01 at population 50. Their F30 mean errors are about 1.7881e+04, versus 2.17311e+04 at population 50. Under the common objective budget, larger populations also allow fewer generations. Each function has three observations per population; the ordering is descriptive.')
    p.h('5.2 Complete numerical results',2)
    p.p('Table 4 retains all 30 functions. Each cell gives the arithmetic mean and sample standard deviation of three absolute final errors. Bold means identify the lowest population means under the tie rule in Figure 3. The accompanying records.csv preserves each individual value, seed, final fitness, declared optimum and source hash.','Paper Note')
    rows=[];bold=set();comp=json.loads((OUT/'figures/comparison_data.json').read_text())
    for fid in range(1,31):
        row=[f'F{fid:02d}']
        for j,pop in enumerate([50,100,150]):
            a=[float(r['absolute_error']) for r in records if int(r['function'])==fid and int(r['population'])==pop];assert len(a)==3
            row.append(f'{math.fsum(a)/3:.5e} ({statistics.stdev(a):.3e})')
            if pop in comp['function_winners'][str(fid)]:bold.add((fid-1,j+1))
        rows.append(row)
    p.table(['Function','NP 50: mean (SD)','NP 100: mean (SD)','NP 150: mean (SD)'],rows,[.10,.30,.30,.30],'Table 4. Complete per-function absolute errors over the three master seeds; lower means are better.',8.5,bold)
    p.fig('03_function_profile','Complete functionwise mean errors across the three master seeds. Panels (a–c) cover F01–F10, F11–F20 and F21–F30 with identical logarithmic axes. Colours and marker shapes identify population sizes. Hollow markers at the labelled left floor denote values ≤10⁻⁸; numerical values remain unchanged in Table 4. All 270 saved solutions contribute to the means; Table 4 reports their sample SDs.')
    p.section(2);p.h('5.3 Explaining the suite-score scale',2)
    p.p('Figure 5 separates the pooled error of F29, F30 and the remaining 28 functions. F29 exceeds the other contributions by several orders of magnitude. A second diagnostic removes F29 and averages the remaining 29 absolute errors within each master seed. This comparison reveals how much of the observed ordering persists outside the dominant function; the required score remains the complete F01–F30 mean in Table 3.')
    p.fig('04_error_decomposition','Decomposing the scale-sensitive suite score. (a) Pooled absolute errors over all three seeds, split into F29, F30 and the other 28 functions; the vertical axis is logarithmic. (b) Diagnostic mean error over the 29 functions other than F29, shown for every seed as grey paired traces and summarized by coloured mean ± sample SD. Blue, orange and violet consistently identify NP 50, 100 and 150. The diagnostic does not replace the required 30-function score.')
    p.section(2);p.h('5.4 Complete convergence histories',2)
    p.p('Figures 6–8 compare measured progress on all 30 functions at the common evaluation budget. Each curve combines the three rerun master seeds for one population size. Median trajectories show the typical recorded progress, while min–max bands retain the observed seed variation. Population size is the only changed algorithm setting. All 270 histories contribute, including functions whose final errors tie or reach numerical precision.')
    p.p('The checkpoints differ slightly across population sizes. At the union of recorded evaluation counts, each history carries forward its most recently recorded value; no value is extrapolated before initialization. Each panel uses its own logarithmic vertical limits. A display floor of 10⁻⁸ makes zero errors visible without changing the stored values or the complete numerical table.','Paper Note')
    for first in [1,11,21]:
        p.fig(f'05_convergence_{first:02d}_{first+9:02d}',f'Convergence on F{first:02d}–F{first+9:02d} under 100,000 objective evaluations per run. Curves show the median absolute best-so-far error over three master seeds; shaded bands show the observed minimum and maximum, rather than confidence intervals. Blue circles/solid lines, orange squares/dashed lines and violet triangles/dash-dot lines identify NP 50, 100 and 150. All recorded checkpoints contribute through previous-observation hold. Vertical scales differ by function; values below 10⁻⁸ are displayed at that floor.',page=(first!=1))
    p.section(2);p.h('6 Experimental execution and verification')
    p.p('Independent checks recompute all 270 solutions and verify bounds, F01–F30 coverage, seeds, evaluation budgets, population sizes, monotone histories and source hashes. Audit calls are separate from optimization. BATCH_SUCCESS follows both record and summary validation.')
    p.p('Seven tests cover valid output, changed solutions, missing functions, altered summaries, reused directories, invalid arguments and manual ancestry. Failures stop the pipeline with nonzero status.')
    p.p('Recorded command evidence includes executable permissions, the vi search for SUITE_RESULT and :q! exit, Bash for/echo help, grep/awk help and man 5 crontab [3]. The current pipeline is rerun_20261116/run_experiments.sh; all paths in the implementation listings are relative to that directory. The earlier PGE-DE sources and November 10 records remain historical material and do not enter these tables or figures.')
    p.section(1);p.h('6.1 Scheduling records',2)
    p.p('Figures 9–15 document the completed experiments using saved logs, original receipts and command transcripts. The scheduling records show planned launches and actual cron ancestry; the batch records show score extraction for each execution. Full-resolution captures and source records accompany the report.','Paper Note')
    p.screenshot('01_schedule_configuration','Figure 9. Installed crontab and the three planned launch times.',110)
    p.screenshot('01_schedule_execution','Figure 10. Original scheduler events, actual execution times and cron ancestry.',110)
    p.h('6.2 Batch logs and score extraction',2,page=True)
    p.screenshot('02_execution_1','Figure 11. Run 1: original score lines, validation marker and extracted summary.',110)
    p.screenshot('02_execution_2','Figure 12. Run 2: original score lines, validation marker and extracted summary.',110)
    p.screenshot('02_execution_3','Figure 13. Run 3: original scores, actual completion time and extracted summary.',110,page=True)
    p.screenshot('03_unix_tools','Figure 14. Executable permissions, Bash help and the retained editor transcript.',110)
    p.h('6.3 Pipeline validation',2,page=True)
    p.screenshot('04_input_validation','Figure 15. Seven pipeline checks and the recorded test outcome.',145)
    p.section(1)
    p.h('7 Conclusions')
    p.p('The Bash workflow links parameter sweeps, optimization, structured logs, exact score extraction and independent numerical verification. Three genuine cron executions produced 270 validated solutions and nine suite scores. The temporary schedule removed itself after the third successful batch.')
    p.p('Population 100 achieves the lowest suite mean across the three master seeds, whereas population 50 gives the lowest mean on the most functions. F29’s dominant error contribution explains the difference between these summaries. Reporting both summaries keeps this scale dependence visible.')
    p.h('References')
    for s in ['[1] Automation protocol. Bash execution, structured logging and experiment analysis.','[2] AdaptiveDE final DC-DE implementation and experimental report. Unchanged DLS-based adaptive crossover optimizer; copied runner and source lineage retained in the rerun evidence.','[3] Installed Bash, grep, awk and crontab manual resources. Executed help excerpts retained with the command evidence.']:p.p(s,'Paper Note')
    p.save();print(OUT/'Automation_Study.docx')
if __name__=='__main__':main()
