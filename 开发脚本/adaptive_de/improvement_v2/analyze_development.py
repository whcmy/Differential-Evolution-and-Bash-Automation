"""Complete development-set comparison, without confirmation claims. Author: 殷明骏."""
from pathlib import Path
import json
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from analyze_adaptive_de import load, ranks, csv_write


def main():
    local=Path(__file__).parent
    new=load(local/'results/development')
    assert len(new)==300
    methods=['DE','DSPDE','DLSDE','PEMSDE','TEAM','APE','DLC','DUAL']
    old=[r for r in load(ROOT/'results/common_benchmark') if r['algorithm'] in methods and r['run']<=5]
    ape=[r for r in load(ROOT/'improvement/results/development_v1') if r['algorithm']=='APE']
    rows=old+ape+new
    table=[]
    for fid in range(1,31):
        stats=[]
        for method in methods:
            group=sorted([r for r in rows if r['function']==fid and r['algorithm']==method],key=lambda r:r['run'])
            assert len(group)==5 and [r['run'] for r in group]==list(range(1,6))
            values=np.asarray([r['error'] for r in group])
            stats.append(dict(function=fid,algorithm=method,n=5,best=float(values.min()),
                              mean=float(values.mean()),std=float(values.std(ddof=1))))
        for stat,rank in zip(stats,ranks([r['mean'] for r in stats])):stat['rank']=float(rank)
        table.extend(stats)
    output=local/'analysis';output.mkdir(exist_ok=True)
    csv_write(output/'development_statistics.csv',table)
    ranking=sorted([dict(algorithm=a,mean_rank=float(np.mean([r['rank'] for r in table if r['algorithm']==a]))) for a in methods],key=lambda r:r['mean_rank'])
    comparisons=[]
    for candidate in ['DLC','DUAL']:
        for control in ['DE','DLSDE','PEMSDE','TEAM','APE']:
            a=np.array([next(r['mean'] for r in table if r['function']==fid and r['algorithm']==candidate) for fid in range(1,31)])
            b=np.array([next(r['mean'] for r in table if r['function']==fid and r['algorithm']==control) for fid in range(1,31)])
            tie=np.isclose(a,b,atol=1e-8,rtol=1e-10)
            comparisons.append(dict(candidate=candidate,control=control,mean_lower=int(((a<b)&~tie).sum()),
                                    mean_tied=int(tie.sum()),mean_higher=int(((a>b)&~tie).sum())))
    result=dict(author='殷明骏',scope='All thirty functions, five historical development seeds; no confirmation or significance claim',
                rankings=ranking,comparisons=comparisons)
    (output/'development_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    csv_write(output/'development_comparisons.csv',comparisons)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
