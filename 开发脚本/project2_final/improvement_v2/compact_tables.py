"""Pivot complete statistics into paper-style comparison matrices. Author: 殷明骏."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import re
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
import fitz
ROOT=Path(__file__).resolve().parents[1]
HEADER=['F','Algorithm','Best','Mean','Std','Variance','Rank']
TITLES=['DSPDE component statistics','DLS-DE native component statistics','PEMS-DE component statistics',
        'Independent six-method confirmation statistics','Independent DC-DE ablation statistics',
        'Historical five-algorithm comparison','Historical PGE-DE ablation statistics']


def text(node):return ''.join(t.text or '' for t in node.iter(qn('w:t')))


def compact(value):
    return re.sub(r'e([+-])0*(\d+)',lambda m:'e'+('-' if m[1]=='-' else '')+m[2],value)


def cell_values(cell):
    value=''.join((n.text or '') if n.tag==qn('w:t') else '\n' if n.tag in [qn('w:br'),qn('w:cr')] else '' for n in cell.iter())
    return re.findall(r'\d+(?:\.\d+)?(?:[eE][+−-]?\d+)?',value)


def decode_table(node):
    rows=node.findall(qn('w:tr'));headers=[text(c) for c in rows[0].findall(qn('w:tc'))]
    result=[]
    if headers==HEADER:
        return [tuple(text(c) for c in row.findall(qn('w:tc'))) for row in rows[1:]]
    if headers and headers[0]=='F' and len(headers)>2 and 'Algorithm' not in headers:
        for row in rows[1:]:
            cells=row.findall(qn('w:tc'));fid=text(cells[0])
            if not re.fullmatch(r'F\d{2}',fid):return []
            for algorithm,cell in zip(headers[1:],cells[1:]):
                values=cell_values(cell)
                if len(values)!=5:return []
                nums=[float(x.replace('−','-')) for x in values]
                result.append((fid,algorithm,*['0' if x==0 else f'{x:.3e}' for x in nums[:4]],f'{nums[-1]:.1f}'))
    return result


def make_matrix(records):
    algorithms=list(dict.fromkeys(r[1] for r in records));functions=list(dict.fromkeys(r[0] for r in records))
    assert len(functions)==30 and functions==[f'F{i:02d}' for i in range(1,31)]
    lookup={(r[0],r[1]):r for r in records};assert len(lookup)==len(records)==30*len(algorithms)
    width=6.8504;first=.34;numeric=(width-first)/len(algorithms)
    two_width=max(fitz.get_text_length(f'{compact(r[2])};{compact(r[3])}({compact(r[4])})',fontname='Times-Roman',fontsize=8) for r in records)
    lines=4 if len(algorithms)>=7 else 2 if two_width<=numeric*72-3 else 3
    temp=Document();table=temp.add_table(rows=1,cols=1+len(algorithms));table.autofit=False
    widths=[first]+[numeric]*len(algorithms)
    for col,w in zip(table.columns,widths):col.width=Inches(w)
    for cell,label in zip(table.rows[0].cells,['F']+algorithms):cell.text=label
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
    for fid in functions:
        row=table.add_row();row.cells[0].text=fid
        best_rank=min(float(lookup[fid,a][-1]) for a in algorithms)
        for cell,a in zip(row.cells[1:],algorithms):
            r=lookup[fid,a];b,mean,sd,var,rank=[compact(x) for x in r[2:]]
            p=cell.paragraphs[0]
            p.add_run(b)
            p.add_run(';' if lines==2 else '\n')
            run=p.add_run(mean);run.bold=float(rank)==best_rank
            p.add_run(('\n' if lines==4 else '')+'('+sd+')\n'+var+' [')
            run=p.add_run(rank);run.bold=float(rank)==best_rank
            p.add_run(']')
    props=table._tbl.tblPr
    borders=OxmlElement('w:tblBorders')
    for edge in ['top','bottom','left','right','insideH','insideV']:
        e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single' if edge in ['top','bottom','insideH'] else 'nil');e.set(qn('w:sz'),'5' if edge in ['top','bottom'] else '2');e.set(qn('w:color'),'222222' if edge in ['top','bottom'] else 'BBBBBB');borders.append(e)
    props.append(borders)
    margins=OxmlElement('w:tblCellMar')
    for edge in ['top','bottom','left','right']:
        e=OxmlElement('w:'+edge);e.set(qn('w:w'),'8' if edge in ['top','bottom'] else '20');e.set(qn('w:type'),'dxa');margins.append(e)
    props.append(margins)
    for i,row in enumerate(table.rows):
        row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        for cell,w in zip(row.cells,widths):
            cell.width=Inches(w);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for p in cell.paragraphs:
                p.alignment=WD_ALIGN_PARAGRAPH.CENTER
                pf=p.paragraph_format;pf.space_before=pf.space_after=Pt(0);pf.line_spacing=Pt(9)
                pf.keep_with_next=i==0;pf.widow_control=False
                for run in p.runs:
                    run.font.name='Times New Roman';run.font.size=Pt(8);run.font.color.rgb=RGBColor(0,0,0)
                    if i==0:run.bold=True
    return deepcopy(table._tbl),lines,algorithms


def apply(j):
    body=j.doc._element.body;items=[];groups=[]
    for node in list(body):
        if node.tag!=qn('w:tbl'):continue
        rows=decode_table(node)
        if not rows:continue
        cap=node.getprevious()
        assert re.match(r'^Table \d+\.',text(cap)),text(cap)
        entry=dict(node=node,caption=cap,number=int(re.match(r'^Table (\d+)',text(cap))[1]),rows=rows)
        items.append(entry)
        if rows[0][0]=='F01':groups.append([])
        groups[-1].append(entry)
    assert len(groups)==7
    expected=Counter(r for entry in items for r in entry['rows']);assert sum(expected.values())==1110
    group_meta=[];removed_to_first={}
    for entries,title in zip(groups,TITLES):
        records=[r for entry in entries for r in entry['rows']]
        matrix,lines,algorithms=make_matrix(records);first=entries[0]
        first['node'].addprevious(matrix)
        for entry in entries:
            removed_to_first[entry['number']]=first['number'];body.remove(entry['node'])
            if entry is not first:body.remove(entry['caption'])
        description=('Each cell: Best; Mean (SD), then Variance [Rank].' if lines==2 else 'Each cell: Best; Mean; (SD); Variance [Rank], on four lines.' if lines==4 else 'Each cell: Best; Mean (SD); Variance [Rank], on three lines.')
        cap=first['caption'];ts=list(cap.iter(qn('w:t')));ts[0].text=f"Table {first['number']}. {title}, F01–F30. {description}"
        for t in ts[1:]:t.text=''
        group_meta.append(dict(title=title,original_tables=[e['number'] for e in entries],records=len(records),functions=30,algorithms=algorithms,cell_lines=lines))
    mapping={}
    captions=[n for n in body if n.tag==qn('w:p') and re.match(r'^Table \d+\.',text(n))]
    for new,node in enumerate(captions,1):mapping[int(re.match(r'^Table (\d+)',text(node))[1])]=new
    for old,first in removed_to_first.items():mapping[old]=mapping[first]
    for node in body:
        if node.tag!=qn('w:p'):continue
        s=text(node)
        if 'Table 7 dimension remains unresolved' in s:continue
        updated=re.sub(r'\bTable (\d+)\b',lambda m:'Table '+str(mapping[int(m[1])]),s)
        if updated!=s:
            ts=list(node.iter(qn('w:t')));ts[0].text=updated
            for t in ts[1:]:t.text=''
        if 'Bold Mean/Rank cells mark' in s:
            updated=text(node).replace('The following tables summarize every final-method and ablation run by function.','The following matrices summarize every final-method and ablation run by function.').replace('Bold Mean/Rank cells mark','Bold mean/rank entries mark')
            ts=list(node.iter(qn('w:t')));ts[0].text=updated
            for t in ts[1:]:t.text=''
    actual=Counter(r for n in body if n.tag==qn('w:tbl') for r in decode_table(n))
    assert actual==expected,'Pivot changed or lost statistical values'
    assert len(captions)==20
    from prose_revision import apply as revise_prose
    revise_prose(j.doc)
    # Regenerate matching editable Markdown from the final visible body.
    j.md=['# NUIST Experiment Report'];picture=0
    for node in body:
        if node.tag==qn('w:tbl'):
            from docx.table import Table
            rows=[[c.text.replace('\n','<br>') for c in row.cells] for row in Table(node,j.doc._body).rows]
            j.md.append('| '+' | '.join(rows[0])+' |\n| '+' | '.join('---' for _ in rows[0])+' |\n'+'\n'.join('| '+' | '.join(row)+' |' for row in rows[1:]))
        elif node.tag==qn('w:p'):
            if any(n.tag.endswith('}blip') for n in node.iter()):
                j.md.append(f'![Figure](figures/{j.figures[picture]}.png)');picture+=1
            value=''.join(n.text or '' for n in node.iter() if n.tag in [qn('w:t'),qn('m:t')])
            if value:j.md.append(value)
    assert picture==16
    manifest=dict(author='殷明骏',passed=True,original_statistical_records=1110,compact_function_rows=210,
                  original_tables=43,compact_tables=20,numeric_fields_retained=['Best','Mean','Std','Variance','Rank'],
                  all_printed_values_preserved=True,table_number_mapping=mapping,groups=group_meta)
    (ROOT/'output/compact_table_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
