"""Single-column text and full-width displays. Author: 殷明骏."""
from docx.enum.section import WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


def enable_journal_layout(report):
    doc = report.doc
    original_p, original_h = report.p, report.h
    original_fig, original_table = report.fig, report.table
    report._journal_columns = 1
    report._journal_started = False

    for name, size in [('Paper Body', 11), ('Paper Abstract', 11),
                       ('Paper Caption', 9), ('Paper Note', 9),
                       ('Paper Heading 1', 12), ('Paper Heading 2', 10.5)]:
        st = doc.styles[name]
        st.font.size = Pt(size)
        st.paragraph_format.line_spacing = 1.12
        st.paragraph_format.space_after = Pt(4)
        if 'Heading' in name:
            st.paragraph_format.space_before = Pt(7)

    def section(columns=1, newpage=False):
        if newpage and report._journal_started and report._journal_columns == 2:
            section(1)
        if report._journal_started and columns == report._journal_columns and not newpage:
            return
        sec = doc.add_section(WD_SECTION_START.NEW_PAGE if newpage else WD_SECTION_START.CONTINUOUS)
        sec.left_margin = Inches((sec.page_width.inches - 6.9) / 2)
        sec.right_margin = sec.left_margin
        sec.top_margin = Inches(.78)
        sec.bottom_margin = Inches(.68)
        sec.different_first_page_header_footer = False
        cols = sec._sectPr.find(qn('w:cols'))
        if cols is None:
            cols = OxmlElement('w:cols')
            sec._sectPr.append(cols)
        for child in list(cols):
            cols.remove(child)
        cols.set(qn('w:num'), str(columns))
        cols.set(qn('w:space'), '320')
        # Section-break paragraphs must not consume body leading.
        paragraph = doc.paragraphs[-1]
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = Pt(1)
        for run in paragraph.runs:
            run.font.size = Pt(1)
        report._journal_columns = columns
        report._journal_started = True

    def paragraph(text, style='Report Body', keep=False):
        if style in ['Report Body','Paper Reference']:
            section(1)
        p = original_p(text, 'Report Note' if style=='Paper Reference' else style, keep)
        size = 11 if style in ['Report Body', 'Paper Abstract'] else 9
        for run in p.runs:
            run.font.size = Pt(size)
        if style == 'Report Body':
            p.paragraph_format.keep_together = False
            p.paragraph_format.line_spacing = 1.12
        return p

    def heading(text, level=1, newpage=False, toc=True):
        section(1, newpage=newpage)
        p = original_h(text, level, False, toc)
        p.paragraph_format.page_break_before = False
        p.paragraph_format.space_before = Pt(0 if newpage else 7)
        for run in p.runs:
            run.font.size = Pt(12 if level == 1 else 10.5)
        return p

    def figure(name, caption, width=6.9):
        section(1)
        original_fig(name, caption, width)
        doc.paragraphs[-2].alignment = WD_ALIGN_PARAGRAPH.CENTER

    def table(*args, **kwargs):
        section(1)
        kwargs['size'] = min(kwargs.get('size', 9), 9)
        return original_table(*args, **kwargs)

    report.close_layout = lambda: section(1)
    report.p, report.h = paragraph, heading
    report.fig, report.table = figure, table
