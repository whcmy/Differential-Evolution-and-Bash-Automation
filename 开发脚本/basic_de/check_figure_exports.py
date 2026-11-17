"""Inspect exported scientific figures. Author: 殷明骏."""
from pathlib import Path
import json, subprocess, sys
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output';QA=OUT/'qa';QA.mkdir(exist_ok=True)
names=json.loads((OUT/'report_figures.json').read_text())
records=[]
for name in names:
    p=OUT/'figures'/f'{name}.pdf'
    for tool,args in [('audit_pdf_text',['--min-pt','5','--json']),('audit_figure_collisions',['--json-out',str(OUT/'figures'/f'{name}.collision.json')])]:
        cmd=[sys.executable,str(ROOT/'tools'/f'{tool}.py'),str(p)]+args
        run=subprocess.run(cmd,capture_output=True,text=True)
        records.append(dict(figure=name,tool=tool,exit_code=run.returncode,output=run.stdout))
        if run.returncode:print(name,tool,run.returncode,run.stdout[-1800:])
(QA/'figure_audits.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'figures':len(names),'audits':len(records),'failures':sum(r['exit_code']!=0 for r in records)},indent=2))
