"""Raw-result, document-content and metadata acceptance. Author: 殷明骏."""
from collections import Counter
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import statistics
import sys
import zipfile
from lxml import etree
import fitz
ROOT=Path(__file__).resolve().parents[1];LOCAL=Path(__file__).parent;OUT=ROOT/'output'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
AUTHOR='殷明骏'
BASE=ROOT.parent/'backups/2026-11-16_before_report2_algorithm_improvement/project2_final/output/Project2_Report.docx'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def text(node):return ''.join(node.xpath('.//w:t/text()',namespaces=NS))


def xml(path):
    with zipfile.ZipFile(path) as z:return etree.fromstring(z.read('word/document.xml'))


def table_rows(document):
    from compact_tables import decode_table
    return Counter(r for table in document.findall('.//w:tbl',NS) for r in decode_table(table))


def read_csv(name):
    with (LOCAL/'analysis'/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))


def formatted(x):return '0' if float(x)==0 else f'{float(x):.3e}'


def main():
    summary=json.loads((LOCAL/'analysis/confirmation_summary.json').read_text())
    contract=json.loads((LOCAL/'confirmation_contract.json').read_text())
    verified=json.loads((LOCAL/'results/confirmation/verification.json').read_text())
    assert verified['passed'] and verified['records']==4800
    records=[json.loads(p.read_text()) for p in (LOCAL/'results/confirmation').rglob('*_run*.json')]
    assert len(records)==4800
    lookup={}
    for record in records:lookup.setdefault((record['function'],record['algorithm']),[]).append(record)
    for group in lookup.values():assert len(group)==20
    display={'DE':'DE','DSPDE':'DSPDE','DLSDE':'DLS-DE','PEMSDE':'PEMS-DE','TEAM':'PGE-DE','DUAL':'DC-DE'}
    short={'DUAL':'DC-DE','DLSDE':'Without crossover','DUAL_no_phase':'Without two-phase','DUAL_no_learning':'Without learning'}
    expected_new=Counter();cell_count=0
    for filename,names in [('confirmation_statistics.csv',display),('confirmation_ablation_statistics.csv',short)]:
        for row in read_csv(filename):
            group=lookup[int(row['function']),row['algorithm']]
            values=[r['error'] for r in group]
            independent=dict(best=min(values),mean=statistics.mean(values),std=statistics.stdev(values),variance=statistics.variance(values))
            for key,value in independent.items():
                assert math.isclose(value,float(row[key]),rel_tol=1e-12,abs_tol=1e-9),(filename,row,key)
                cell_count+=1
            expected_new[(f"F{int(row['function']):02d}",names[row['algorithm']],
                          *[formatted(row[k]) for k in ['best','mean','std','variance']],
                          f"{float(row['rank']):.1f}")]+=1
    # Independently implement the documented sorted-anchor tie groups with stdlib.
    methods=summary['main_methods'];rank_sums=dict.fromkeys(methods,0.)
    for fid in range(1,31):
        means={a:statistics.mean(r['error'] for r in lookup[fid,a]) for a in methods}
        ordered=sorted(methods,key=lambda a:means[a]);start=0
        while start<len(ordered):
            stop=start+1;anchor=means[ordered[start]]
            while stop<len(ordered) and abs(means[ordered[stop]]-anchor)<=1e-8+1e-10*abs(anchor):stop+=1
            for a in ordered[start:stop]:rank_sums[a]+=(start+1+stop)/2
            start=stop
    independent_ranks={a:value/30 for a,value in rank_sums.items()}
    for r in summary['mean_ranks']:assert math.isclose(independent_ranks[r['algorithm']],r['mean_rank'],abs_tol=1e-12)
    assert independent_ranks['DUAL']<min(value for a,value in independent_ranks.items() if a!='DUAL')
    tests=read_csv('confirmation_paired_tests.csv')
    assert Counter(r['family'] for r in tests)=={'primary':90,'other_paper':60,'ablation':60}
    assert len({(r['function'],r['comparison']) for r in tests})==210
    curve_path=OUT/'figures/revision_curve_selection.csv'
    with curve_path.open(encoding='utf-8-sig') as f:selected=list(csv.DictReader(f))
    assert len(selected)==180
    assert {(int(r['function']),r['algorithm']) for r in selected}=={(f,a) for f in range(1,31) for a in methods}
    selected_lookup={}
    for r in selected:
        key=int(r['function']),r['algorithm'];best=min(lookup[key],key=lambda x:(x['fun'],x['run']))
        assert (int(r['run']),int(r['seed']),float(r['final_objective']))==(best['run'],best['seed'],best['fun'])
        selected_lookup[key]=best
    curve_points={key:[] for key in selected_lookup}
    with (OUT/'figures/revision_curve_data.csv').open(encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            key=int(r['function']),r['algorithm'];best=selected_lookup[key]
            assert (int(r['run']),int(r['seed']))==(best['run'],best['seed'])
            curve_points[key].append([int(r['fes']),float(r['objective'])])
    assert all(curve_points[key]==best['history'] for key,best in selected_lookup.items())
    document=xml(OUT/'Project2_Report.docx');previous=xml(BASE)
    old_rows=table_rows(previous);actual=table_rows(document)
    assert sum(old_rows.values())==810
    assert sum(expected_new.values())==300
    assert actual==old_rows+expected_new, 'A required numerical row is missing or altered'
    cover=etree.fromstring((ROOT/'source/cover_preserved.xml').read_bytes())
    nodes=list(document.find('w:body',NS))
    canonical=lambda n:etree.tostring(n,method='c14n',exclusive=True)
    assert [canonical(n) for n in nodes[:len(cover)]]==[canonical(n) for n in cover]
    paragraphs=[text(n) for n in document.findall('w:body/w:p',NS)]
    tables=[int(m[1]) for s in paragraphs if (m:=re.match(r'^Table (\d+)\.',s))]
    figures=[int(m[1]) for s in paragraphs if (m:=re.match(r'^Figure (\d+)\.',s))]
    assert tables==list(range(1,21)),tables
    assert figures==list(range(1,17)),figures
    assert len(document.findall('.//m:oMath',NS))>=5
    fidelity=json.loads((OUT/'template_fidelity.json').read_text());assert fidelity['body_columns']==1
    assert all(c.get('{'+NS['w']+'}num','1')=='1' for c in document.findall('.//w:cols',NS))
    assert not any(re.search('appendix|appendices',s,re.I) for s in paragraphs)
    with zipfile.ZipFile(OUT/'Project2_Report.docx') as z:
        core=etree.fromstring(z.read('docProps/core.xml'))
        values={etree.QName(n).localname:n.text for n in core}
        assert values.get('creator')==values.get('lastModifiedBy')==AUTHOR
        assert set(values)<={'title','creator','lastModifiedBy'}
        assert len(etree.fromstring(z.read('docProps/app.xml')))==0
        assert not any('/comments' in name for name in z.namelist())
        preserve=json.loads((ROOT/'source/journal_base_fidelity.json').read_text())['preserve_only_parts']
        with zipfile.ZipFile(ROOT/'source/template/实验报告模板.docx') as template:
            assert all(z.read(name)==template.read(name) for name in preserve)
    pdf=fitz.open(OUT/'pdf/Project2_Report.pdf')
    assert pdf.metadata['author']==AUTHOR
    assert not any(pdf.metadata.get(k) for k in ['creator','producer','subject','keywords'])
    assert not pdf.get_xml_metadata() and not any(list(p.annots() or []) for p in pdf)
    with fitz.open(ROOT/'source/cover_preserved.pdf') as cover_pdf:
        assert pdf[0].get_pixmap(matrix=fitz.Matrix(2,2)).samples==cover_pdf[0].get_pixmap(matrix=fitz.Matrix(2,2)).samples
    assert len(pdf.get_toc())==len(json.loads((OUT/'report_sections.json').read_text()))
    clipped=[];footer_intrusions=[];fragment_pages=[]
    for i,page in enumerate(pdf):
        spans=[s for block in page.get_text('dict')['blocks'] if 'lines' in block for line in block['lines'] for s in line['spans']]
        footers=[s for s in spans if re.fullmatch(r'\d+',s['text'].strip()) and s['bbox'][1]>page.rect.height-45 and abs((s['bbox'][0]+s['bbox'][2])/2-page.rect.width/2)<40]
        footer_top=min((s['bbox'][1] for s in footers),default=page.rect.height-20)
        for span in spans:
            b=span['bbox']
            if b[0]<-.5 or b[1]<-.5 or b[2]>page.rect.width+.5 or b[3]>page.rect.height+.5:clipped.append(dict(page=i+1,text=span['text'],bbox=b))
            if i and span not in footers and b[1]<footer_top and b[3]>footer_top-12:footer_intrusions.append(dict(page=i+1,text=span['text'],bbox=b))
        if len(page.get_text().strip())<100:fragment_pages.append(i+1)
    assert not clipped and not footer_intrusions and not fragment_pages,(clipped,footer_intrusions,fragment_pages)
    build=json.loads((OUT/'visual_revision_build.json').read_text())
    assert len(build['vector_figures'])==16
    assert all(r['raster_agreement_mae']<5 for r in build['vector_figures'])
    geometry=dict(author=AUTHOR,report_sha256=sha(OUT/'pdf/Project2_Report.pdf'),total_pages=len(pdf),
                  geometric_clipping_passed=True,clipped=clipped,footer_intrusions=footer_intrusions,fragment_pages=fragment_pages)
    (OUT/'qa/render_audit.json').write_text(json.dumps(geometry,ensure_ascii=False,indent=2)+'\n')
    visual_path=OUT/'qa/visual_acceptance.json'
    visual=json.loads(visual_path.read_text()) if visual_path.exists() else {}
    fresh_visual=(visual.get('accepted') is True and visual.get('pages_reviewed')==len(pdf)
                  and visual.get('report_sha256')==sha(OUT/'pdf/Project2_Report.pdf')
                  and visual.get('docx_sha256')==sha(OUT/'Project2_Report.docx'))
    result=dict(author=AUTHOR,passed=True,pages=len(pdf),independent_records=4800,
                raw_statistic_cells_recomputed=cell_count,independently_recomputed_mean_ranks=independent_ranks,
                first_descriptive_rank_verified=True,original_numerical_rows=810,new_numerical_rows=300,
                complete_cover_xml_and_pdf_preserved=True,metadata_passed=True,body_columns=1,
                selected_curve_runs_verified=180,all_curve_checkpoints_verified=True,geometric_clipping_passed=True,
                table_captions=20,compact_function_rows=210,all_five_statistics_retained=True,figure_captions=16,docx_sha256=sha(OUT/'Project2_Report.docx'),
                pdf_sha256=sha(OUT/'pdf/Project2_Report.pdf'),visual_acceptance_required=not fresh_visual,visual_acceptance_verified=fresh_visual)
    (OUT/'algorithm_revision_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
