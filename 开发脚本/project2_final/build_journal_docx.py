"""Rebuild the report body from measured evidence in paper-style columns. Author: 殷明骏."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,re,zipfile,tempfile
from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Mm,Inches,Pt,RGBColor
from docx.oxml import OxmlElement,parse_xml
from docx.oxml.ns import qn
from lxml import etree
from clean_metadata import clean_docx

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output';WIDTH=6.8504
BASE=ROOT/'source/journal_content_base.docx';DOC=OUT/'Project2_Report.docx'
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M='http://schemas.openxmlformats.org/officeDocument/2006/math'
A='http://schemas.openxmlformats.org/drawingml/2006/main'

def visible(n):return ''.join(t.text or '' for t in n.iter(qn('w:t')))

class Journal:
    def __init__(self):
        self.doc=Document(BASE);body=self.doc._element.body
        self.cover=etree.fromstring((ROOT/'source/cover_preserved.xml').read_bytes())
        for n in list(body):
            if n.tag!=qn('w:sectPr'):body.remove(n)
        for i,n in enumerate(self.cover):body.insert(i,deepcopy(n))
        self.cols=0;self.figures=[];self.titles=[];self.md=['# NUIST Experiment Report'];self.figure_no=0
        for n in self.cover:
            if visible(n):self.md.append(visible(n))
        for name,size,bold in [('Journal Body',10,False),('Journal Note',8.5,False),('Journal Caption',8.5,False),('Journal Heading 1',11.5,True),('Journal Heading 2',10,True),('Journal Title',16,True)]:
            st=self.doc.styles.add_style(name,1) if name not in self.doc.styles else self.doc.styles[name]
            st.font.name='Times New Roman';st.font.size=Pt(size);st.font.bold=bold;st.font.color.rgb=RGBColor(0,0,0)
            pf=st.paragraph_format;pf.line_spacing=1.05;pf.space_before=Pt(0);pf.space_after=Pt(4);pf.widow_control=True
            if 'Heading' in name:pf.keep_with_next=True;pf.space_before=Pt(7);pf.space_after=Pt(4)
            if 'Heading' in name:
                level=OxmlElement('w:outlineLvl');level.set(qn('w:val'),'0' if name.endswith('1') else '1');st._element.get_or_add_pPr().append(level)
        self.section(1,first=True)
        # Shared body furniture does not affect the retained first-page parts.
        for p in self.doc.sections[-1].header.paragraphs:
            p.clear();p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
            r=p.add_run('Project 2   Differential evolution');r.font.name='Times New Roman';r.font.size=Pt(7);r.italic=True
        for p in self.doc.sections[-1].footer.paragraphs:
            p.clear();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');p._p.append(fld)
            p.paragraph_format.space_before=Pt(0)

    def section(self,cols,first=False):
        if self.cols==cols:return
        sec=self.doc.add_section(WD_SECTION_START.NEW_PAGE if first else WD_SECTION_START.CONTINUOUS)
        sec.page_width=Mm(210);sec.page_height=Mm(297)
        sec.left_margin=sec.right_margin=Mm(18);sec.top_margin=sec.bottom_margin=Mm(18)
        sec.header_distance=sec.footer_distance=Mm(8);sec.different_first_page_header_footer=False
        c=sec._sectPr.find(qn('w:cols'));c.attrib.clear();c.set(qn('w:num'),str(cols));c.set(qn('w:space'),'340');c.set(qn('w:equalWidth'),'1')
        for child in list(c):c.remove(child)
        self.cols=cols

    def p(self,text,style='Journal Body',keep=False):
        p=self.doc.add_paragraph(text,style);p.paragraph_format.keep_with_next=keep
        if style=='Journal Body':p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
        self.md.append(text);return p

    def clone_p(self,node,style='Journal Body',text=None):
        n=parse_xml(etree.tostring(node))
        p=self.doc.add_paragraph();p._p.addprevious(n);self.doc._element.body.remove(p._p)
        from docx.text.paragraph import Paragraph
        p=Paragraph(n,self.doc._body);p.style=self.doc.styles[style]
        pf=p.paragraph_format;pf.page_break_before=False;pf.keep_together=False;pf.keep_with_next=('Heading' in style);pf.space_before=Pt(6 if 'Heading' in style else 0);pf.space_after=Pt(4);pf.line_spacing=1.05
        pf.first_line_indent=Pt(0);pf.left_indent=Pt(0);pf.right_indent=Pt(0);pf.widow_control=True
        for r in p.runs:
            r.font.name='Times New Roman';r.font.size=Pt(11.5 if style.endswith('Heading 1') else 10 if style in ['Journal Body','Journal Heading 2'] else 8.5);r.font.color.rgb=RGBColor(0,0,0)
            r.bold='Heading' in style
        if text is not None:
            ts=list(n.iter(qn('w:t')))
            if ts:
                ts[0].text=text
                for t in ts[1:]:t.text=''
        self.md.append(visible(n));return n

    def heading(self,node,text=None):
        s=text or visible(node);level=2 if re.match(r'^\d+\.',s) or s=='Guide and memory definitions' else 1
        n=self.clone_p(node,f'Journal Heading {level}',s)
        anchor=next(iter(n.iter(qn('w:bookmarkStart'))),None)
        if anchor is not None:self.titles.append({'title':s,'anchor':anchor.get(qn('w:name')),'level':level})

    def figure(self,name,caption):
        self.section(1);self.figure_no+=1
        caption=re.sub(r'^Figure \d+\.',f'Figure {self.figure_no}.',caption)
        p=self.doc.add_paragraph();p.paragraph_format.space_before=Pt(5);p.paragraph_format.space_after=Pt(3);p.paragraph_format.keep_with_next=True
        p.add_run().add_picture(str(OUT/'figures'/f'{name}.png'),width=Inches(WIDTH))
        cp=self.p(caption,'Journal Caption');cp.paragraph_format.space_after=Pt(6)
        cp.clear();label,rest=caption.split('.',1);cp.add_run(label+'.').bold=True;cp.add_run(rest)
        self.figures.append(name);self.md.append(f'![Figure](figures/{name}.png)')

    def table(self,node):
        self.section(1);n=parse_xml(etree.tostring(node));self.doc._element.body.insert(len(self.doc._element.body)-1,n)
        from docx.table import Table
        table=Table(n,self.doc._body);table.autofit=False
        # Wider paper-style evidence tables retain every original cell.
        old_grid=[int(x.get(qn('w:w'))) for x in n.findall('./'+qn('w:tblGrid')+'/'+qn('w:gridCol'))]
        if not old_grid:old_grid=[1]*len(table.columns)
        ratios=[x/sum(old_grid) for x in old_grid]
        for i,col in enumerate(table.columns):col.width=Inches(WIDTH*ratios[i])
        for e in n.findall('.//'+qn('w:tblBorders')):
            for child in e:child.set(qn('w:val'),'nil')
            for edge in ['top','bottom']:
                x=e.find(qn('w:'+edge));x.set(qn('w:val'),'single');x.set(qn('w:sz'),'5');x.set(qn('w:color'),'222222')
        mar=n.find('./'+qn('w:tblPr')+'/'+qn('w:tblCellMar'))
        if mar is not None:
            for e in mar:e.set(qn('w:w'),'12' if e.tag in [qn('w:top'),qn('w:bottom')] else '45')
        for i,row in enumerate(table.rows):
            for j,cell in enumerate(row.cells):
                cell.width=Inches(WIDTH*ratios[j])
                for sh in cell._tc.get_or_add_tcPr().findall(qn('w:shd')):sh.set(qn('w:fill'),'FFFFFF')
                for border in cell._tc.get_or_add_tcPr().findall(qn('w:tcBorders')):
                    for e in border:e.set(qn('w:color'),'B0B0B0');e.set(qn('w:sz'),'2')
                for p in cell.paragraphs:
                    p.paragraph_format.line_spacing=1.0;p.paragraph_format.space_before=Pt(0);p.paragraph_format.space_after=Pt(0)
                    for run in p.runs:run.font.name='Times New Roman';run.font.size=Pt(8);run.font.color.rgb=RGBColor(0,0,0)
            if i==0:
                for cell in row.cells:
                    pr=cell._tc.get_or_add_tcPr();b=pr.find(qn('w:tcBorders'))
                    if b is None:b=OxmlElement('w:tcBorders');pr.append(b)
                    x=OxmlElement('w:bottom');x.set(qn('w:val'),'single');x.set(qn('w:sz'),'3');x.set(qn('w:color'),'222222');b.append(x)
        rows=[[c.text for c in row.cells] for row in table.rows]
        self.md.append('| '+' | '.join(rows[0])+' |');self.md.append('| '+' | '.join('---' for _ in rows[0])+' |');self.md.extend('| '+' | '.join(row)+' |' for row in rows[1:])

    def save(self):
        self.doc.core_properties.author=self.doc.core_properties.last_modified_by='殷明骏'
        self.doc.core_properties.title='Project 2 Differential Evolution Experiments';self.doc.core_properties.subject='';self.doc.core_properties.comments='';self.doc.core_properties.keywords=''
        self.doc.save(DOC);clean_docx(DOC)
        previous=json.loads((ROOT/'source/journal_base_fidelity.json').read_text())
        preserve=previous['preserve_only_parts']
        temp=DOC.with_suffix('.opaque.docx')
        with zipfile.ZipFile(DOC) as current,zipfile.ZipFile(ROOT/'source/template/实验报告模板.docx') as template,zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as out:
            for name in current.namelist():out.writestr(name,template.read(name) if name in preserve else current.read(name))
        temp.replace(DOC)
        with zipfile.ZipFile(DOC) as z:
            root=etree.fromstring(z.read('word/document.xml'));nodes=list(root.find(qn('w:body')))
            c=lambda n:etree.tostring(n,method='c14n',exclusive=True)
            assert [c(n) for n in nodes[:len(self.cover)]]==[c(n) for n in self.cover]
        previous.update(header_only=False,title_xml_unchanged=True,section_geometry_unchanged=False,cover_geometry_unchanged=True,body_geometry_user_authorized=True,body_columns=2,body_margin_mm=18,intentional_changes=['Only the first page is locked','Two-column paper body','Full-width figures and tables','Black ruled numerical tables','No contents page or appendices'])
        (OUT/'template_fidelity.json').write_text(json.dumps(previous,ensure_ascii=False,indent=2)+'\n')
        (OUT/'report_figures.json').write_text(json.dumps(self.figures,indent=2)+'\n')
        (OUT/'report_sections.json').write_text(json.dumps(self.titles,ensure_ascii=False,indent=2)+'\n')
        (OUT/'Project2_Report.md').write_text('\n\n'.join(self.md)+'\n')
        (OUT/'journal_body_manifest.json').write_text(json.dumps({'author':'殷明骏','figure_sheets':self.figures,'sections':self.titles,'cover_xml_unchanged':True,'body_columns':2,'all_statistics_retained':True,'curve_functions':30},ensure_ascii=False,indent=2)+'\n')

def main():
    with zipfile.ZipFile(BASE) as z:source=etree.fromstring(z.read('word/document.xml')).find(qn('w:body'))
    nodes=list(source);figs=json.loads((ROOT/'source/journal_base_figures.json').read_text());j=Journal()
    abstract=next(visible(n) for n in nodes if visible(n).startswith('Strategy transfer in differential evolution depends'))
    keywords=next(visible(n) for n in nodes if visible(n).startswith('Keywords:'))
    j.p('Reconstruction and strategy transfer in differential evolution','Journal Title')
    j.p('DSPDE, DLS-DE, PEMS-DE and a controlled PGE-DE combination','Journal Note')
    j.p('Abstract','Journal Heading 2');j.p(abstract);j.p(keywords,'Journal Note')
    start=next(i for i,n in enumerate(nodes) if visible(n)=='1 Introduction');j.section(2)
    picture_index=0;skip_caption=False;seen_stats=set();skip_note=False;curve_heading=False
    mapping={'00_experiment_flow':'journal_workflow','00_algorithm_flow':'journal_mechanisms','01_performance':'journal_performance',
             '02_evaluator':'journal_02_evaluator','03_transfer':'journal_03_transfer','04_distributions':'journal_04_distributions','05_telemetry':'journal_05_telemetry'}
    for n in nodes[start:]:
        if n.tag==qn('w:sectPr'):continue
        if n.tag==qn('w:tbl'):j.table(n);continue
        if n.tag!=qn('w:p'):continue
        s=visible(n)
        if list(n.iter('{'+A+'}blip')):
            name=figs[picture_index];picture_index+=1;skip_caption=True
            cap=visible(n.getnext())
            if name.startswith('curves_'):
                first=int(name.split('_')[1])
                if (first-1)%6:continue
                caption=f'Figure 0. Best-run convergence for F{first:02d}–F{first+5:02d}. Each panel retains all measured checkpoints of the lowest-final-objective run among 20 runs per method. CEC2014, 10D, fixed NP 100, 100,000 FEs; original objective values, logarithmic vertical axes, no smoothing or cross-run splicing.'
                j.figure(f'journal_curves_{first:02d}_{first+5:02d}',caption)
            else:
                if name=='00_experiment_flow':cap='Figure 0. Experimental tracks. Original-condition reconstructions and source controls retain their recorded protocols; all five complete algorithms share the common fixed-population CEC2014 comparison. Every function and condition has 20 independent runs.'
                if name=='00_algorithm_flow':cap='Figure 0. PGE-DE mechanism interfaces. (a) Symbolic mutation geometry combines potential-weighted guidance and a donor difference; coordinates are explanatory rather than measured. (b) F sampling changes after 30% of the consumed budget. (c) Eligible inferior targets receive a probabilistic escape proposal; otherwise the ordinary candidate is retained. Every evaluated candidate consumes the shared budget.'
                if name=='01_performance':cap='Figure 0. Overall ordering and complete paired effects. (a) Mean within-function error rank across the fixed 30-function set. (b) Signed rank-biserial effects of PGE-DE versus each control; blue favours PGE-DE, red favours the control, and black dots mark Holm-adjusted P < 0.05 in the 120-test family. Each cell uses 20 paired seeds; nondetection does not establish equivalence.'
                j.figure(mapping[name],cap)
            continue
        if skip_caption:
            if s.startswith('Figure '):skip_caption=False;continue
            skip_caption=False
        if not s and not list(n.iter('{'+M+'}oMath')):continue
        if s.startswith('6.4 '):
            if not curve_heading:
                j.section(1);j.heading(n,'6.4 Convergence behaviour across all 30 functions');curve_heading=True
            continue
        stat=re.match(r'^(5\.[234]|6\.[23]) ',s)
        if stat:
            key=stat[1];skip_note=key in seen_stats
            if skip_note:continue
            seen_stats.add(key);j.section(1);j.heading(n,re.sub(r' F\d+ to F\d+$','',s));continue
        if skip_note and (s.startswith('CEC2014,') or 'Each row summarizes 20 runs.' in s):skip_note=False;continue
        if s.startswith('Table '):
            j.section(1);p=j.clone_p(n,'Journal Caption');ppr=p.find(qn('w:pPr'));keep=OxmlElement('w:keepNext');ppr.append(keep);continue
        if list(n.iter('{'+M+'}oMath')):
            j.section(1);j.clone_p(n,'Journal Note');continue
        is_heading=bool(re.match(r'^\d+(?:\.\d+)? ',s)) or s in ['Guide and memory definitions','Function families','References']
        if is_heading:
            following=n.getnext()
            j.section(1 if following is not None and list(following.iter('{'+A+'}blip')) else 2)
            j.heading(n);continue
        # Notes immediately accompanying wide evidence stay at full width.
        style_id=n.find('./'+qn('w:pPr')+'/'+qn('w:pStyle'));style_id=style_id.get(qn('w:val')) if style_id is not None else ''
        if style_id in ['PaperNote','ReportNote']:
            j.clone_p(n,'Journal Note')
        else:j.section(2);j.clone_p(n)
    assert picture_index==len(figs)==22
    assert len(j.figures)==12 and len([x for x in j.figures if 'curves' in x])==5
    j.save();print(json.dumps({'figure_sheets':len(j.figures),'sections':len(j.titles),'body_columns':2,'author':'殷明骏'},ensure_ascii=False))

if __name__=='__main__':main()
