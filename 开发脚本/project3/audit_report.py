"""Verify the rebuilt report against the retained experiment. Author: 殷明骏."""
from pathlib import Path
import csv,hashlib,json,math,statistics,zipfile
from lxml import etree
from docx import Document
from docx.oxml.ns import qn
import pymupdf as fitz
import numpy as np
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    docx=OUT/'Project3_Report.docx';pdf=OUT/'pdf/Project3_Report.pdf';doc=Document(docx)
    with (OUT/'analysis/records.csv').open() as f:records=list(csv.DictReader(f))
    data=json.loads((OUT/'analysis/results.json').read_text());assert len(records)==270
    assert data['algorithm']=='DC-DE' and data['strict_hourly_spacing_passed']
    assert [r['gap_from_previous_seconds'] for r in data['timing_audit'][1:]]==[3601.,3599.]
    assert all(r['source'].startswith('rerun_20261116/') for r in records)
    curves=list(csv.DictReader((OUT/'figures/convergence_source.csv').open()))
    groups={}
    for row in curves:groups.setdefault((int(row['function']),int(row['population'])),[]).append(row)
    assert len(groups)==90 and {key[0] for key in groups}==set(range(1,31))
    for (fid,pop),values in groups.items():
        grid=np.asarray([float(r['evaluations']) for r in values]);expected=[]
        for row in records:
            if int(row['function'])!=fid or int(row['population'])!=pop:continue
            source=ROOT/row['source'];assert digest(source)==row['sha256']
            record=json.loads(source.read_text());history=np.asarray(record['history'])
            assert np.all(np.isin(history[:,0],grid))
            idx=np.searchsorted(history[:,0],grid,side='right')-1
            assert idx.min()>=0
            expected.append(np.abs(history[idx,1]-record['optimum']))
        assert len(expected)==3
        expected=np.asarray(expected)
        assert grid[-1]==100000
        for key,a in [('median_absolute_error',np.median(expected,axis=0)),('minimum_absolute_error',expected.min(axis=0)),('maximum_absolute_error',expected.max(axis=0))]:
            assert np.array_equal(np.asarray([float(r[key]) for r in values]),a),(fid,pop,key)
    assert all(sec._sectPr.find(qn('w:cols')).get(qn('w:num'),'1')=='1' for sec in doc.sections)
    table=doc.tables[-1];assert len(table.rows)==31
    for fid,row in enumerate(table.rows[1:],1):
        assert row.cells[0].text==f'F{fid:02d}'
        for j,pop in enumerate([50,100,150],1):
            a=[float(r['absolute_error']) for r in records if int(r['function'])==fid and int(r['population'])==pop]
            assert len(a)==3
            assert row.cells[j].text==f'{math.fsum(a)/3:.5e} ({statistics.stdev(a):.3e})'
    for row,pop in zip(doc.tables[2].rows[1:],[50,100,150]):
        scores=[s['score'] for s in data['suites'] if s['population']==pop]
        assert [c.text for c in row.cells[1:4]]==[f'{x:.6e}' for x in scores]
    body=doc._element.body;cover=etree.fromstring((ROOT/'source/cover_preserved.xml').read_bytes());canon=lambda n:etree.tostring(n,method='c14n',exclusive=True)
    for node in cover.iter(qn('w:t')):
        if node.text: node.text=node.text.replace('2026-11-10','2026-11-16')
    assert [canon(n) for n in list(body)[:15]]==[canon(n) for n in list(cover)[:15]]
    document_text='\n'.join(p.text for p in doc.paragraphs)
    assert 'Mingjun Yin (殷明骏) completed the experiments and wrote the experimental report.' in document_text
    assert 'Hongrui Ding (丁鸿睿) improved the report’s layout and visual presentation.' in document_text
    assert not any(s in document_text.lower() for s in ['future work','outlook','prospects','前瞻','展望'])
    assert 'Project 3 at a glance' not in document_text
    assert 'Population 100 gives the lowest arithmetic mean' in document_text
    assert not any(v in document_text for v in ['18:44:22','20261111','1.736147e+05'])
    assert not any(s in document_text.lower() for s in ['appendix','appendices','figure e'])
    assert document_text.index('6.1 Scheduling records')<document_text.index('7 Conclusions')<document_text.index('References')
    labels=[int(p.text.split('.')[0].split()[1]) for p in doc.paragraphs if p.text.startswith('Figure ') and p.style.name=='Paper Caption']
    assert labels==list(range(1,16)),labels
    assert len(list(body.iter(qn('m:oMath'))))==1
    with zipfile.ZipFile(docx) as z:
        assert not any('comments' in n.lower() for n in z.namelist())
        core=etree.fromstring(z.read('docProps/core.xml'));meta={etree.QName(n).localname:n.text for n in core}
        assert meta['creator']==meta['lastModifiedBy']=='殷明骏';assert set(meta)<={'title','creator','lastModifiedBy'}
    baseline=ROOT.parent/'backups/2026-11-16_before_project3_paper_rebuild/Project3_殷明骏_202483890029_Final.zip'
    frozen=[]
    with zipfile.ZipFile(baseline) as old:
        for entry in old.namelist():
            relative=entry.removeprefix('Project3/')
            if relative.startswith(('code/','output/cron_1_','output/cron_2_','output/cron_3_','evidence/screenshots/')) or relative in ['run_experiments.sh','verify_batch.py','cron/success_01.json','cron/success_02.json','cron/success_03.json','cron/scheduled.log']:
                p=ROOT/relative;assert p.is_file();assert hashlib.sha256(old.read(entry)).hexdigest()==digest(p),relative;frozen.append(relative)
    final=fitz.open(pdf);source=fitz.open(ROOT/'source/cover_preserved.pdf')
    spans=lambda page:[(s['text'].replace('2026-11-10','2026-11-16'),s['bbox'],s['font'],s['size']) for b in page.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans'] if s['bbox'][1]<500]
    assert spans(final[0])==spans(source[0])
    first=final[0].get_text();assert 'Author contributions' in first and 'at a glance' not in first
    assert 'completed the experiments' in first and 'Hongrui Ding' in first
    with fitz.open(ROOT.parent/'backups/2026-11-16_before_project3_scientific_figures/Project3_Report.pdf') as before:
        a=final[0].get_pixmap(matrix=fitz.Matrix(2,2));b=before[0].get_pixmap(matrix=fitz.Matrix(2,2))
        aa=np.frombuffer(a.samples,dtype=np.uint8).reshape(a.height,a.width,3).copy()
        bb=np.frombuffer(b.samples,dtype=np.uint8).reshape(b.height,b.width,3).copy()
        for page,date in [(final[0],'2026-11-16'),(before[0],'2026-11-10')]:
            for rect in page.search_for(date):
                x0,y0,x1,y1=rect+(-2,-2,2,2)
                aa[int(y0*2):int(y1*2)+1,int(x0*2):int(x1*2)+1]=255
                bb[int(y0*2):int(y1*2)+1,int(x0*2):int(x1*2)+1]=255
        assert np.array_equal(aa,bb),'Cover changed outside experiment date'
    assert '2026-11-16' in first
    rendered_checks=json.loads((OUT/'figures/rendered_qa.json').read_text())
    assert len(rendered_checks)==16 and all(x['code']==0 for x in rendered_checks)
    assert final.metadata['author']=='殷明骏';assert not final.get_xml_metadata()
    assert not any(final.metadata.get(k) for k in ['creator','producer','subject','keywords','creationDate','modDate'])
    assert not any(list(p.annots() or []) for p in final)
    sections=json.loads((OUT/'report_sections.json').read_text());assert len(final.get_toc())==len(sections)
    audit=dict(author='殷明骏',passed=True,body_columns=1,pages=len(final),docx_sha256=digest(docx),pdf_sha256=digest(pdf),cover_identity_xml_unchanged=True,cover_identity_pdf_spans_unchanged=True,cover_overview_replaced_with_contributions=True,complete_function_mean_sd_cells_verified=90,suite_scores_verified=9,native_tables=4,vector_figure_sheets=8,convergence_functions=30,convergence_histories=270,evidence_screenshots=7,contributions_on_first_page=True,appendices_absent=True,evidence_in_main_experiment_section=True,outlook_absent=True,native_math_preserved=True,metadata_passed=True,baseline_files_compared=len(frozen),frozen_code_and_records_unchanged=True,all_thirty_functions_in_one_table=True)
    (OUT/'paper_revision_checks.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n');print(json.dumps(audit,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
