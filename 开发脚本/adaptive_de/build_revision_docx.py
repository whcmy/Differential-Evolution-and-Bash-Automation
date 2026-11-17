"""Template-preserving illustrated report. Author: 殷明骏, 202483890029."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import csv
import hashlib
import json
import re
import sys
import tempfile
import zipfile
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from lxml import etree
from build_template_docx import build as build_opening, TEMPLATE
from clean_metadata import clean_docx
from paper_layout import enable_paper_body, preserve_cover
from integrate_main_body import integrate

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'
DOC=OUT/'DCDE_Study.docx'
WIDTH=5.76805556
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M='http://schemas.openxmlformats.org/officeDocument/2006/math'
TITLES=[]
TEXT=[]
FIGURES=[]

def csvrows(name):
    with (OUT/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def fmt(x):
    v=float(x)
    return '0' if v==0 else f'{v:.3e}'

def shade(cell,color):
    s=OxmlElement('w:shd');s.set(qn('w:fill'),color);cell._tc.get_or_add_tcPr().append(s)

def font(run,size=12,bold=False,color='000000'):
    run.font.name='Times New Roman';run.font.size=Pt(size);run.bold=bold;run.font.color.rgb=RGBColor.from_string(color)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'宋体')

class Report:
    def __init__(self,pages=None):
        build_opening(header_only=True)
        self.doc=Document(DOC);self.body=self.doc._element.body
        nodes=list(self.body)
        start=next(i for i,n in enumerate(nodes) if '1. Experimental objectives' in ''.join(n.itertext()))
        for n in nodes[start:]:
            if n.tag!=qn('w:sectPr'):self.body.remove(n)
        self.pages=pages or {};self.id=100;self.contents=[]
        self.table_id=0
        self.figure_nodes=[]
        for name,size,bold in [('Report Body',12,False),('Report Heading 1',14,True),('Report Heading 2',12,True),('Report Caption',9.5,False),('Report Note',9.5,False)]:
            st=self.doc.styles.add_style(name,1) if name not in self.doc.styles else self.doc.styles[name]
            st.font.name='Times New Roman';st.font.size=Pt(size);st.font.bold=bold;st.font.color.rgb=RGBColor(0,0,0)
            pf=st.paragraph_format;pf.first_line_indent=Pt(0);pf.left_indent=Pt(0);pf.right_indent=Pt(0);pf.space_before=Pt(0);pf.space_after=Pt(7);pf.line_spacing=1.5 if name=='Report Body' else 1.15
            st._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'宋体')
            if 'Heading' in name:
                pf.keep_with_next=True;pf.space_before=Pt(12);pf.space_after=Pt(9)
                lev=OxmlElement('w:outlineLvl');lev.set(qn('w:val'),'0' if name.endswith('1') else '1');st._element.get_or_add_pPr().append(lev)
        # Navigation additions are confined to page furniture, outside the source fields.
        s=self.doc.sections[0];s.different_first_page_header_footer=True
        first=s.first_page_header.paragraphs[0];first.style=self.doc.styles['Report Note']
        borders=OxmlElement('w:pBdr');bottom=OxmlElement('w:bottom');bottom.set(qn('w:val'),'nil');borders.append(bottom);first._p.get_or_add_pPr().append(borders)
        p=s.header.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
        font(p.add_run('ADAPTIVE DE   DIFFERENTIAL EVOLUTION'),8,color='5D6B73')
        p.paragraph_format.space_after=Pt(0)
        p=s.footer.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
        font(p.add_run('Adaptive DE  |  '),9,color='5D6B73')
        f=OxmlElement('w:fldSimple');f.set(qn('w:instr'),'PAGE');r=OxmlElement('w:r');t=OxmlElement('w:t');t.text='1';r.append(t);f.append(r);p._p.append(f)
        settings=self.doc.settings._element
        update=OxmlElement('w:updateFields');update.set(qn('w:val'),'true');settings.append(update)

    def p(self,text,style='Report Body',keep=False):
        p=self.doc.add_paragraph(style=style);p.paragraph_format.keep_with_next=keep
        p.paragraph_format.widow_control=True
        snap=OxmlElement('w:snapToGrid');snap.set(qn('w:val'),'0');p._p.get_or_add_pPr().append(snap)
        font(p.add_run(text),12 if style=='Report Body' else 9.5)
        TEXT.append(text);return p

    def h(self,text,level=1,newpage=False,toc=True):
        p=self.doc.add_paragraph(style=f'Report Heading {level}');font(p.add_run(text),14 if level==1 else 12,True)
        p.paragraph_format.page_break_before=newpage
        p.paragraph_format.space_before=Pt(0 if newpage else 10)
        self.id+=1;anchor=f'section_{self.id}'
        a=OxmlElement('w:bookmarkStart');a.set(qn('w:id'),str(self.id));a.set(qn('w:name'),anchor)
        b=OxmlElement('w:bookmarkEnd');b.set(qn('w:id'),str(self.id));p._p.insert(0,a);p._p.append(b)
        if toc:TITLES.append(dict(title=text,anchor=anchor,level=level))
        TEXT.extend(['## '+text,'']);return p

    def table(self,headers,rows,widths=None,groups=None,highlight=None,size=9,caption=None):
        if caption:self.p(caption,'Report Caption',keep=True)
        n=len(headers);widths=widths or [1/n]*n
        t=self.doc.add_table(rows=1,cols=n);t.autofit=False
        for c,w in zip(t.columns,widths):c.width=Inches(WIDTH*w)
        pr=t._tbl.tblPr
        borders=OxmlElement('w:tblBorders')
        for edge in ['top','bottom','left','right','insideH','insideV']:
            el=OxmlElement('w:'+edge);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'3');el.set(qn('w:color'),'D9D9D9');borders.append(el)
        pr.append(borders)
        margins=OxmlElement('w:tblCellMar')
        for edge,val in [('top',18),('bottom',18),('left',45),('right',45)]:
            e=OxmlElement('w:'+edge);e.set(qn('w:w'),str(val));e.set(qn('w:type'),'dxa');margins.append(e)
        pr.append(margins)
        allrows=[headers]+rows
        for i,row in enumerate(allrows):
            cells=t.rows[0].cells if i==0 else t.add_row().cells
            group=groups[i-1] if i and groups else i
            for j,(cell,value) in enumerate(zip(cells,row)):
                cell.width=Inches(WIDTH*widths[j]);cell.vertical_alignment=1
                p=cell.paragraphs[0];p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.space_before=Pt(0);p.paragraph_format.space_after=Pt(0);p.paragraph_format.line_spacing=1
                snap=OxmlElement('w:snapToGrid');snap.set(qn('w:val'),'0');p._p.get_or_add_pPr().append(snap)
                p.paragraph_format.keep_with_next=(i<len(allrows)-1 and groups is not None and (i==0 or groups[i-1]==groups[i]))
                numeric=(n>=4 and j>=1 and (headers[1]!='Algorithm' or j>=2))
                p.alignment=WD_ALIGN_PARAGRAPH.RIGHT if numeric else WD_ALIGN_PARAGRAPH.LEFT
                font(p.add_run(str(value)),size,i==0 or (highlight is not None and i-1 in highlight and j in [3,6]),'FFFFFF' if i==0 else '000000')
                shade(cell,'304E60' if i==0 else ('F1F5F7' if group%2==0 else 'FFFFFF'))
            trp=t.rows[i]._tr.get_or_add_trPr();trp.append(OxmlElement('w:cantSplit'))
            if i > 1 and groups is not None and groups[i-1] != groups[i-2]:
                for cell in cells:
                    border=OxmlElement('w:tcBorders');edge=OxmlElement('w:top')
                    for key,value in [('val','single'),('sz','5'),('color','BCCBD3')]:edge.set(qn('w:'+key),value)
                    border.append(edge);cell._tc.get_or_add_tcPr().append(border)
            if i==0:trp.append(OxmlElement('w:tblHeader'))
        self.p('','Report Note')
        TEXT.append('| '+' | '.join(headers)+' |');TEXT.append('| '+' | '.join(['---']*n)+' |')
        TEXT.extend('| '+' | '.join(map(str,r))+' |' for r in rows);TEXT.append('')
        return t

    def fig(self,name,caption,width=WIDTH):
        p=self.doc.add_paragraph();p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.left_indent=Pt(0);p.paragraph_format.right_indent=Pt(0);p.paragraph_format.space_before=Pt(4);p.paragraph_format.space_after=Pt(6);p.paragraph_format.keep_with_next=True
        snap=OxmlElement('w:snapToGrid');snap.set(qn('w:val'),'0');p._p.get_or_add_pPr().append(snap)
        p.add_run().add_picture(str(OUT/'figures'/f'{name}.png'),width=Inches(width))
        self.figure_nodes.append((p._p,name))
        self.p(caption,'Report Caption');FIGURES.append(name);TEXT.extend([f'![{caption}](figures/{name}.png)',''])

    def equation(self,pieces,number):
        p=self.doc.add_paragraph();p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.left_indent=Pt(0);p.paragraph_format.right_indent=Pt(0);p.paragraph_format.space_before=Pt(3);p.paragraph_format.space_after=Pt(9)
        om=etree.Element('{'+M+'}oMath')
        for piece in pieces:om.append(piece)
        p._p.append(om);font(p.add_run('     ('+str(number)+')'),11)
        TEXT.append('Equation '+str(number)+': '+''.join(om.itertext()))

def mr(s):
    r=etree.Element('{'+M+'}r');rp=etree.SubElement(r,'{'+M+'}rPr');sty=etree.SubElement(rp,'{'+M+'}sty');sty.set('{'+M+'}val','p')
    t=etree.SubElement(r,'{'+M+'}t');t.text=s;return r

def sub(base,index):
    s=etree.Element('{'+M+'}sSub');e=etree.SubElement(s,'{'+M+'}e');e.append(mr(base));v=etree.SubElement(s,'{'+M+'}sub');v.append(mr(index));return s

def frac(a,b):
    s=etree.Element('{'+M+'}f');e=etree.SubElement(s,'{'+M+'}num')
    for node in [mr(a)] if isinstance(a,str) else a:e.append(node)
    v=etree.SubElement(s,'{'+M+'}den')
    for node in [mr(b)] if isinstance(b,str) else b:v.append(node)
    return s

def sub_sup(base,index,power):
    s=etree.Element('{'+M+'}sSubSup')
    for tag,value in [('e',base),('sub',index),('sup',power)]:
        e=etree.SubElement(s,'{'+M+'}'+tag);e.append(mr(value))
    return s

def save(r):
    preserve_cover(r,ROOT,WIDTH)
    abstract=TEXT.index('Abstract')
    cover=etree.fromstring((ROOT/'source/cover_preserved.xml').read_bytes())
    cover_text=[''.join(t.text or '' for t in n.iter(qn('w:t'))) for n in cover]
    TEXT[:abstract]=['# Optimization Research']+[s for s in cover_text if s and s!='Optimization Research']
    for p,label,target in r.contents:
        section=next(x for x in TITLES if x['title']==target)
        for child in list(p._p):
            if child.tag!=qn('w:pPr'):p._p.remove(child)
        link=OxmlElement('w:hyperlink');link.set(qn('w:anchor'),section['anchor'])
        rr=OxmlElement('w:r');rp=OxmlElement('w:rPr');ff=OxmlElement('w:rFonts');ff.set(qn('w:ascii'),'Times New Roman');ff.set(qn('w:hAnsi'),'Times New Roman');rp.append(ff);sz=OxmlElement('w:sz');sz.set(qn('w:val'),'19');rp.append(sz);rr.append(rp)
        tt=OxmlElement('w:t');tt.text=label;rr.append(tt);link.append(rr);p._p.append(link)
        rr=OxmlElement('w:r');rr.append(OxmlElement('w:tab'));p._p.append(rr)
        field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGEREF '+section['anchor']+' \\h')
        rr=OxmlElement('w:r');rr.append(deepcopy(rp));tt=OxmlElement('w:t');tt.text=str(r.pages.get(target,''));rr.append(tt);field.append(rr);p._p.append(field)
    r.doc.core_properties.author='殷明骏';r.doc.core_properties.last_modified_by='殷明骏';r.doc.core_properties.subject=''
    r.doc.core_properties.keywords=''
    r.doc.core_properties.title='Adaptive DE Differential Evolution Experiments';r.doc.core_properties.comments=''
    with tempfile.TemporaryDirectory(dir=ROOT/'template_work') as temp:
        generated=Path(temp)/'report.docx';r.doc.save(generated)
        editable={'word/document.xml','word/styles.xml','word/settings.xml','docProps/core.xml','docProps/app.xml','word/_rels/document.xml.rels','[Content_Types].xml'}
        with zipfile.ZipFile(TEMPLATE) as original,zipfile.ZipFile(generated) as built,zipfile.ZipFile(DOC,'w',zipfile.ZIP_DEFLATED) as final:
            for name in original.namelist():final.writestr(name,built.read(name) if name in editable else original.read(name))
            for name in built.namelist():
                if name not in original.namelist():final.writestr(name,built.read(name))
    clean_docx(DOC)
    with zipfile.ZipFile(TEMPLATE) as src,zipfile.ZipFile(DOC) as dst:
        preserve=[n for n in src.namelist() if n not in editable]
        assert all(src.read(n)==dst.read(n) for n in preserve)
        a=etree.fromstring(src.read('word/document.xml'));b=etree.fromstring(dst.read('word/document.xml'))
        assert etree.tostring(a.find('.//{'+W+'}body/{'+W+'}p'),method='c14n')==etree.tostring(b.find('.//{'+W+'}body/{'+W+'}p'),method='c14n')
        for el in ['pgSz','pgMar','cols','docGrid']:
            assert etree.tostring(a.find('.//{'+W+'}sectPr/{'+W+'}'+el))==etree.tostring(b.find('.//{'+W+'}sectPr/{'+W+'}'+el))
        visible=''.join(b.itertext());identity=json.loads((ROOT/'protocol/report_identity.json').read_text())
        for name in [identity['tutor_chinese']]+[m['chinese'] for m in identity['members']]:visible=visible.replace(name,'')
        assert not re.search(r'[\u3400-\u9fff]',visible)
    fidelity=dict(author='殷明骏',student_id='202483890029',header_only=False,retained_template_unchanged=True,title_xml_unchanged=True,
                  section_geometry_unchanged=True,preserve_only_parts=preserve,template_sha256=hashlib.sha256(TEMPLATE.read_bytes()).hexdigest(),
                  intentional_changes=['Free body redesigned','Semantic styles','Header/footer navigation','Update fields setting','New figures and equations'])
    (OUT/'template_fidelity.json').write_text(json.dumps(fidelity,ensure_ascii=False,indent=2)+'\n')
    (OUT/'report_contents.json').write_text(json.dumps([dict(label=l,target=t) for _,l,t in r.contents],indent=2)+'\n')
    (OUT/'report_sections.json').write_text(json.dumps(TITLES,ensure_ascii=False,indent=2)+'\n')
    (OUT/'report_figures.json').write_text(json.dumps(FIGURES,indent=2)+'\n')
    (OUT/'DCDE_Study.md').write_text('\n\n'.join(TEXT),encoding='utf-8')

def main(pages=None):
    TITLES.clear();TEXT.clear();FIGURES.clear()
    r=Report(pages)
    identity=json.loads((ROOT/'protocol/report_identity.json').read_text())
    TEXT.extend(['# Optimization Research','protocol name: '+identity['course_english'],
                 'Experiment name: Adaptive DE Differential Evolution',
                 'Tutor: '+identity['tutor_chinese']+' / '+identity['tutor_english'],
                 'College: '+identity['college_english'],'Class: '+identity['class_english']])
    TEXT.extend('Name: '+m['chinese']+' / '+m['english']+'   Student ID: '+m['student_id'] for m in identity['members'])
    r.h('Contributions',2,toc=False)
    for statement in json.loads((ROOT/'protocol/contributions.json').read_text())['statements']:
        r.p(statement,'Report Note')
    enable_paper_body(r)
    r.h('Abstract',newpage=True,toc=False)
    r.p('Strategy transfer in differential evolution depends on both the receiving algorithm and the benchmark implementation. This study reconstructs DSPDE, DLS-DE and PEMS-DE, evaluates their components, and integrates three mechanisms into PGE-DE. A controlled CEC2014 comparison uses 20 paired initialization seeds per function, a fixed population of 100 and a budget of 100,000 evaluations. The common experiments contain 7,200 optimization records. PGE-DE achieves 11 Holm-corrected wins against basic DE, with seven losses, and ranks fourth among five methods; DLS-DE has the lowest mean rank. Component controls identify which source benefits survive transfer to the combined backbone. An independent audit finds evaluator differences on 13 functions, and 600 saved C++ solutions reproduce their recorded values exactly. These results connect algorithm reconstruction, component testing and evaluator verification in one reproducible comparison, revealing where the combined strategy improves performance and where its shared guidance concentrates the population.', 'Paper Abstract')
    r.p('Keywords: differential evolution; strategy transfer; component ablation; CEC2014; benchmark verification', 'Paper Keywords')
    r.h('Contents',newpage=False,toc=False)
    contents=[('1 Introduction','1 Introduction'),('2 Methods','2 Methods'),('3 Benchmark fidelity','3 Benchmark fidelity'),('4 Component strategy evidence','4 Component strategy evidence'),('5 Comparative performance','5 Comparative performance'),('6 Mechanistic interpretation','6 Mechanistic interpretation'),('7 Conclusions','7 Conclusions'),('References','References'),('Appendix A Reproduction details','Appendix A Reproduction details'),('Appendix B Original condition results','Appendix B1 DSPDE original condition results'),('Appendix C Five algorithm statistics','Appendix C Five algorithm statistics F01 to F08'),('Appendix D PEMS-DE ablations','Appendix D PEMS-DE ablations F01 to F08'),('Appendix E PGE-DE ablations','Appendix E PGE-DE ablations F01 to F10'),('Appendix F DSPDE ablations','Appendix F DSPDE ablations F01 to F06'),('Appendix G DLS-DE native ablations','Appendix G DLS-DE native ablations F01 to F06'),('Appendix H Convergence curves','Appendix H Convergence curves F01 and F02')]
    # Page numbers are filled from the rendered document in the second build.
    for label,target in contents:
        p=r.p(label,'Report Note');p.paragraph_format.space_after=Pt(12)
        p.paragraph_format.tab_stops.add_tab_stop(Inches(WIDTH-.1),WD_ALIGN_PARAGRAPH.RIGHT)
        font(p.add_run('\t'+str((pages or {}).get(target,''))),9.5)
        r.contents.append((p,label,target))
    r.h('Reading the evidence',2,toc=False)
    r.p('The main comparison uses one common opfunu objective and paired seeds. Native reproductions establish source context; component controls explain transfer. Appendices retain complete statistics and all 30 best-run convergence curves. ND denotes no detected difference after correction.','Report Note')

    r.h('1 Introduction',newpage=True)
    r.p('Combining successful differential evolution (DE) mechanisms requires more than adding operators: each mechanism changes the population on which the others act. This study examines that interaction through reconstructions of DSPDE [1], DLS-DE [2] and PEMS-DE [3], followed by a frozen three-strategy PGE-DE combination.')
    r.p('The experimental contribution is an end-to-end comparison linking native reproductions, component controls, a common evaluation protocol and an independent evaluator audit. This design identifies useful source mechanisms, measures their behavior after transfer and separates algorithm effects from changes in the objective landscape.')
    r.h('1.1 Experimental tracks',2,toc=False)
    r.fig('00_experiment_flow','Figure X1. Experimental design. Three paper reconstructions are evaluated in separate original-condition tracks; source controls retain their recorded protocols. The common CEC2014 track compares five complete algorithms with paired initialization seeds and a fixed evaluation budget. This diagram describes the executed design rather than additional observations.')
    r.table(['Track','Objective and budget','Purpose'],[
        ['Common comparison','CEC2014, 10D; NP 100 fixed; 100,000 FEs','Five methods and PEMS-DE/PGE-DE ablations'],
        ['DSPDE native','CEC2022, 10D; NP 50; 75,000 FEs','Paper comparison'],
        ['DLS-DE native','CEC2014, 10D; NP 182 to 4; 100,000 FEs','Paper comparison and native ablations'],
        ['PEMS-DE native','CEC2017, 10D; NP 60; 100,000 FEs','Paper comparison, official numbering']
    ],[.21,.47,.32],caption='Table 1. Experimental tracks. Each function and method has 20 independent runs.')
    r.p('The common comparison uses unmodified opfunu 1.0.4, CEC2014 F1 to F30, bounds [−100, 100], and identical initialization seeds. Function evaluations (FEs) include initialization and additional searches. DLS-DE population reduction is disabled only in this fixed-NP control. Its native reproduction remains separate.')
    r.h('1.2 Statistical analysis',2,toc=False)
    r.p('Tables report final best error, mean, sample standard deviation (Std), sample variance and within-function rank. Sample spread uses n−1. Error is the nonnegative difference from the declared optimum. Ranks use unrounded means with absolute tie tolerance 10⁻⁸ and relative tolerance 10⁻¹⁰; rounded printed means can therefore have different ranks.')
    r.p('Two-sided paired Wilcoxon tests match initialization seeds within each function. Holm correction uses separate families of 120 final comparisons and 120, 150, 120 and 90 DSPDE, DLS-DE, PEMS-DE and PGE-DE ablation tests. Mean ranks describe this fixed function set; they are not significance tests.')

    r.h('2 Methods',newpage=True)
    r.h('2.1 Source mechanisms',2,toc=False)
    r.p('DSPDE reassigns elite, ordinary and inferior roles by fitness. Linnik perturbations and social learning update the first two groups. A Gaussian mixture guides probabilistic escape for inferior individuals [1]. Linnik parameters and the escape convention are specified in Appendix A.')
    r.p('DLS-DE combines current-to-pbest mutation, an archive, direction learning, exponential crossover, displacement weighting, adaptive sampling and population reduction [2]. Its learning gate follows Algorithm 5, where rand exceeds 0.3.')
    r.p('PEMS-DE uses potential and elite guidance, multi-stage mutation learning, elite reinforcement and complementary learning [3]. Parent donors remain frozen within each generation. The archive and successful-parameter sets update after each individual, following Algorithm 4; parameter means update at generation end.')
    r.table(['Method','Key settings','Population'],[
        ['DE','F 0.5; CR 0.9; rand/1/bin','100 fixed'],
        ['DSPDE','Mixture 0.7/0.3; regularizer 10⁻⁶; Linnik α 1, v 0.5','50 native; 100 common'],
        ['DLS-DE','H 6; p 0.11; archive ratio 1.6; initial σ 0.05','182 to 4 native; 100 common'],
        ['PEMS-DE','Initial μF and μCR 0.5; ERS 0.3; reset every 20 generations','60 native; 100 common'],
        ['PGE-DE','CR 0.9; H 6; two-phase split 0.3; fixed σ 0.05','100 fixed']
    ],[.17,.58,.25],caption='Table 2. Main algorithm settings. Native source details and interventions appear in Appendix A.')

    r.h('2.2 Three strategy interfaces',toc=False)
    r.fig('00_algorithm_flow','Figure X2. PGE-DE execution and strategy interfaces. Potential-weighted guidance supplies the mutation target, two-phase sampling supplies F, and eligible inferior targets can receive an escape candidate. Every evaluated candidate consumes the common budget. Only ordinary successful candidates update F memory. Arrows describe the executed implementation, not inferred causal effects.')
    r.p('PGE-DE combines three borrowed mechanisms in a fixed-population current-to-guide backbone. Explicit interfaces connect the guide, scale-factor sampler and escape stage; source-to-team ablations measure each transferred effect. The configuration was fixed before the team comparison outcomes.')
    r.table(['Strategy and source','Interface in PGE-DE','Removal control'],[
        ['Potential guidance [3]','Fitness-improvement ranking selects a potential group and its weighted center','Random p-best guide, p 0.11'],
        ['Two-phase F [2]','Early success-rate sampling; later Cauchy sampling from memory','Later-phase sampling throughout'],
        ['Probabilistic escape [1]','Replaces an eligible inferior candidate before evaluation','Ordinary DE candidate retained']
    ],[.25,.47,.28],caption='Table 3. Source-to-combination mapping. Each removal changes one interface.')
    r.p('For target i, mutation uses the guide c, scale F and distinct donor indices r₁ and r₂. Binomial crossover uses CR 0.9 and at least one mutant coordinate. The trial is clipped to the box before evaluation.')
    r.equation([sub('v','i'),mr(' = '),sub('x','i'),mr(' + '),sub('F','i'),mr(' [ (c − '),sub('x','i'),mr(') + ('),sub('x','r₁'),mr(' − '),sub('x','r₂'),mr(') ]')],1)
    r.p('Progress q is consumed FEs divided by the budget. SR is the last generation’s fraction of successful ordinary candidates. The six-entry memory is M, ΔM equals mean(M) minus min(M), and u is uniform on [0, 1]. For q below 0.3,')
    r.equation([sub('F','i'),mr(' = clip [ 0.35 + '),frac('0.4 SR','0.1 + SR'),mr(' + sin(2πu) ΔM, 0.35, 0.65 ]')],2)
    r.p('Later positive Cauchy samples use a random memory entry, scale 0.05 and a cap of 1. The transferred sampler uses fixed scale and fitness-improvement weighting.')

    r.h('2.3 Executable procedure',toc=False)
    r.p('The following order specifies the combination and prevents extra evaluations from escaping the common budget.')
    for s in [
        '1. Initialize 100 solutions, evaluate them, and initialize F memory to 0.5.',
        '2. Rank fitness and recent relative improvement. Select the potential group and compute its fitness-weighted guide.',
        '3. Sample F using the current phase and construct ordinary mutation and binomial crossover candidates.',
        '4. Fit elite and global Gaussian models. Replace eligible inferior candidates by the escape proposal.',
        '5. Clip candidates to the bounds and evaluate only the remaining budget’s targets.',
        '6. Accept strict improvements. Update F memory using ordinary successful candidates only.',
        '7. Record the actual FEs and historical best; repeat until exactly 100,000 FEs.'
    ]:r.p(s,'Report Note')
    r.h('Guide and memory definitions',2,toc=False)
    r.p('Potential members are ranked by relative fitness improvement. Their number decreases from about 0.382NP through a cosine schedule. Weights are the selected group’s maximum fitness minus each member’s fitness; equal weights fall back to its best member.')
    r.equation([sub('M','next'),mr(' = '),frac([mr('Σ '),sub('w','i'),mr(' '),sub_sup('F','i','2')],[mr('Σ '),sub('w','i'),mr(' '),sub('F','i')]),
                mr(' ,    '),sub('w','i'),mr(' = '),frac([mr('Δ'),sub('f','i')],[mr('Σ Δ'),sub('f','j')])],3)

    r.h('3 Benchmark fidelity',newpage=True)
    r.fig('02_evaluator','Figure 1. Evaluator sensitivity of native DLS-DE means relative to published means. Each point summarizes 20 runs; the paper uses 51. The plotted ratio is log10[(mean + 10⁻⁸)/(paper mean + 10⁻⁸)]. The small offset displays zero-error functions and defines no equivalence margin. Full means and Std appear in Appendix B2.')
    r.p('A source audit identified nonmatching landscapes in 13 of 30 functions. On 660 probes, differences occurred at F17 to F27, F29 and F30. Official hybrid construction rotates before permutation; the inspected opfunu construction uses a different order. F29 also uses different component rotation matrices.')
    c={int(x['function']):x for x in csvrows('diagnostics/dls_evaluator_comparison.csv')}
    r.table(['Function','Paper mean','opfunu mean','C++ mean'],[[f'F{f:02d}',fmt(c[f]['paper_mean']),fmt(c[f]['opfunu_mean']),fmt(c[f]['cpp_mean'])] for f in [22,29,30]],[.16,.28,.28,.28],caption='Table 4. Matched optimizer, seeds, population schedule and FE budget; only the objective evaluator changes.')
    r.p('Independent reevaluation of all 600 saved C++ solutions matched their recorded objective values exactly [4]. On F29, the mean error changed from approximately 5.039 × 10⁶ under opfunu to 217.5 under the C++ evaluator, compared with the published 221.9. On F30, the corresponding means were approximately 21,570, 468.6 and 464.5. Benchmark construction therefore explains a substantial part of these literature gaps.')

    r.h('4 Component strategy evidence',newpage=True)
    r.fig('03_transfer','Figure 2. Full method versus defined replacement controls across 30 functions. Bars show wins, no difference detected (ND), and losses after Holm correction. The source PEMS-DE control replaces the potential–elite guidance module; the team control replaces only its weighted guide interface. Source families contain 120, 150 and 120 tests; the team family contains 90.')
    r.table(['Candidate','Source evidence','Selection judgment'],[
        ['Potential–elite module','8 wins, 20 ND, 2 losses in PEMS-DE','Module-level support; transfer uses its weighted-center interface'],
        ['Two-phase sampling','0 wins, 30 ND, 0 losses in DLS-DE','Exploratory choice; rank direction only'],
        ['Probabilistic escape','12 wins, 18 ND, 0 losses in DSPDE','Supported against the defined reset control']
    ],[.26,.37,.37],caption='Table 5. Unequal evidence strength behind the frozen selection.')
    r.p('The PEMS-DE source control replaces the potential center, p-best and elite center with the global best and clears potential membership, which also changes complementary learning. Its result concerns that complete guidance module. PGE-DE transfers only the potential-group weighted center.')
    r.p('The two-phase sampler was selected for its descriptive rank improvement and compatible F interface. DSPDE escape was tested against random reset in its source experiment and ordinary DE in the team experiment. Pre-existing single-paper experiments informed the frozen choice; the corrected PEMS-DE results evaluate it under the final protocol.')

    r.h('4.1 Candidate strategies and controls',newpage=True,toc=False)
    candidates=[
        ('pems','PEMS_no_peg','PEMS guidance','Global-best guide and elite centers; clear membership','Transfer weighted center'),
        ('pems','PEMS_no_mml','PEMS MML','Use one guide-plus-archive mutation throughout','Retain common DE backbone'),
        ('pems','PEMS_no_ers','PEMS ERS','Disable elite reinforcement','No detected gain'),
        ('pems','PEMS_no_cls','PEMS CLS','Disable complementary learning','Not transferred; additional search stage'),
        ('dls','no_learning','DLS learning','Disable learned direction','Retain ordinary differences'),
        ('dls','no_two_phase','DLS phase','Use later-phase F sampling throughout','Transfer F interface'),
        ('dls','fixed_sigma','DLS sigma','Hold Cauchy scale at 0.05','Use fixed transfer scale'),
        ('dls','fitness_weights','DLS weights','Use fitness gains in the memory update','Transfer memory convention'),
        ('dls','binomial','DLS crossover','Replace exponential with binomial crossover','Retain binomial backbone'),
        ('dsp','without_escape','DSP escape','Replace model escape with uniform reset','Transfer escape candidate'),
        ('dsp','without_linnik','DSP Linnik','Replace elite proposals with rand/1/bin','Retain ordinary DE mutation'),
        ('dsp','without_social','DSP social','Replace ordinary proposals with rand/1/bin','Control wins on 11 functions'),
        ('dsp','frozen_roles','DSP roles','Freeze initial group membership','Keep dynamic target ranking')]
    counts={stem:{x['comparison']:x for x in csvrows(stem+'_ablation_comparison_counts.csv')} for stem in ['pems','dls','dsp']}
    selection_rows=[]
    for stem,key,label,control,decision in candidates:
        item=counts[stem][key]
        outcome='/'.join(item[k] for k in ['reference_wins','no_difference_detected','reference_losses'])
        selection_rows.append([label,control,outcome,decision])
    r.table(['Strategy','Replacement control','W/ND/L','Integration decision'],selection_rows,[.19,.36,.13,.32],size=9.2,
            caption='Table 5a. All source-strategy controls. W/ND/L is full method versus its control within each recorded family.')
    r.p('CLS has the same 8/20/2 source count as the complete guidance-module control. The combination uses the guide as its mutation target and excludes the additional CLS search stage. Social learning had 0/19/11, favoring its DE replacement; the two-phase control had 0/30/0. These results support a compact, testable combination rather than selecting every source mechanism.', 'Report Note')

    r.h('5 Comparative performance',newpage=True)
    r.fig('01_performance','Figure 3. Common CEC2014 comparison. All five methods use 10D, fixed NP 100, 100,000 FEs and 20 runs per function. (a) Average within-function mean-error rank over the fixed 30-function set; no sampling interval is implied. (b) PGE-DE paired Wilcoxon outcomes after Holm correction over 120 tests. DLS-DE is the fixed-NP control throughout this figure.')
    r.p('PGE-DE achieved 11 corrected wins against basic DE, with seven losses, demonstrating useful gains on selected functions. Across all five methods, DLS-DE (fixed NP) had the lowest average rank, followed by PEMS-DE; PGE-DE ranked fourth with mean rank 3.333. The pairwise results locate its gains, while average rank measures its position across the complete comparison.')
    r.p('Corrected win counts describe pairwise evidence on individual functions. Average rank summarizes ordering across all five methods, including functions without detected pairwise differences.')
    r.h('Function families',2,toc=False)
    r.p('CEC2014 separates unimodal F1 to F3, basic multimodal F4 to F16, hybrid F17 to F22 and composition F23 to F30. The latter groups include the evaluator-sensitive landscapes. Common-track comparisons remain internally matched, while their scope is the specified opfunu implementation.')

    r.h('5.1 Seed distributions and heterogeneity',newpage=True,toc=False)
    r.fig('04_distributions','Figure 4. Final errors for every seed in two diagnostic examples. Points show all 20 runs per condition. Boxes show median and quartiles; whiskers extend to observations within 1.5 interquartile ranges. F11 and F29 are the largest absolute TEAM-versus-DE mean gain and loss, selected post hoc. The without-guidance condition is an ablation, not a newly validated replacement.')
    lookup={(int(x['function']),x['algorithm']):x for x in csvrows('final_statistics.csv')+csvrows('team_ablation_statistics.csv')}
    r.table(['Function','DE mean','PGE-DE mean','Without guidance'],[
        [f'F{f:02d}']+[fmt(lookup[(f,a)]['mean']) for a in ['DE','TEAM','TEAM_no_peg']] for f in [11,29]
    ],[.16,.28,.28,.28],caption='Table 6. Mean final errors for the displayed examples. Precise source values are retained in CSV.')
    r.p('The distributions show that the combination’s benefits are not uniform across functions or seeds. Removing guidance lowered both displayed mean errors, but the corrected team tests did not detect a difference on either example. Across all 30 functions, replacing the weighted center improved F08, F10, F19 and F22 after Holm correction. The two-phase and escape replacements produced no detected differences in the team comparison.')
    r.p('The full seed distributions complement the best-run convergence curves for all 30 functions in Appendix H.')

    r.h('6 Mechanistic interpretation',newpage=True)
    r.fig('05_telemetry','Figure 5. Observation-only replays of all 20 PGE-DE and without-guidance seeds on F11 and F29. Lines show medians; bands show interquartile ranges. Diversity is the root mean coordinate variance divided by the bound width 200; F29 diversity ticks use 10⁻⁴ units. Boundary occupancy counts coordinates within 10⁻¹⁰ of a bound. All 80 replays exactly reproduced the stored solutions, values and histories.')
    r.p('On F11, final median diversity was 0.125 with guidance and 0.144 without it. The shared guide accompanies a more concentrated final population in these matched replays.')
    r.p('On F29, both variants converged to concentrated populations with 70% median boundary occupancy. The common boundary pattern is shared by the two observed variants on this evaluator-sensitive landscape.')

    r.h('7 Conclusions',newpage=True)
    r.p('Three DE reconstructions, component controls and a frozen combination establish a reproducible account of strategy transfer. Source controls support probabilistic escape and the complete potential–elite guidance module in their recorded contexts. In the common protocol, PGE-DE delivers 11 corrected wins against basic DE and ranks fourth among five methods, locating its strengths at the function level.')
    r.p('The evaluator audit identifies a second decisive result: benchmark construction explains a substantial part of the DLS-DE literature gap on F29 and F30. Exact reevaluation of 600 saved C++ solutions links this conclusion to inspectable numerical evidence; the reproduction tables retain the accompanying spread and implementation settings.')
    r.p('Component tests and population traces connect implementation choices with observed performance. The source potential–elite module benefited PEMS-DE on several functions, whereas its transferred weighted guide did not retain that advantage in the combined backbone.')
    r.h('References')
    for ref in [
        '[1] Qu C, Yuan J, Zhang L, Zhang X, Huang Z. DSPDE: A synergistic integration of dynamic stratification and probabilistic escape for enhanced differential evolution optimization. Swarm and Evolutionary Computation 104 (2026), 102380. doi:10.1016/j.swevo.2026.102380.',
        '[2] Chen J, Meng Z. An Adaptive Differential Evolution Algorithm with Exponential Crossover Based on a Learning Strategy Within the Difference Vector. Swarm and Evolutionary Computation 100 (2026), 102247. doi:10.1016/j.swevo.2025.102247.',
        '[3] Sahu D, Gupta S. Adaptive differential evolution with potential-elite guidance and multi-stage learning for numerical optimization and feature selection. Swarm and Evolutionary Computation 107 (2026), 102435. doi:10.1016/j.swevo.2026.102435.',
        '[4] Liang JJ and CEC2014 benchmark contributors. CEC2014 C test-function source and input data. Retained official archive from github.com/P-N-Suganthan/CEC2014, cec14-c-code.zip. Source hash and portability changes are recorded with the independent audit.'
    ]:r.p(ref,'Report Note')

    r.h('Appendix A Reproduction details',newpage=True)
    r.p('The formal delivery contains 7,200 common CEC2014 runs, 580 corrected native PEMS-DE runs and 8,280 retained native/source-ablation DSPDE and DLS-DE runs. It additionally includes 600 retained C++ evaluator-control runs, 80 exact telemetry replays and 40 reference-evaluator replays. Replays are not independent observations; reused full-method records are counted once. Small-budget smoke runs are excluded.')
    r.p('All 7,780 newly generated formal solutions passed saved-solution, budget and history checks. The 4,200 retained DLS-DE records passed reevaluation under NumPy 2.3.5; the 4,080 retained DSPDE records passed under NumPy 1.26.4. Five selected full-budget runs replayed exactly.')
    r.p('The independent CEC2014 audit compiles retained source with two Linux portability changes: removing an unused Windows header and correcting five double scanning specifiers. All 600 saved solution values matched exactly. Full-budget replays of all 20 F29 and F30 seeds agreed in final values within 3 × 10⁻⁸; histories were not bit-identical. The original source remains unchanged.')
    r.p('DSPDE uses Linnik α 1 and v 0.5 as reconstruction choices. Its source comparison uses NP 50 and 75,000 FEs; the Table 7 dimension remains unresolved. Native DLS-DE uses H 6, p 0.11, archive ratio 1.6, λ 0.1, stagnation threshold 30, τ 0.3 and initial σ 0.05.')
    r.p('PEMS-DE uses NP 6D, initial μF and μCR 0.5, ERS 0.3, global/individual stagnation thresholds 5/20, learning rate 0.1 and reset period 20. Original-condition reproduction uses unchanged CEC2017-py through an opfunu interface adapter, official F1 and F3 to F30. It is distinct from unmodified opfunu CEC2017 class numbering.')
    r.p('DLS-DE repairs bounds by parent-bound midpoint and accepts ties. DE, DSPDE and PGE-DE clip and require strict improvement; PEMS-DE clips and accepts ties. PEMS-DE complementary learning can replace stagnant individuals unconditionally; its historical best is stored separately.')
    r.p('Native DSPDE ablations retain NP 50 and 75,000 FEs. Native DLS-DE ablations retain population reduction and 100,000 FEs; their DE baseline has fixed NP 182. PEMS-DE and PGE-DE ablations use the common NP 100 setting. Rank values must be read within their own comparison family.','Report Note')

    for label,filename in [('B1 DSPDE','dsp_paper_comparison.csv'),('B2 DLS-DE','dls_paper_comparison.csv'),('B3 PEMS-DE','pems_paper_comparison.csv')]:
        r.h('Appendix '+label+' original condition results',newpage=True)
        r.p('Paper values are transcribed source-table summaries. Our values use 20 independent runs. Published DLS-DE and PEMS-DE summaries use 51 runs. These descriptive comparisons do not constitute equivalence tests. DSPDE reports objective values; DLS-DE and PEMS-DE report errors.','Report Note')
        data=csvrows(filename)
        if label.startswith('B2'):
            native={int(x['function']):x for x in csvrows('dls_native_statistics.csv')}
            rows=[[int(x['function']),fmt(native[int(x['function'])]['best']),fmt(x['paper_mean']),fmt(x['opfunu_mean']),fmt(x['opfunu_std']),fmt(x['cpp_mean']),fmt(x['cpp_std']),fmt(x['paper_std'])] for x in csvrows('diagnostics/dls_evaluator_comparison.csv')]
            r.table(['F','opfunu\nBest','Paper\nmean','opfunu\nmean','opfunu\nStd','C++\nmean','C++\nStd','Paper\nStd'],rows,[.05]+[.95/7]*7,caption='Table B2. Native DLS-DE statistics under both evaluators, with published means and spread.')
            r.p('For F29, the C++ mean 217.5 is near the paper mean 221.9, but Std 20.19 remains much larger than 0.3122. Thus mean proximity does not establish replicated stability. The complete opfunu Std and all evaluator differences remain in the supplied CSV.','Report Note')
        else:
            rows=[[x['function'],fmt(x['reproduced_best']),fmt(x['paper_mean']),fmt(x['reproduced_mean']),fmt(x['paper_std']),fmt(x['reproduced_std']),fmt(x['mean_difference'])] for x in data]
            r.table(['F','Our Best','Paper mean','Our mean','Paper Std','Our Std','Difference'],rows,[.05]+[.95/6]*6,size=10 if label.startswith('B1') else 9,caption='Table '+label.split()[0]+'. Difference is reproduced mean minus published mean.')
            if label.startswith('B1'):
                r.p('Raw objective biases can conceal large error differences. DSPDE F10 has paper mean 2500.2 and our mean 2635.7, while the optimum is 2500. The corresponding errors are about 0.2 and 135.7. The source-table dimension and unspecified choices prevent an exact reproduction claim.','Report Note')
            else:
                r.p('PEMS-DE F30 has mean error 82,162.5 and median 442.2 across 20 runs, with a worst error of 817,640. The large mean is sensitive to rare failures. The paper mean 16,430 and Std 114,400 also show high spread; unequal samples do not identify its cause.','Report Note')

    labels={'DE':'DE','de':'DE (NP 182)','DSPDE':'DSPDE','DLSDE':'DLS-DE fixed NP','PEMSDE':'PEMS-DE','TEAM':'PGE-DE',
            'PEMS_no_peg':'Without PEG','PEMS_no_mml':'Without MML','PEMS_no_ers':'Without ERS','PEMS_no_cls':'Without CLS',
            'TEAM_no_peg':'Without PEG','TEAM_no_phase':'Without phase','TEAM_no_escape':'Without escape',
            'without_escape':'Without escape','without_linnik':'Without Linnik','without_social':'Without social','frozen_roles':'Fixed roles',
            'dls_de':'DLS-DE native','no_learning':'Without learning','no_two_phase':'Without phase','fixed_sigma':'Fixed sigma','fitness_weights':'Fitness weights','binomial':'Binomial'}
    groups=[('C Five algorithm statistics','final',[(1,8),(9,16),(17,23),(24,30)],'CEC2014, 10D; fixed NP 100; 100,000 FEs.'),
            ('D PEMS-DE ablations','pems_ablation',[(1,8),(9,16),(17,23),(24,30)],'CEC2014, 10D; fixed NP 100; 100,000 FEs. PEG replaces the potential–elite module as defined in Table 5a; MML is multi-stage mutation, ERS elite reinforcement and CLS complementary learning.'),
            ('E PGE-DE ablations','team_ablation',[(1,10),(11,20),(21,30)],'CEC2014, 10D; fixed NP 100; 100,000 FEs. Phase denotes the two-phase F sampler.'),
            ('F DSPDE ablations','dsp_ablation',[(i,i+5) for i in range(1,31,6)],'CEC2014, 10D; NP 50; 75,000 FEs. Without escape uses uniform reset. Without Linnik/social replaces the elite/ordinary proposals with rand/1/bin (F 0.5, CR 0.9). Fixed roles retains initial membership.'),
            ('G DLS-DE native ablations','dls_ablation',[(i,i+5) for i in range(1,31,6)],'CEC2014, 10D; native NP 182 to 4; 100,000 FEs. DE uses fixed NP 182. Phase denotes the two-phase F sampler.')]
    for title,stem,chunks,condition in groups:
        data=csvrows(stem+'_statistics.csv')
        for index,(first,last) in enumerate(chunks,1):
            r.h(f'Appendix {title} F{first:02d} to F{last:02d}',newpage=True)
            r.p(condition+' Each row summarizes 20 runs. Lower rank is better within this family; Std and variance use n−1. Bold means mark the lowest rank, including ties.','Report Note')
            subset=[x for x in data if first<=int(x['function'])<=last]
            rows=[[f"F{int(x['function']):02d}",labels[x['algorithm']],fmt(x['best']),fmt(x['mean']),fmt(x['std']),fmt(x['variance']),f"{float(x['rank']):.1f}"] for x in subset]
            minimum={f:min(float(x['rank']) for x in subset if int(x['function'])==f) for f in range(first,last+1)}
            bold={i for i,x in enumerate(subset) if float(x['rank'])==minimum[int(x['function'])]}
            r.table(['F','Algorithm','Best','Mean','Std','Variance','Rank'],rows,[.065,.23,.15,.15,.155,.17,.08],
                    groups=[int(x['function']) for x in subset],highlight=bold,size=8.8,
                    caption=f'Table {title[0]}{index}. Final error statistics F{first:02d} to F{last:02d}.')

    for i in range(1,31,2):
        r.h(f'Appendix H Convergence curves F{i:02d} and F{i+1:02d}',newpage=True)
        r.fig(f'curves_{i:02d}_{i+1:02d}',f'Figure H{(i+1)//2}. Best final run of 20 for each method on F{i:02d} and F{i+1:02d}. CEC2014, 10D, fixed NP 100, 100,000 FEs. Actual checkpoints; no smoothing. The vertical axis is the original objective on a log scale. Selected run IDs and source data are supplied.')
    integrate(r,TITLES,FIGURES,TEXT)
    save(r)
    print(json.dumps(dict(headings=len(TITLES),figures=len(FIGURES),author='殷明骏'),ensure_ascii=False))

if __name__=='__main__':
    pages=json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv)>1 else None
    main(pages)
