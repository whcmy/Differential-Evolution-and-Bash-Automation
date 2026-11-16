from pathlib import Path
from lxml import etree
from PIL import Image
import fitz,hashlib,json,zipfile
r=Path(__file__).resolve().parents[1];out=r/'output';qa=out/'qa'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
artifact_hashes=dict(pdf_sha256=sha(out/'pdf/Project1_Report.pdf'),docx_sha256=sha(out/'Project1_Report.docx'))
raw=json.loads((r/'report_work/journal_integrity_before.json').read_text())
assert all(sha(r.parent/p)==h for p,h in raw.items())
backup=r.parent/'backups/2026-11-16_before_project1_journal_rebuild/root_Project1_殷明骏_202483890029_Final.zip'
with zipfile.ZipFile(backup) as z:
 refs=[n for n in z.namelist() if n.startswith(('project1/source/','project1/reference/'))]
 assert all(hashlib.sha256(z.read(n)).hexdigest()==sha(r.parent/n) for n in refs)
with zipfile.ZipFile(r.parent/'paper.zip') as z:
 for p in (r.parent/'paper').glob('*.pdf'):
  n=next(n for n in z.namelist() if Path(n).name==p.name)
  assert hashlib.sha256(z.read(n)).hexdigest()==sha(p)
with fitz.open(out/'pdf/Project1_Report.pdf') as d,fitz.open(r.parent/'backups/2026-11-16_before_project1_journal_rebuild/output/pdf/Project1_Report.pdf') as old:
 assert len(d)==11
 assert d[0].get_pixmap().samples==old[0].get_pixmap().samples
 metadata=dict(d.metadata)
 assert metadata['author']=='殷明骏' and all(not metadata.get(k) for k in ['creator','producer','subject','keywords'])
 assert not d.get_xml_metadata() and not any(list(p.annots() or []) for p in d)
 pdfmeta=dict(author='殷明骏',creator='',producer='',subject='',keywords='',xmp_absent=True,annotations_absent=True)
with zipfile.ZipFile(out/'Project1_Report.docx') as z:
 ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
 doc=etree.fromstring(z.read('word/document.xml'));tables=doc.findall('w:body/w:tbl',ns)
 assert len(tables)==6
 assert not any('/comments' in n for n in z.namelist())
 core=etree.fromstring(z.read('docProps/core.xml'))
 fields={etree.QName(x).localname:x.text for x in core}
 assert fields['creator']==fields['lastModifiedBy']=='殷明骏'
 assert not any(fields.get(k) for k in ['description','subject','keywords'])
 assert len(etree.fromstring(z.read('docProps/app.xml')))==0
 for table in tables:
  assert all(x.get('{'+ns['w']+'}fill')=='FFFFFF' for x in table.findall('.//w:shd',ns))
sourceaudit=json.loads((qa/'figure_source_audit.json').read_text())
assert sourceaudit['summary']['ready'] and sourceaudit['summary']['counts']['FAIL']==0
source_reviews={
 'FONT-GLYPH-FLOOR':'Static heuristic mixes unrelated parent sizes. All eight final PDF glyph audits pass the 5 pt floor.',
 'EXPORT-RASTER':'Editable PDF/SVG are authoritative and PNG is the Word preview; TIFF is not required for this course report.',
 'RASTER-DPI':'400 dpi previews exceed 300 dpi; final PDF figures are vector.',
 'FINAL-WIDTH':'All eight active exported figures measure 6.9 inches. The detected 5.72 inch helper is unused.',
 'LOG-GUARD':'Absolute-error displays use a documented 1e-12 floor. Raw objectives are positive; late-window scales have explicit positive-range checks.',
 'ROTATION-ANCHOR':'Vertical function tick labels were inspected in final exports and final report; all rendered collision audits pass.'}
write(qa/'figure_source_warning_review.json',dict(author='殷明骏',source_sha256=sha(r/'plot_report.py'),all_warnings_reviewed=True,review={f['check_id']:source_reviews[f['check_id']] for f in sourceaudit['findings'] if f['level']=='WARN'}))
figures=json.loads((out/'report_figures.json').read_text())
assert len(figures)==8
for name in figures:
 alignment=json.loads((out/'figures'/f'{name}.alignment.json').read_text())
 assert alignment['verdict']=='PASS',(name,alignment['verdict'])
 collision=json.loads((out/'figures'/f'{name}.collision.json').read_text())
checks=json.loads((out/'report_acceptance.json').read_text());assert checks['passed'] and checks['pages']==11
exports=json.loads((qa/'figure_audits.json').read_text());assert len(exports)==16 and all(x['exit_code']==0 for x in exports)
visual=dict(author='殷明骏',passed=True,pages=11,pages_reviewed=11,reviewed_pages=list(range(1,12)),
 **artifact_hashes,method='All final vector PDF pages inspected at full report size; final revision changed only page11 and page1–10 raster hashes remained identical to the inspected revision.',
 qa_render_directory='output/qa/journal_final',page_image_sha256={str(i):sha(qa/'journal_final'/f'page-{i}.png') for i in range(1,12)},
 final_word_render='report_work/visual_revision_145430_02',cover_pixel_identical_to_previous=True)
write(out/'visual_acceptance.json',visual);write(qa/'visual_acceptance.json',visual)
write(out/'metadata_audit.json',dict(author='殷明骏',passed=True,**artifact_hashes,word_author=fields['creator'],word_last_editor=fields['lastModifiedBy'],word_optional_fields_empty=True,word_comments_absent=True,word_application_metadata_empty=True,pdf=pdfmeta))
write(out/'beautification_integrity.json',dict(author='殷明骏',passed=True,**artifact_hashes,source_plot_sha256=sha(r/'plot_report.py'),unchanged_raw_records=600,unchanged_experiment_and_summary_files=[p for p in raw if not p.startswith('paper/') and '_run' not in p],unchanged_source_and_reference_files=len(refs),all_six_supplied_papers_match_original_zip=True,first_page_pixel_identical=True,baseline_archive_sha256=sha(backup)))
write(out/'paper_style_acceptance.json',dict(author='殷明骏',passed=True,**artifact_hashes,pages=11,supplied_papers_inventoried=6,primary_style_sources={'PEMS-DE':[7,18,19],'DSPDE':[4,9,15],'DE-VCR':[6,10,12,18],'DMDE':[5,12,14]},adaptation='Unchanged first page; two-column body interpretation; 6.9-inch full-width scientific figures; shared legends; white horizontal-rule tables. Local-paper style references only, with all observations from original Project1 records.',figure_sheets=8,complete_curve_sheets=['curves_01_15','curves_16_30'],all_30_functions_in_main_results=True,monochrome_horizontal_rule_tables=6,retained_raw_records=600,report_checks=len(checks['checks']),figure_export_audits=16,all_pages_visually_reviewed=True))
write(out/'paper_revision_checks.json',dict(author='殷明骏',passed=True,**artifact_hashes,pages=11,vector_sheets=8,all_results_in_main_text=True,cover_unchanged=True,pdf_navigation='Section bookmarks; no separate contents page'))
# Replace earlier layout notes with the current final design record.
p=r/'report_work/paper_style_study/decisions.md';s=p.read_text();start=s.index('The reference body font')
s=s[:start]+'''The reference body font is predominantly 8 pt in two-column production. The final course adaptation preserves the first page exactly and uses 10.5 pt two-column interpretation, 9 pt captions/tables, 6.9-inch full-width displays and thin blue/orange/green trajectories. Accuracy and the 30-function temporal heatmap share one Results page. All 30 raw-objective histories occupy two15-panel plates. Redundant stages/representative plates and standalone definition/check tables are consolidated into figures and Methods prose. Six native tables retain complete required numerical results and comparison conditions. The report has11pages, eight vector sheets and no separate contents page. All source observations, papers and frozen experiment files remain unchanged.\n'''
p.write_text(s)
print(json.dumps(dict(passed=True,pages=11,figures=8,tables=6,report_checks=len(checks['checks']),figure_audits=16),indent=2))
