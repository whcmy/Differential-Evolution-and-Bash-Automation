"""Final report and evidence checks. Author: 殷明骏."""
from pathlib import Path
import csv,json,hashlib,re,zipfile
from lxml import etree
import fitz
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math','dc':'http://purl.org/dc/elements/1.1/','cp':'http://schemas.openxmlformats.org/package/2006/metadata/core-properties'}
def read(p):
 with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def fmt(x):return '0' if float(x)==0 else f'{float(x):.3e}'
def main():
 checks=[]
 def check(name,value):
  assert value,name
  checks.append(dict(name=name,passed=True))
 with zipfile.ZipFile(OUT/'Baseline_Study.docx') as z:
  doc=etree.fromstring(z.read('word/document.xml'));core=etree.fromstring(z.read('docProps/core.xml'));app=etree.fromstring(z.read('docProps/app.xml'))
  check('Word author and last editor',core.findtext('dc:creator',namespaces=NS)==core.findtext('cp:lastModifiedBy',namespaces=NS)=='殷明骏')
  check('Word optional metadata removed',all(not core.findtext(t,namespaces=NS) for t in ['dc:subject','dc:description','cp:keywords']) and len(app)==0)
  check('Word comments absent',not any('comments' in n.lower() for n in z.namelist()))
  check('Three editable equations',len(doc.findall('.//m:oMath',NS))==3)
  tables=[]
  for t in doc.findall('w:body/w:tbl',NS):
   tables.append([[''.join(c.itertext()).strip() for c in row.findall('w:tc',NS)] for row in t.findall('w:tr',NS)])
  check('Six native tables',len(tables)==6)
  summary=read(OUT/'summary_error.csv')
  target=next(t for t in tables if t[0]==['Function','Best','Median','Mean','Worst','Std','Variance'])
  check('All 180 original statistics',target[1:]==[[r['function']]+[fmt(r[k]) for k in ['best','median','mean','worst','std','variance']] for r in summary])
  ev=read(ROOT/'consistency/evaluator_summary.csv');comp=read(ROOT/'consistency/paper_comparison.csv')
  target=next(t for t in tables if t[0]==['Function','opfunu Mean','opfunu Std','Original Mean','Original Std'])
  check('All 120 evaluator comparison cells',target[1:]==[[f"F{int(r['function']):02d}"]+[fmt(r[k]) for k in ['opfunu_mean','opfunu_std','official_mean','official_std']] for r in ev])
  target=next(t for t in tables if t[0]==['Function','Python Mean','Python SD(n)','Paper Mean','Paper SD(n)','Gap / band'])
  expected=[[f"F{int(r['function']):02d}"]+[fmt(r[k]) for k in ['mean','population_std','paper_mean','paper_std']]+[f"{float(r['absolute_gap'])/float(r['descriptive_tolerance']):.3f}"] for r in comp]
  check('All 140 same-algorithm comparison cells',target[1:]==expected)
  text=''.join(doc.itertext());identity=json.loads((ROOT/'source/report_identity.json').read_text())
  check('All group members retained',all(m['chinese'] in text and m['student_id'] in text for m in identity['members']))
  for n in [identity['tutor_chinese']]+[m['chinese'] for m in identity['members']]:text=text.replace(n,'')
  check('Report English except names',not re.search(r'[\u3400-\u9fff]',text))
  check('All body sections single-column',all(e.get('{'+NS['w']+'}num','1')=='1' for e in doc.findall('.//w:cols',NS)))
  check('No VCR column used as reproduction target','DE-VCR mean' not in text and '27 of 28' in text and 'F21 remains' in text)
 frozen=json.loads((ROOT/'consistency/frozen_inputs.json').read_text())
 check('Original 600 records and optimizer unchanged',all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in frozen.items()))
 verification=json.loads((ROOT/'consistency/verification.json').read_text())
 check('1160 added runs verified',verification['saved_solutions_recomputed']==1160 and verification['all_solution_checks_pass'])
 check('Expanded 6120 benchmark probes',verification['pointwise_probes']==6120 and len(verification['mismatch_functions'])==13)
 check('Full literature comparison and residual discrepancy',verification['paper_comparison_functions']==28 and len(verification['descriptively_close_functions'])==27 and verification['outside_descriptive_band']==[21])
 check('Original record verification passed',json.loads((OUT/'verification.json').read_text())['status']=='passed')
 pdf=fitz.open(OUT/'pdf/Baseline_Study.pdf')
 check('PDF author',pdf.metadata['author']=='殷明骏')
 check('PDF optional metadata absent',all(not pdf.metadata.get(k) for k in ['creator','producer','subject','keywords']) and not pdf.get_xml_metadata())
 check('PDF annotations absent',all(not list(p.annots() or []) for p in pdf))
 before=fitz.open(ROOT.parent/'backups/2026-11-16_baseline_study_consistency/Baseline_Study.pdf')
 check('Cover unchanged',pdf[0].get_pixmap().samples==before[0].get_pixmap().samples)
 mapping=json.loads((OUT/'report_page_map.json').read_text());norm=lambda x:''.join(x.split())
 check('All section destinations correct',all(norm(t) in norm(pdf[n-1].get_text()) for t,n in mapping.items()))
 check('Bookmarks correct',all(r[2]==mapping[r[1]] for r in pdf.get_toc()))
 check('No nearly empty body pages',all(len(p.get_text().split())>70 for p in list(pdf)[1:]))
 for p in pdf:
  check('Page bounds '+str(p.number+1),all(x[0]>=0 and x[1]>=0 and x[2]<=p.rect.width+.5 and x[3]<=p.rect.height+.5 for x in p.get_text('words')))
 check('No missing glyphs','\ufffd' not in ''.join(p.get_text() for p in pdf))
 figures=json.loads((OUT/'report_figures.json').read_text());build=json.loads((OUT/'visual_revision_build.json').read_text())
 check('12 vector figures included',len(figures)==len(build['vector_figures'])==12)
 audits=json.loads((ROOT/'consistency/figure_audits.json').read_text())
 check('8 new rendered-figure audits pass',len(audits)==8 and all(r['exit_code']==0 for r in audits))
 for n in figures:
  f=fitz.open(OUT/'figures'/f'{n}.pdf')
  check('Figure metadata '+n,f.metadata['author']=='殷明骏' and all(not f.metadata.get(k) for k in ['creator','producer','subject','keywords']) and not f.get_xml_metadata())
 result=dict(author='殷明骏',passed=True,pages=len(pdf),vector_sheets=12,course_runs=600,added_runs=1160,checked_numeric_cells=440,checks=checks)
 (OUT/'report_acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
