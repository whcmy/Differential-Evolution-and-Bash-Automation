"""Package only verified final Project3 deliverables. Author: 殷明骏."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

import fitz
from lxml import etree

ROOT=Path(__file__).resolve().parent


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    analysis=json.loads((ROOT/'output/analysis/results.json').read_text())
    assert analysis['complete'] and analysis['record_count']==270
    assert analysis['algorithm']=='DC-DE' and analysis['strict_hourly_spacing_passed']
    rerun=ROOT/'rerun_20261116'
    proof=json.loads((rerun/'evidence/final_independent_verification.json').read_text())
    assert proof['passed'] and proof['records_recomputed']==270
    frozen=json.loads((rerun/'evidence/pipeline_sha256.json').read_text())
    assert all(digest(rerun/name)==h for name,h in frozen.items())
    render=json.loads((ROOT/'output/render_audit.json').read_text())
    assert not render['draft'] and render['geometric_clipping_passed']
    acceptance=json.loads((ROOT/'output/visual_acceptance.json').read_text())
    assert acceptance['passed'] and acceptance['pages_reviewed']==len(render['pages'])
    original_hashes=json.loads((ROOT/'evidence/original_record_hashes.json').read_text())
    for name,expected in original_hashes['sha256'].items():
        assert digest(ROOT/name)==expected, f'Original execution record changed: {name}'
    docx=ROOT/'output/Project3_Report.docx';pdf=ROOT/'output/pdf/Project3_Report.pdf'
    assert acceptance['docx_sha256']==digest(docx) and acceptance['pdf_sha256']==digest(pdf)
    with zipfile.ZipFile(docx) as document:
        assert not any('/comments' in name for name in document.namelist())
        core=etree.fromstring(document.read('docProps/core.xml'))
        values={etree.QName(n).localname:n.text for n in core}
        assert values['creator']==values['lastModifiedBy']=='殷明骏'
        assert set(values)<= {'title','creator','lastModifiedBy'}
    with fitz.open(pdf) as document:
        assert document.metadata['author']=='殷明骏'
        assert not any(document.metadata.get(k) for k in ('creator','producer','subject','keywords'))
        assert not document.get_xml_metadata()
        assert not any(list(page.annots() or []) for page in document)
    files=[]
    for name in ('README.md','RUN_STATE.md','requirements.lock.txt','run_experiments.sh','verify_batch.py',
                 'collect_results.py','build_report.py','report_components.py','finish_report.py',
                 'clean_metadata.py','package_project3.py','paper_layout.py','plot_report.py','audit_report.py'):
        files.append(ROOT/name)
    for folder in ('code','source','cron','evidence','tests','protocol','rerun_20261116'):
        for path in (ROOT/folder).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix in ('.pyc','.lock'):continue
            if path.is_relative_to(ROOT/'evidence/presentation'):continue
            if path.name in ('manual_console.log','precompute_console.log','draft_build.log'):continue
            files.append(path)
    for path in (ROOT/'output').rglob('*'):
        if path.is_file() and (path.parent==ROOT/'output' or 'analysis' in path.parts or 'figures' in path.parts or path==pdf):
            if path.name not in ('package_validation.json','delivery_manifest.json','precomputation_replay.json'):files.append(path)
    for receipt in analysis['receipts']:
        files.extend(p for p in (ROOT/receipt['output']).rglob('*') if p.is_file() and p.suffix!='.pyc')
    # Keep the earlier PGE-DE raw records as explicitly labelled historical evidence.
    for historical in (ROOT/'output').glob('cron_*'):
        files.extend(p for p in historical.rglob('*') if p.is_file() and p.suffix not in ('.pyc','.lock'))
    files=sorted(set(files))
    manifest=dict(author='殷明骏',last_modified_by='殷明骏',algorithm='DC-DE',
                  current_experiment='rerun_20261116',historical_pgede_records_preserved=True,
                  scheduled_executions=3,optimization_records=270,
                  strict_actual_hourly_spacing_passed=analysis['strict_hourly_spacing_passed'],
                  report_timeline='Original execution timestamps; planned launches shown separately',
                  files={str(p.relative_to(ROOT)):dict(size=p.stat().st_size,sha256=digest(p)) for p in files})
    manifest_path=ROOT/'output/delivery_manifest.json'
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    files.append(manifest_path)
    target=ROOT.parent/'Project3_殷明骏_202483890029_Final.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.comment=b''
        for path in files:archive.write(path,'Project3/'+str(path.relative_to(ROOT)))
    with zipfile.ZipFile(target) as archive:
        assert not archive.comment and not any(i.comment for i in archive.infolist())
        assert archive.testzip() is None
        for name,info in manifest['files'].items():
            assert hashlib.sha256(archive.read('Project3/'+name)).hexdigest()==info['sha256']
        assert archive.getinfo('Project3/run_experiments.sh').external_attr>>16 & 0o111
    receipt=dict(author='殷明骏',passed=True,archive=str(target),sha256=digest(target),files=len(files),
                 synchronized_report=True,metadata_passed=True)
    (ROOT/'output/package_validation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(target)


if __name__=='__main__':main()
