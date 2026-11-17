"""Observation-only replays of frozen PGE-DE. Author 殷明骏, 202483890029."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import csv
import hashlib
import json
import sys
import numpy as np
from opfunu.cec_based import cec2014

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/diagnostics/team_replays'
sys.path.insert(0,str(ROOT/'code'))

def instrument():
    source=(ROOT/'code/team_de.py').read_text()
    source=source.replace('    while fes < max_fes:', '''    telemetry=[]
    interval_escape=interval_accept=interval_count=0
    while fes < max_fes:''',1)
    source=source.replace('        previous_fit = old_fit','''        previous_fit = old_fit
        interval_escape += len(escaped)
        interval_accept += int(accepted.sum())
        interval_count += count
        if (fes+count) % 10000 == 0 or fes+count == max_fes:
            telemetry.append(dict(fes=fes+count,
                normalized_rms_diversity=float(np.sqrt(np.var(x,axis=0).mean())/200),
                boundary_fraction=float(np.mean(np.isclose(x,lo,atol=1e-10,rtol=0)|np.isclose(x,hi,atol=1e-10,rtol=0))),
                accepted_fraction=interval_accept/interval_count,
                escape_fraction=interval_escape/interval_count,
                best_error=float(fit.min()),
                guide_distance=float(np.sqrt(np.mean((guide-x[:count])**2))/200)))
            interval_escape=interval_accept=interval_count=0''',1)
    source=source.replace('history=history, diagnostics=diag)', 'history=history, diagnostics=diag, telemetry=telemetry)')
    assert 'telemetry=telemetry' in source
    namespace={'__name__':'observed_team'}
    exec(compile(source,'<observation-only team replay>','exec'),namespace)
    return namespace['minimize']

def one(task):
    fid,variant,run=task
    saved=json.loads((ROOT/'results/common_benchmark'/variant/f'F{fid:02d}_run{run:02d}.json').read_text())
    objective=getattr(cec2014,f'F{fid}2014')(ndim=10)
    result=instrument()(objective.evaluate,[(-100.,100.)]*10,max_fes=100000,population_size=100,
                        seed=saved['seed'],variant=variant,trace_interval=1000)
    exact=result['fun']==saved['fun'] and np.array_equal(result['x'],saved['x']) and result['history']==saved['history']
    if not exact: raise RuntimeError(f'replay mismatch {task}')
    for t in result['telemetry']: t['best_error']=max(0,t['best_error']-100*fid)
    result.update(function=fid,variant=variant,run=run,seed=saved['seed'],exact_replay=exact,
                  source_sha256=hashlib.sha256((ROOT/'code/team_de.py').read_bytes()).hexdigest())
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    # Largest absolute gain and loss in the original TEAM versus DE mean errors.
    # This is a post hoc diagnostic subset, not independent validation.
    tasks=[(fid,v,r) for fid in [11,29] for v in ['TEAM','TEAM_no_peg'] for r in range(1,21)]
    pending=[t for t in tasks if not (OUT/f'F{t[0]:02d}_{t[1]}_run{t[2]:02d}.json').exists()]
    with ProcessPoolExecutor(max_workers=12) as pool:
        for i,future in enumerate(as_completed([pool.submit(one,t) for t in pending]),1):
            r=future.result()
            (OUT/f"F{r['function']:02d}_{r['variant']}_run{r['run']:02d}.json").write_text(json.dumps(r,indent=2)+'\n')
            if i%10==0: print(f'Exact telemetry replays {i}/{len(pending)}',flush=True)
    records=[json.loads(p.read_text()) for p in sorted(OUT.glob('*.json'))]
    rows=[]
    for r in records:
        for t in r['telemetry']:
            rows.append(dict(function=r['function'],algorithm=r['variant'],run=r['run'],**t))
    with (OUT.parent/'team_telemetry.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
    summary=dict(author='殷明骏',student_id='202483890029',replays=len(records),
                 all_exact=all(r['exact_replay'] for r in records),functions=[11,29],runs_per_group=20,
                 selection='Post hoc largest absolute TEAM-versus-DE mean gain and loss; original outcomes retained',
                 interpretation='Observational telemetry supports a bounded process diagnosis; no parameter tuning or independent generalization claim')
    (OUT.parent/'team_telemetry_audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
