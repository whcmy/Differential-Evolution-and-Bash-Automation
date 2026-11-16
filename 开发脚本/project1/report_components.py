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


ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'
DOC=OUT/'Project1_Report.docx'
REFERENCE=ROOT/'source/template/Project2_Report_reference.docx'
WIDTH=6.9
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
        self.doc=Document(REFERENCE);self.body=self.doc._element.body
        nodes=list(self.body)
        start=next(i for i,n in enumerate(nodes) if 'Project 2 at a glance' in ''.join(n.itertext()))
        for n in nodes[start:]:
            if n.tag!=qn('w:sectPr'):self.body.remove(n)
        for p in self.doc.paragraphs:
            for run in p.runs:
                if 'Project 2 Differential Evolution' in run.text:
                    run.text=run.text.replace('Project 2 Differential Evolution','Project 1 Basic Differential Evolution')
        for section in self.doc.sections:
            for area in [section.header,section.footer,section.first_page_header]:
                for p in area.paragraphs:
                    for run in p.runs:
                        run.text=run.text.replace('PROJECT 2','PROJECT 1').replace('Project 2','Project 1')
        self.pages=pages or {};self.id=500;self.contents=[];self.table_id=0

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
            if i==0:trp.append(OxmlElement('w:tblHeader'))
        self.p('','Report Note')
        TEXT.append('| '+' | '.join(headers)+' |');TEXT.append('| '+' | '.join(['---']*n)+' |')
        TEXT.extend('| '+' | '.join(map(str,r))+' |' for r in rows);TEXT.append('')
        return t

    def fig(self,name,caption,width=WIDTH):
        p=self.doc.add_paragraph();p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.left_indent=Pt(0);p.paragraph_format.right_indent=Pt(0);p.paragraph_format.space_before=Pt(4);p.paragraph_format.space_after=Pt(6);p.paragraph_format.keep_with_next=True
        snap=OxmlElement('w:snapToGrid');snap.set(qn('w:val'),'0');p._p.get_or_add_pPr().append(snap)
        p.add_run().add_picture(str(OUT/'figures'/f'{name}.png'),width=Inches(width))
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
