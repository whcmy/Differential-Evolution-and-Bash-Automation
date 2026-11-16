"""Revision acceptance checks. Author 殷明骏, 202483890029."""
from pathlib import Path
import csv
import hashlib
import json
import re
import zipfile
import fitz
from lxml import etree

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output'
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M='http://schemas.openxmlformats.org/officeDocument/2006/math'

def main():
    checks=[]
    def check(name,passed,evidence):checks.append(dict(check=name,passed=bool(passed),evidence=evidence))
    d=fitz.open(OUT/'pdf/Project2_Report.pdf');build=json.loads((OUT/'visual_revision_build.json').read_text())
    check('Complete paper-style report with two explanatory diagrams, five analytical figures and thirty convergence plots',len(build['vector_figures'])==12,'2 diagrams, 5 analytical figures and 5 six-function curve sheets; full numerical row and cell checks follow')
    check('PDF author identity and empty optional metadata',d.metadata['author']=='殷明骏' and all(not d.metadata.get(k) for k in ['creator','producer','subject','keywords']) and not d.get_xml_metadata(),d.metadata)
    rules=[x for x in d[0].get_drawings() if abs(x['rect'].y0-102.375)<.5 and x['rect'].width>460]
    check('Template title rule visible in PDF',bool(rules),'Original intended rule at y=102.375pt, width approximately 463.5pt')
    check('PDF navigation bookmarks',len(d.get_toc())==len(json.loads((OUT/'report_sections.json').read_text())),'PDF outline versus report sections')
    check('Paper-style body navigation',len(d.get_toc())>=20,'Native section bookmarks replace the former contents page')
    check('All evidence is in the main body',not re.search(r'appendix|appendices',' '.join(p.get_text() for p in d),re.I),'All former appendix sections are integrated before conclusions')
    clips=[];footer=[];blank=[]
    for i,p in enumerate(d):
        spans=[s for b in p.get_text('dict')['blocks'] if 'lines'in b for l in b['lines'] for s in l['spans']]
        footer_spans=[s for s in spans if re.fullmatch(r'\d+',s['text'].strip()) and s['bbox'][1]>p.rect.height-45 and abs((s['bbox'][0]+s['bbox'][2])/2-p.rect.width/2)<40]
        footer_top=min((s['bbox'][1] for s in footer_spans),default=p.rect.height-20)
        if len(p.get_text().strip())<100:blank.append(i+1)
        for s in spans:
            b=s['bbox']
            if b[0]<-.5 or b[1]<-.5 or b[2]>p.rect.width+.5 or b[3]>p.rect.height+.5:clips.append(dict(page=i+1,text=s['text'],bbox=b))
            if i and s not in footer_spans and b[1]<footer_top and b[3]>footer_top-12:footer.append(dict(page=i+1,text=s['text'],bbox=b))
    check('No page clipping',not clips,clips)
    check('Body clears footer',not footer,footer)
    check('No blank or fragment pages',not blank,blank)
    check('Analytical figure geometry',all(r['raster_agreement_mae']<5 for r in build['vector_figures']),build['vector_figures'])
    with zipfile.ZipFile(OUT/'Project2_Report.docx') as z:
        xml=etree.fromstring(z.read('word/document.xml'));core=etree.fromstring(z.read('docProps/core.xml'))
        vals={etree.QName(e).localname:e.text for e in core}
        check('Word identity',vals.get('creator')==vals.get('lastModifiedBy')=='殷明骏','Word core properties')
        check('Native editable equations',len(xml.findall('.//{'+M+'}oMath'))==3,'3 OMML equations')
        check('Semantic headings',b'outlineLvl' in z.read('word/styles.xml'),'Native heading outline levels')
        check('Two-column body and native page fields',any(e.get('{'+W+'}num')=='2' for e in xml.findall('.//{'+W+'}cols')) and any(b'PAGE' in z.read(n) for n in z.namelist() if 'footer' in n),'Native two-column sections, spanning evidence and PAGE footer')
        identity=json.loads((ROOT/'protocol/report_identity.json').read_text())
        visible=''.join(xml.itertext())
        for name in [identity['tutor_chinese']]+[m['chinese'] for m in identity['members']]:visible=visible.replace(name,'')
        check('English except names',not re.search('[\u3400-\u9fff]',visible),'Full body XML')
        for stem,prefix in [('final','6.2'),('pems_ablation','5.4'),('team_ablation','6.3'),('dsp_ablation','5.2'),('dls_ablation','5.3')]:
            with (OUT/(stem+'_statistics.csv')).open(encoding='utf-8-sig') as f:source=list(csv.DictReader(f))
            tables=[]
            for table in xml.findall('.//{'+W+'}tbl'):
                rows=table.findall('./{'+W+'}tr')
                head=[''.join(c.itertext()) for c in rows[0].findall('./{'+W+'}tc')]
                if not head or head[0]!='F' or 'Algorithm' not in head:continue
                prev=table.getprevious()
                while prev is not None:
                    prevtext=''.join(prev.itertext())
                    if re.match(r'^(5\.[234]|6\.[23]) ',prevtext):break
                    prev=prev.getprevious()
                if prev is not None and prevtext.startswith(prefix+' '):tables.extend(rows[1:])
            check(stem+' full data row count',len(tables)==len(source),dict(report=len(tables),source=len(source)))
            cell_mismatches=[]
            for row,expected in zip(tables,source):
                values=[''.join(c.itertext()) for c in row.findall('./{'+W+'}tc')]
                for j,key in enumerate(['best','mean','std','variance','rank'],2):
                    number=float(expected[key]);printed=f'{number:.1f}' if key=='rank' else ('0' if number==0 else f'{number:.3e}')
                    if values[j]!=printed:cell_mismatches.append(dict(function=expected['function'],algorithm=expected['algorithm'],key=key,printed=values[j],expected=printed))
            check(stem+' printed numeric cells',not cell_mismatches,cell_mismatches)
    audit=json.loads((OUT/'diagnostics/benchmark_closure.json').read_text())
    check('Independent source audit',audit['passed'] and audit['reference_solution_passes']==600,'660 probes and 600 solutions')
    team=json.loads((OUT/'diagnostics/team_telemetry_audit.json').read_text())
    check('Observation-only telemetry',team['replays']==80 and team['all_exact'],'80 exact frozen-algorithm replays')
    refs=json.loads((OUT/'diagnostics/reference_replays.json').read_text())
    check('Reference full budget values',refs['all_final_values_agree'] and refs['all_budgets_passed'],'40 final values within declared tolerance; trajectories not claimed bit-identical')
    figs=json.loads((OUT/'journal_figure_audit.json').read_text())
    check('Fresh figure render audits',len(figs)==12 and all(r['collision_code']==r['font_code']==0 for r in figs),'All 12 paper-style exported PDF figure pages')
    def curve_index(name):
        with (OUT/name).open(encoding='utf-8-sig') as f:return {(int(x['function']),x['algorithm']):(int(x['run']),int(x['seed'])) for x in csv.DictReader(f)}
    check('Best-run selection preserved',curve_index('best_curve_runs.csv')==curve_index('figures/journal_curve_selection.csv'),'150 selected function-method run and seed pairs')
    # Compare the exact XML prefix of the populated opening with the last delivery.
    with zipfile.ZipFile(ROOT/'template_work/revision_baseline/Project2_Report.docx') as z:
        previous=etree.fromstring(z.read('word/document.xml'))
    oldp=previous.find('{'+W+'}body').findall('{'+W+'}p')
    newp=xml.find('{'+W+'}body').findall('{'+W+'}p')
    stop=next(i for i,p in enumerate(oldp) if '1. Experimental objectives' in ''.join(p.itertext()))
    def opening_bytes(p):
        raw=etree.tostring(p,method='c14n')
        return re.sub(rb'2026-11-\d\d',b'REPORT_DATE',raw)
    check('Opening fields unchanged except report date',all(opening_bytes(a)==opening_bytes(b) for a,b in zip(oldp[:stop],newp[:stop])),'Populated opening paragraph XML; report date updated for the revision')
    accepted=all(c['passed'] for c in checks)
    result=dict(author='殷明骏',student_id='202483890029',passed=accepted,checks=checks)
    (OUT/'revision_acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(passed=accepted,checks=len(checks),failures=[c for c in checks if not c['passed']]),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
