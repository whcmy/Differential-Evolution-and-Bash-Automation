"""Descriptive development comparison; not confirmation. Author: 殷明骏."""
from pathlib import Path
import csv
import json
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analyze_project2 import ranks


def main():
    revision = Path(__file__).parent
    rows = []
    for path in (ROOT/'results/coursework').rglob('*_run*.json'):
        r = json.loads(path.read_text())
        if r['run'] <= 5 and r['algorithm'] in ['DE','DSPDE','DLSDE','PEMSDE','TEAM','TEAM_no_peg']:
            rows.append(r)
    new = [json.loads(p.read_text()) for p in (revision/'results/development_v1').rglob('*_run*.json')]
    assert len(new) == 450
    rows.extend(new)
    algorithms = ['DE','DSPDE','DLSDE','PEMSDE','TEAM','TEAM_no_peg','APE','APE_no_potential','APE_no_control']
    table=[]
    for fid in range(1,31):
        summaries=[]
        for algorithm in algorithms:
            group=sorted([r for r in rows if r['algorithm']==algorithm and r['function']==fid],key=lambda r:r['run'])
            assert len(group)==5 and [r['run'] for r in group]==list(range(1,6))
            y=np.array([r['error'] for r in group])
            summaries.append(dict(function=fid,algorithm=algorithm,n=5,mean=float(y.mean()),median=float(np.median(y)),std=float(y.std(ddof=1))))
        for row,rank in zip(summaries,ranks([r['mean'] for r in summaries])):
            row['rank']=float(rank)
        table.extend(summaries)
    output=revision/'analysis';output.mkdir(exist_ok=True)
    with (output/'development_statistics.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    ranking=sorted([dict(algorithm=a,mean_rank=float(np.mean([r['rank'] for r in table if r['algorithm']==a]))) for a in algorithms],key=lambda r:r['mean_rank'])
    result=dict(author='殷明骏',scope='development only, first five observed seeds; no superiority test',mean_ranks=ranking)
    for control in ['DE','DLSDE','TEAM','TEAM_no_peg','APE_no_potential','APE_no_control']:
        a=np.array([next(r['mean'] for r in table if r['function']==fid and r['algorithm']=='APE') for fid in range(1,31)])
        b=np.array([next(r['mean'] for r in table if r['function']==fid and r['algorithm']==control) for fid in range(1,31)])
        tied=np.isclose(a,b,atol=1e-8,rtol=1e-10)
        result[control]=dict(lower=int(((a<b)&~tied).sum()),tied=int(tied.sum()),higher=int(((a>b)&~tied).sum()))
    (output/'development_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
