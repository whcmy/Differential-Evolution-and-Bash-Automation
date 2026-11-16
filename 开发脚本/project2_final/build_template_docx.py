"""Populate retained report template and build editable final Word report.

Execute with the bundled document runtime. Author and last editor: 殷明骏.
"""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import tempfile
import zipfile
from zoneinfo import ZoneInfo
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from lxml import etree

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT/'source/template/实验报告模板.docx'
OUTPUT = ROOT/'output/Project2_Report.docx'
IDENTITY = ROOT/'protocol/report_identity.json'
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def set_run_text(run, value):
    for node in list(run):
        if node.tag != qn('w:rPr'):
            run.remove(node)
    for i, line in enumerate(value.split('\n')):
        if i:
            run.append(OxmlElement('w:br'))
        t = OxmlElement('w:t')
        t.set(qn('xml:space'), 'preserve')
        t.text = line
        run.append(t)


def append_text(paragraph_element, source_run, value):
    run = deepcopy(source_run)
    set_run_text(run, value)
    paragraph_element.append(run)
    return run


def plain_paragraph(proto, text, run_proto=None):
    paragraph = deepcopy(proto)
    runs = paragraph.findall(qn('w:r'))
    base = deepcopy(run_proto if run_proto is not None else runs[0]) if runs or run_proto is not None else OxmlElement('w:r')
    for node in list(paragraph):
        if node.tag != qn('w:pPr'):
            paragraph.remove(node)
    set_run_text(base, text)
    paragraph.append(base)
    return paragraph


def build(header_only=False):
    (ROOT/'template_work').mkdir(parents=True, exist_ok=True)
    identity = json.loads(IDENTITY.read_text())
    baseline = TEMPLATE.read_bytes()
    doc = Document(TEMPLATE)
    body = doc._element.body
    original = list(body.findall(qn('w:p')))
    original_title = etree.tostring(original[0], method='c14n')
    original_sect = etree.tostring(body.find(qn('w:sectPr')), method='c14n')
    heading_proto = deepcopy(original[8])
    body_proto = deepcopy(original[11])
    body_ppr = body_proto.find(qn('w:pPr'))
    if body_ppr is None:
        body_ppr = OxmlElement('w:pPr'); body_proto.insert(0, body_ppr)
    # Retain 1.5-line paragraph style; prevent the CJK fallback renderer from
    # expanding it to three document-grid rows per line. Header is untouched.
    snap = OxmlElement('w:snapToGrid'); snap.set(qn('w:val'), '0'); body_ppr.append(snap)
    widow = OxmlElement('w:widowControl'); widow.set(qn('w:val'), '1'); body_ppr.append(widow)
    # Original source instructions are blue. New substantive body is black;
    # paragraph/font geometry otherwise follows the retained body pattern.
    body_run = deepcopy(body_proto.findall(qn('w:r'))[0])
    rp = body_run.find(qn('w:rPr'))
    if rp is None:
        rp = OxmlElement('w:rPr'); body_run.insert(0, rp)
    color = rp.find(qn('w:color'))
    if color is None:
        color = OxmlElement('w:color'); rp.append(color)
    color.attrib.clear(); color.set(qn('w:val'), '000000')
    fonts = rp.find(qn('w:rFonts'))
    if fonts is None:
        fonts = OxmlElement('w:rFonts'); rp.insert(0, fonts)
    fonts.set(qn('w:ascii'), 'Times New Roman')
    fonts.set(qn('w:hAnsi'), 'Times New Roman')
    fonts.set(qn('w:eastAsia'), '宋体')
    # Course and experiment fields keep every original label/run format.
    append_text(original[1], original[1].findall(qn('w:r'))[0],
                f"  {identity['course_english']}")
    # A filled, nonzero-height connector keeps the retained rule visible in
    # converters that discard legacy zero-height shapes alongside inline images.
    rule_run = OxmlElement('w:r')
    rule_drawing = OxmlElement('w:drawing')
    wp_uri = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
    a_uri = 'http://schemas.openxmlformats.org/drawingml/2006/main'
    rule = deepcopy(next(original[0].iter('{'+wp_uri+'}anchor')))
    for axis, offset in [('H',1038225),('V',1300163)]:
        pos = rule.find('{'+wp_uri+'}position'+axis)
        pos.set('relativeFrom','page')
        pos.find('{'+wp_uri+'}posOffset').text = str(offset)
    rule.find('{'+wp_uri+'}extent').set('cy','9525')
    rule.find('{'+wp_uri+'}docPr').set('id','30001')
    rule.find('{'+wp_uri+'}docPr').set('name','Template rule compatibility')
    for child in list(rule):
        if etree.QName(child).localname in ['sizeRelH','sizeRelV']:
            rule.remove(child)
    sp = next(rule.iter('{http://schemas.microsoft.com/office/word/2010/wordprocessingShape}spPr'))
    sp.find('{'+a_uri+'}xfrm/{'+a_uri+'}ext').set('cy','9525')
    sp.find('{'+a_uri+'}prstGeom').set('prst','rect')
    for child in list(sp):
        if etree.QName(child).localname in ['noFill','ln','extLst']:
            sp.remove(child)
    fill = etree.SubElement(sp,'{'+a_uri+'}solidFill')
    etree.SubElement(fill,'{'+a_uri+'}srgbClr').set('val','000000')
    outline = etree.SubElement(sp,'{'+a_uri+'}ln')
    etree.SubElement(outline,'{'+a_uri+'}noFill')
    rule_drawing.append(rule); rule_run.append(rule_drawing); original[1].append(rule_run)
    append_text(original[2], original[2].findall(qn('w:r'))[0],
                ' Project 2 Differential Evolution')
    date = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d')
    p3runs = original[3].findall(qn('w:r'))
    set_run_text(p3runs[1], f'  {date}   ')
    append_text(original[3], p3runs[-1], f"  {identity['tutor_chinese']} / {identity['tutor_english']}")
    p4runs = original[4].findall(qn('w:r'))
    set_run_text(p4runs[1], f"  {identity['college_english']}    ")
    for run in p4runs[2:4]:
        set_run_text(run, '')
    set_run_text(p4runs[-1], f" {identity['class_english']}")
    name_proto = deepcopy(original[5])
    prior = original[5]
    for index, member in enumerate(identity['members']):
        p = original[5] if index == 0 else deepcopy(name_proto)
        if index:
            prior.addnext(p)
        runs = p.findall(qn('w:r'))
        set_run_text(runs[1], f" {member['chinese']}   ")
        append_text(p, runs[-1], ' '+member['student_id'])
        english = plain_paragraph(name_proto, '      '+member['english'], runs[0])
        p.addnext(english)
        prior = english
    # Only the explicitly free body region is replaced. Title, header rule,
    # original label paragraphs and section geometry remain retained source.
    for node in original[8:]:
        body.remove(node)
    def insert(element):
        body.insert(len(body)-1, element)
    def add_heading(value):
        p = plain_paragraph(heading_proto, value)
        ppr = p.find(qn('w:pPr'))
        num = ppr.find(qn('w:numPr')) if ppr is not None else None
        if num is not None:
            ppr.remove(num)
        # Source manual numbering is used because body categories may change.
        if ppr is not None:
            keep = OxmlElement('w:keepNext'); ppr.append(keep)
        insert(p)
    def add_body(value):
        paragraph = plain_paragraph(body_proto, value, body_run)
        if value.endswith(':'):
            paragraph.find(qn('w:pPr')).append(OxmlElement('w:keepNext'))
        insert(paragraph)
    if header_only:
        add_heading('1. Experimental objectives')
        add_body('Reproduce DSPDE, DLS-DE and PEMS-DE, evaluate their individual strategies, and combine selected strategies into PGE-DE. Compare the proposed combination with basic DE and the three paper algorithms under a common experimental protocol.')
        add_heading('2. Methods and implementation')
        add_body('The report will describe algorithm implementations, parameter settings, strategy sources and single-strategy ablation definitions.')
        add_heading('3. Results and analysis')
        add_body('Formal experiments are still running. Paper comparisons, ablation statistics, the five-algorithm comparison and convergence curves will be included after complete data validation.')
        add_heading('4. Conclusions')
        add_body('Conclusions will be based on the validated formal results.')
    else:
        markdown = (ROOT/'output/Project2_Report.md').read_text()
        start = markdown.index('## 1.')
        lines = markdown[start:].splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1; continue
            if line.startswith('## '):
                add_heading(line[3:])
                i += 1; continue
            if line.startswith('|'):
                matrix = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    values = [v.strip() for v in lines[i].strip().strip('|').split('|')]
                    if not all(re.fullmatch(r':?-+:?', v) for v in values):
                        matrix.append(values)
                    i += 1
                table = doc.add_table(rows=0, cols=len(matrix[0]))
                table.autofit = False
                width = (doc.sections[0].page_width-doc.sections[0].left_margin-doc.sections[0].right_margin)/914400
                weights = ([.28]+[(1-.28)/(len(matrix[0])-1)]*(len(matrix[0])-1)) if len(matrix[0]) > 2 else [.65,.35]
                if matrix[0][0] == 'F':
                    weights = [.08]+[.92/(len(matrix[0])-1)]*(len(matrix[0])-1)
                for j, column in enumerate(table.columns):
                    column.width = Inches(width*weights[j])
                for rindex, row in enumerate(matrix):
                    cells = table.add_row().cells
                    for j, value in enumerate(row):
                        cells[j].width = Inches(width*weights[j])
                        p = cells[j].paragraphs[0]
                        p.paragraph_format.space_after = Pt(1)
                        p.paragraph_format.space_before = Pt(1)
                        p.paragraph_format.line_spacing = 1
                        p.paragraph_format.keep_with_next = len(matrix) <= 8 and rindex < len(matrix)-1
                        p.paragraph_format.first_line_indent = Pt(0)
                        snap = OxmlElement('w:snapToGrid'); snap.set(qn('w:val'), '0')
                        p._p.get_or_add_pPr().append(snap)
                        run = p.add_run(value)
                        run.font.name = 'Times New Roman'
                        run.font.size = Pt(8)
                        run.bold = rindex == 0
                        if rindex == 0:
                            borders = OxmlElement('w:tcBorders')
                            bottom = OxmlElement('w:bottom')
                            bottom.set(qn('w:val'), 'single'); bottom.set(qn('w:sz'), '6')
                            bottom.set(qn('w:color'), '000000'); borders.append(bottom)
                            cells[j]._tc.get_or_add_tcPr().append(borders)
                    table.rows[-1]._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
                    if rindex == 0:
                        repeat = OxmlElement('w:tblHeader'); table.rows[0]._tr.get_or_add_trPr().append(repeat)
                # Native Word table, three horizontal rules, content width.
                pr = table._tbl.tblPr
                borders = OxmlElement('w:tblBorders')
                for edge in ('top', 'bottom', 'left', 'right', 'insideH', 'insideV'):
                    border = OxmlElement('w:'+edge)
                    border.set(qn('w:val'), 'single' if edge in ('top','bottom') else 'nil')
                    border.set(qn('w:sz'), '6'); border.set(qn('w:color'), '000000')
                    borders.append(border)
                pr.append(borders)
                insert(table._tbl)
                continue
            if line.startswith('未提供课程指定报告模板') or line.startswith('已检查两份课程说明'):
                i += 1; continue
            add_body(line)
            i += 1
        add_heading('G. Best run convergence curves')
        add_body('Each function shows the actual run with the lowest final objective value among 20 runs for each algorithm. The horizontal axis is the actual number of function evaluations and the vertical axis is the original objective value on a logarithmic scale. No smoothing is applied. Run identifiers, seeds and source data are included in the accompanying index.')
        width = doc.sections[0].page_width-doc.sections[0].left_margin-doc.sections[0].right_margin
        for fid in range(1, 31):
            p = doc.add_paragraph()
            p.paragraph_format.keep_with_next = True
            run = p.add_run(f'CEC2014 F{fid:02d}')
            run.font.name = 'Times New Roman'; run.font.size = Pt(12)
            p = doc.add_paragraph()
            picture = p.add_run().add_picture(str(ROOT/'output/curves'/f'F{fid:02d}.png'), width=width)
            # Keep new picture IDs away from the retained legacy shape IDs.
            picture._inline.docPr.set('id', str(10000+fid))
            picture._inline.docPr.set('name', f'Convergence F{fid:02d}')
            for node in picture._inline.iter():
                if node.tag == '{http://schemas.openxmlformats.org/drawingml/2006/picture}cNvPr':
                    node.set('id', str(20000+fid))
                    node.set('name', f'Convergence F{fid:02d}')
    doc.core_properties.author = identity['author']
    doc.core_properties.last_modified_by = identity['last_modified_by']
    doc.core_properties.title = 'Project2 Differential Evolution Experiment Report'
    doc.core_properties.subject = identity['student_id']
    doc.core_properties.comments = ''
    visible_text = ''.join(t.text or '' for t in body.iter(qn('w:t')))
    remaining_text = visible_text
    for name in [identity['tutor_chinese']]+[m['chinese'] for m in identity['members']]:
        remaining_text = remaining_text.replace(name, '')
    if re.search(r'[\u3400-\u9fff]', remaining_text):
        raise ValueError('Report contains Chinese text outside the explicitly permitted personal names')
    assert etree.tostring(body.find(qn('w:p')), method='c14n') == original_title
    assert etree.tostring(body.find(qn('w:sectPr')), method='c14n') == original_sect
    OUTPUT.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT/'template_work') as tmp:
        generated = Path(tmp)/'generated.docx'
        doc.save(generated)
        # Copy opaque reference parts unchanged; replace only intended edits
        # plus relationships/content-types needed for newly inserted images.
        editable = {'word/document.xml', 'docProps/core.xml', 'word/_rels/document.xml.rels', '[Content_Types].xml'}
        with zipfile.ZipFile(TEMPLATE) as source, zipfile.ZipFile(generated) as built, zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED) as target:
            source_names = set(source.namelist())
            for name in source.namelist():
                target.writestr(name, built.read(name) if name in editable else source.read(name))
            for name in built.namelist():
                if name not in source_names:
                    target.writestr(name, built.read(name))
    assert TEMPLATE.read_bytes() == baseline
    preserve = []
    with zipfile.ZipFile(TEMPLATE) as source, zipfile.ZipFile(OUTPUT) as target:
        for name in source.namelist():
            if name not in editable:
                assert source.read(name) == target.read(name), name
                preserve.append(name)
    result = dict(author='殷明骏', student_id='202483890029', header_only=header_only,
                  template_sha256=hashlib.sha256(baseline).hexdigest(), retained_template_unchanged=True,
                  title_xml_unchanged=True, section_geometry_unchanged=True,
                  language='English except bilingual personal names', language_check_passed=True,
                  preserve_only_parts=preserve, output=str(OUTPUT.relative_to(ROOT)),
                  members=identity['members'], metadata_author=identity['author'])
    (ROOT/'output/template_fidelity.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--header-only', action='store_true')
    build(parser.parse_args().header_only)
