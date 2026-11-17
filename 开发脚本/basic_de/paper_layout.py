"""Paper body typography with an unchanged retained cover. Author: 殷明骏."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from lxml import etree

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def enable_paper_body(report):
    """Add body-only styles; existing styles used on the cover are untouched."""
    doc=report.doc
    for section in doc.sections:
        for paragraph in section.header.paragraphs:
            for run in paragraph.runs:run.font.color.rgb=RGBColor(0,0,0)
    for name,size,bold in [('Paper Body',12,False),('Paper Note',9.5,False),
                           ('Paper Caption',9.5,False),('Paper Abstract',11,False),
                           ('Paper Keywords',9.5,False),('Paper Contents',9.5,False),
                           ('Paper Heading 1',14,True),('Paper Heading 2',12,True)]:
        st=doc.styles[name] if name in doc.styles else doc.styles.add_style(name,1)
        st.font.name='Times New Roman';st.font.size=Pt(size);st.font.bold=bold
        st.font.color.rgb=RGBColor(0,0,0)
        pf=st.paragraph_format
        pf.first_line_indent=Pt(0);pf.left_indent=Pt(0);pf.right_indent=Pt(0)
        pf.space_before=Pt(0);pf.space_after=Pt(5)
        pf.line_spacing=1.18 if name=='Paper Body' else 1.10
        pf.widow_control=True
        if 'Heading' in name:
            pf.keep_with_next=True;pf.space_before=Pt(10);pf.space_after=Pt(5)
            level=OxmlElement('w:outlineLvl');level.set(qn('w:val'),'0' if name.endswith('1') else '1')
            st._element.get_or_add_pPr().append(level)
    original_p,original_h,original_table=report.p,report.h,report.table
    original_equation=report.equation
    report._paper_contents=False

    def paragraph(text,style='Report Body',keep=False):
        target={'Report Body':'Paper Body','Report Note':'Paper Note',
                'Report Caption':'Paper Caption'}.get(style,style)
        if report._paper_contents and style=='Report Note':target='Paper Contents'
        p=original_p(text,style if style.startswith('Report ') else 'Report Note',keep)
        p.style=doc.styles[target]
        p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY if target=='Paper Body' else WD_ALIGN_PARAGRAPH.LEFT
        if target=='Paper Body':p.paragraph_format.keep_together=True
        size=12 if target=='Paper Body' else 11 if target=='Paper Abstract' else 9.5
        for run in p.runs:run.font.size=Pt(size);run.font.color.rgb=RGBColor(0,0,0)
        if target=='Paper Keywords':
            for run in p.runs:run.italic=True
        if target=='Paper Caption':
            p.paragraph_format.space_before=Pt(1);p.paragraph_format.space_after=Pt(5)
            match=re.match(r'((?:Figure|Table)\s+[^.]+\.)(.*)',text)
            if match:
                p.clear()
                a=p.add_run(match[1]);a.bold=True;a.font.size=Pt(9.5)
                b=p.add_run(match[2]);b.font.size=Pt(9.5)
        return p

    def heading(text,level=1,newpage=False,toc=True):
        report._paper_contents=(text=='Contents')
        if re.match(r'^\d',text):newpage=newpage or bool(text.startswith('1 '))
        p=original_h(text,level,newpage,toc)
        p.style=doc.styles['Paper Heading '+str(level)]
        p.paragraph_format.space_before=Pt(0 if newpage else 10)
        p.paragraph_format.space_after=Pt(5)
        if text=='Contents':p.paragraph_format.space_before=Pt(13)
        return p

    def table(*args,**kwargs):
        if kwargs.get('size',9)<9:kwargs['size']=9
        t=original_table(*args,**kwargs)
        for edge in t._tbl.tblPr.findall('.//'+qn('w:tblBorders')+'/*'):
            edge.set(qn('w:color'),'444444');edge.set(qn('w:sz'),'4')
            edge.set(qn('w:val'),'single' if edge.tag in [qn('w:top'),qn('w:bottom')] else 'nil')
        margins=t._tbl.tblPr.find(qn('w:tblCellMar'))
        if margins is not None:
            for edge in margins:
                edge.set(qn('w:w'),'24' if edge.tag in [qn('w:top'),qn('w:bottom')] else '55')
        for i,row in enumerate(t.rows):
            for j,cell in enumerate(row.cells):
                shades=cell._tc.get_or_add_tcPr().findall(qn('w:shd'))
                for shade in shades:
                    old=shade.get(qn('w:fill'))
                    shade.set(qn('w:fill'),'FFFFFF')
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.color.rgb=RGBColor(0,0,0)
                        if i==0 or j==0:run.bold=True
                if i==1 or (len(t.rows)==31 and i in [4,17,23]):
                    borders=OxmlElement('w:tcBorders')
                    top=OxmlElement('w:top');top.set(qn('w:val'),'single')
                    top.set(qn('w:color'),'777777');top.set(qn('w:sz'),'3')
                    borders.append(top);cell._tc.get_or_add_tcPr().append(borders)
        if len(t.rows)<=15:
            for row in list(t.rows)[:-1]:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:paragraph.paragraph_format.keep_with_next=True
        return t

    def equation(*args,**kwargs):
        doc.paragraphs[-1].paragraph_format.keep_with_next=True
        original_equation(*args,**kwargs)
        p=doc.paragraphs[-1];p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before=Pt(6);p.paragraph_format.space_after=Pt(8)
        p.paragraph_format.line_spacing=1.1

    report.p=paragraph;report.h=heading;report.table=table;report.equation=equation


def preserve_cover(report,root,width):
    root=Path(root);ns={'w':W}
    body=report.doc._element.body
    start=next(i for i,n in enumerate(body) if ''.join(t.text or '' for t in n.iter(qn('w:t')))=='Abstract')
    contribution_start=next(i for i,n in enumerate(body) if ''.join(t.text or '' for t in n.iter(qn('w:t')))=='Contributions')
    contributions=[deepcopy(n) for n in list(body)[contribution_start:start]]
    for node in list(body)[:start]:body.remove(node)
    cover=etree.fromstring((root/'source/cover_preserved.xml').read_bytes())
    preview=next(i for i,n in enumerate(cover) if ''.join(t.text or '' for t in n.iter(qn('w:t')))=='Basic DE at a glance')
    protected=list(cover)[:preview]
    for i,node in enumerate(protected+contributions):body.insert(i,deepcopy(node))
    for p,_,_ in report.contents:
        p.paragraph_format.space_before=Pt(0);p.paragraph_format.space_after=Pt(3)
        p.paragraph_format.line_spacing=1.1
        p.paragraph_format.tab_stops.clear_all()
        p.paragraph_format.tab_stops.add_tab_stop(Inches(width-.05),WD_TAB_ALIGNMENT.RIGHT,WD_TAB_LEADER.DOTS)
    actual=[hashlib.sha256(etree.tostring(n,method='c14n',exclusive=True)).hexdigest() for n in list(body)[:len(protected)]]
    expected=json.loads((root/'source/cover_preserved.json').read_text())['node_sha256'][:len(protected)]
    assert actual==expected,'Protected cover fields changed'


def restore_pdf_cover(document,root):
    """Use the exact retained cover page, leaving the new body in place."""
    import fitz
    with fitz.open(Path(root)/'source/cover_preserved.pdf') as source:
        document.delete_page(0)
        document.insert_pdf(source,from_page=0,to_page=0,start_at=0)
