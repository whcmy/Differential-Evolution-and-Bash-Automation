"""Final requirement audit and byte-verified ZIP; author 殷明骏."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import zipfile
import xml.etree.ElementTree as ET
from pypdf import PdfReader
from pypdf.generic import NullObject
from analyze_project2 import load, FINAL

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'output'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    requirements = []
    def check(name, value, evidence):
        requirements.append(dict(requirement=name, passed=bool(value), evidence=evidence))
    for name in ['coursework_validation.json', 'pems_native_validation.json',
                 'legacy_dls_validation.json', 'legacy_dsp_validation.json',
                 'selected_replay.json', 'analysis_helper_validation.json']:
        path = OUT/name
        check(name, path.exists() and json.loads(path.read_text())['passed'], str(path.relative_to(ROOT)))
    revision=OUT/'revision_acceptance.json'
    check('evidence and visual revision acceptance',revision.exists() and json.loads(revision.read_text())['passed'] and json.loads(revision.read_text()).get('pdf_sha256')==sha(OUT/'pdf/Project2_Report.pdf'),'output/revision_acceptance.json')
    algorithm_revision=json.loads((OUT/'algorithm_revision_audit.json').read_text())
    check('complete independent algorithm confirmation and fresh report audit',
          algorithm_revision['passed'] and algorithm_revision['independent_records']==4800
          and algorithm_revision['first_descriptive_rank_verified']
          and algorithm_revision['pdf_sha256']==sha(OUT/'pdf/Project2_Report.pdf')
          and algorithm_revision['docx_sha256']==sha(OUT/'Project2_Report.docx'),
          'output/algorithm_revision_audit.json')
    compact=json.loads((OUT/'compact_table_manifest.json').read_text())
    check('compact tables retain all five fields and 1110 statistical records',
          compact['passed'] and compact['all_printed_values_preserved']
          and compact['original_statistical_records']==1110 and compact['compact_function_rows']==210
          and algorithm_revision['table_captions']==20 and algorithm_revision['all_five_statistics_retained'],
          'output/compact_table_manifest.json; output/algorithm_revision_audit.json')
    figure_revision=json.loads((OUT/'confirmation_figure_audit.json').read_text())
    check('all sixteen current figures audited',len(figure_revision)==16
          and all(r['font_code']==r['collision_code']==0 and r['alignment'] in ['PASS','NOT APPLICABLE']
                  and r['pdf_sha256']==sha(OUT/'figures'/f"{r['figure']}.pdf") for r in figure_revision),
          'output/confirmation_figure_audit.json')
    independent=json.loads((ROOT/'improvement_v2/results/confirmation/verification.json').read_text())
    check('all 4800 independent records verified',independent['passed'] and independent['records']==4800,
          'improvement_v2/results/confirmation/verification.json')
    course = load(ROOT/'results/coursework')
    check('7200 formal coursework records', len(course) == 7200, 'results/coursework/manifest.json')
    native = load(ROOT/'results/pems_native_reference')
    check('PEMS official-numbered original-condition reproduction: 29x20', len(native) == 580, 'results/pems_native_reference/manifest.json')
    final_rows = [r for r in course if r['algorithm'] in FINAL]
    check('five algorithms x 30 functions x 20 runs', len(final_rows) == 3000, 'results/coursework/')
    config = json.loads((ROOT/'results/coursework/manifest.json').read_text())['config']
    check('fixed NP=100, actual FEs=100000, CEC2014 10D',
          config['population_size'] == 100 and config['population_mode'] == 'fixed'
          and config['dimension'] == 10 and config['suite'] == 'cec2014'
          and config['max_fes'] == 100000 and all(r['nfev'] == 100000 for r in course), 'results/coursework/manifest.json')
    check('frozen optimizer code matches all recorded hashes', all(sha(ROOT/'code'/name) == value for name, value in config['source_sha256'].items()), 'results/coursework/manifest.json and code/')
    dls = [r for r in course if r['algorithm'] == 'DLSDE']
    check('DLS controlled fixed population stays 100',
          all(r['diagnostics']['initial_population'] == r['diagnostics']['min_population_seen'] == r['diagnostics']['final_population'] == 100 for r in dls), 'results/coursework/DLSDE/')
    # Cross-check table cells using Python's independent standard-library
    # summary functions rather than importing the summary implementation.
    cells = 0
    with (OUT/'final_statistics.csv').open(encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            xs = [r['error'] for r in final_rows if (r['algorithm'], r['function']) == (row['algorithm'], int(row['function']))]
            assert len(xs) == 20
            expected = dict(best=min(xs), mean=statistics.mean(xs), std=statistics.stdev(xs), variance=statistics.variance(xs))
            for key, value in expected.items():
                if not math.isclose(float(row[key]), value, rel_tol=1e-12, abs_tol=1e-9):
                    raise ValueError(f'independent table mismatch: {row["algorithm"]} F{row["function"]} {key}')
                cells += 1
    check('600 final Best/Mean/Std/Variance cells independently recomputed', cells == 600, 'output/final_statistics.csv')
    check('all three paper comparisons exist', all((OUT/(a+'_paper_comparison.csv')).exists() for a in ['dsp', 'dls', 'pems']), 'output/*_paper_comparison.csv')
    check('three paper ablations and team ablation statistics', all((OUT/(a+'_statistics.csv')).exists() for a in ['dsp_ablation', 'dls_ablation', 'pems_ablation', 'team_ablation']), 'output/*_ablation_statistics.csv')
    check('thirty curves, source data and selected run IDs',
          all((OUT/'curves'/f'F{i:02d}.{ext}').exists() for i in range(1, 31) for ext in ['pdf', 'svg', 'png', 'csv'])
          and (OUT/'best_curve_runs.csv').exists(), 'output/curves/ and output/best_curve_runs.csv')
    for fid in range(1, 31):
        result = json.loads((OUT/'curves'/f'F{fid:02d}.collision.json').read_text())
        # Preserve the auditor's raw verdict; review-required warnings must
        # be resolved in the signed visual acceptance record.
        text = json.dumps(result)
        check(f'F{fid:02d} collision audit has no blocking failures',
              'FIX BEFORE DELIVERY' not in text and 'NOT AUDITABLE' not in text,
              f'output/curves/F{fid:02d}.collision.json')
    visual_path = OUT/'qa/visual_acceptance.json'
    visual = json.loads(visual_path.read_text()) if visual_path.exists() else {}
    check('all rendered pages visually inspected', visual.get('accepted') is True and visual.get('pages_reviewed') == visual.get('total_pages')
          and visual.get('report_sha256')==sha(OUT/'pdf/Project2_Report.pdf'), 'output/qa/visual_acceptance.json')
    geometric = json.loads((OUT/'qa/render_audit.json').read_text())
    check('report has no clipped text', geometric['geometric_clipping_passed'], 'output/qa/render_audit.json')
    required_format = json.loads((ROOT/'protocol/report_format.json').read_text())
    check('retained DOCX template format applied and verified', required_format['status'] == 'applied_and_verified', 'protocol/report_format.json and output/template_fidelity.json')
    fidelity = json.loads((OUT/'template_fidelity.json').read_text())
    check('full Word report retains the original cover and authorized paper-style body',
          not fidelity['header_only'] and fidelity['retained_template_unchanged']
          and fidelity['title_xml_unchanged'] and fidelity['cover_geometry_unchanged']
          and fidelity['body_geometry_user_authorized'] and fidelity['body_columns']==1, 'output/template_fidelity.json')
    identity = json.loads((ROOT/'protocol/report_identity.json').read_text())
    docx = OUT/'Project2_Report.docx'
    check('editable final Word report exists', docx.exists(), 'output/Project2_Report.docx')
    with zipfile.ZipFile(docx) as z, zipfile.ZipFile(ROOT/'source/template/实验报告模板.docx') as source:
        check('all opaque template parts remain byte-identical',
              all(z.read(name) == source.read(name) for name in fidelity['preserve_only_parts']), 'DOCX package comparison')
        document = ET.fromstring(z.read('word/document.xml'))
        docx_text = ''.join(document.itertext())
        core = ET.fromstring(z.read('docProps/core.xml'))
        values = {e.tag.split('}')[-1]: e.text for e in core}
        check('Word author and last editor identity', values.get('creator') == values.get('lastModifiedBy') == '殷明骏', 'DOCX core properties')
        check('Word optional metadata and comments removed',set(values)<= {'title','creator','lastModifiedBy'} and len(ET.fromstring(z.read('docProps/app.xml')))==0 and not any('/comments' in n for n in z.namelist()),'DOCX core, application properties and comments')
        check('all four bilingual members and corrected IDs appear',
              all(all(m[k] in docx_text for k in ['chinese', 'english', 'student_id']) for m in identity['members']), 'DOCX opening information fields')
        check('English course college class and bilingual teacher appear',
              all(identity[k] in docx_text for k in ['course_english','tutor_chinese','tutor_english','college_english','class_english']), 'DOCX opening information fields')
        visible = ''.join(t.text or '' for t in document.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
        for name in [identity['tutor_chinese']]+[m['chinese'] for m in identity['members']]:
            visible = visible.replace(name, '')
        import re
        check('only personal names remain Chinese in English report', not re.search(r'[\u3400-\u9fff]', visible), 'DOCX full text language audit')
    report = OUT/'pdf/Project2_Report.pdf'
    reader = PdfReader(report)
    check('report author and empty optional metadata', reader.metadata.get('/Author') == '殷明骏' and all(not reader.metadata.get(k) or isinstance(reader.metadata.get(k),NullObject) for k in ['/Creator','/Producer','/Subject','/Keywords']), 'output/pdf/Project2_Report.pdf metadata')
    check('report XMP removed','/Metadata' not in reader.trailer['/Root'],'output/pdf/Project2_Report.pdf catalog')
    check('report student ID', '202483890029' in (reader.pages[0].extract_text() or ''), 'output/pdf/Project2_Report.pdf opening')
    all_text = '\n'.join(page.extract_text() or '' for page in reader.pages)
    check('report includes identity and three algorithms', all(t in all_text for t in ['殷明骏', '202483890029', 'DSPDE', 'DLS-DE', 'PEMS-DE', 'PGE-DE']), 'output/pdf/Project2_Report.pdf text')
    check('report has editable Markdown source', (OUT/'Project2_Report.md').exists(), 'output/Project2_Report.md')
    check('final PDF includes four member IDs', all(m['student_id'] in all_text for m in identity['members']), 'output/pdf/Project2_Report.pdf')
    verdict = all(r['passed'] for r in requirements)
    audit = dict(author='殷明骏', student_id='202483890029', requirements=requirements,
                 all_requirements_passed=verdict, status='verified_ready_to_package' if verdict else 'incomplete')
    (OUT/'completion_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n')
    if not verdict:
        print(json.dumps([r for r in requirements if not r['passed']], ensure_ascii=False, indent=2))
        sys.exit(1)
    # Runtime caches, invalid initial attempts and rendered QA pages are not
    # submission materials. Their diagnostic summaries remain included.
    def include(path):
        parts = path.relative_to(ROOT).parts
        if any(p in {'.venv', '__pycache__', 'pems_native', '.pytest_cache'} for p in parts):
            return False
        if parts[:2] == ('output','qa') and len(parts)>2 and parts[2] in ('pages','paper_revision'):
            return False
        if parts[0] == 'template_work':
            return False
        if path.name in {'RUN_STATE.md', 'report_body.pdf', 'pipeline_status.json', 'package_validation.json', 'package_project2.log', 'paper_package.log'} or path.suffix in {'.pyc', '.tmp'}:
            return False
        return True
    files = sorted(p for p in ROOT.rglob('*') if p.is_file() and include(p) and p.name != 'delivery_manifest.json')
    manifest = dict(author='殷明骏', student_id='202483890029',
                    files={str(p.relative_to(ROOT)): sha(p) for p in files})
    (ROOT/'delivery_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    files.append(ROOT/'delivery_manifest.json')
    target = ROOT.parent/'Project2_殷明骏_202483890029_Final.zip'
    temporary = target.with_suffix('.tmp')
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for p in files:
            archive.write(p, 'Project2/'+str(p.relative_to(ROOT)))
    with zipfile.ZipFile(temporary) as archive:
        assert archive.testzip() is None
        mismatches = [name for name, value in manifest['files'].items()
                      if hashlib.sha256(archive.read('Project2/'+name)).hexdigest() != value]
        assert not mismatches
    temporary.replace(target)
    check_data = dict(author='殷明骏', student_id='202483890029', archive=target.name,
                      files=len(files), crc_passed=True, all_file_hashes_match=True,
                      archive_sha256=sha(target), bytes=target.stat().st_size)
    (OUT/'package_validation.json').write_text(json.dumps(check_data, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(check_data, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
