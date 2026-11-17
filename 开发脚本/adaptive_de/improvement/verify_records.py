"""Independent per-solution confirmation checks. Author: 殷明骏."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
from opfunu.cec_based import cec2014


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('results',type=Path)
    p.add_argument('--expected',type=int,required=True)
    a=p.parse_args()
    manifest=json.loads((a.results/'manifest.json').read_text())
    cfg=manifest['config']
    seen=set();records=0;max_abs=0.
    problems={fid:getattr(cec2014,f'F{fid}2014')(ndim=10) for fid in cfg['functions']}
    for path in a.results.rglob('*_run*.json'):
        r=json.loads(path.read_text())
        key=r['algorithm'],r['function'],r['run']
        assert key not in seen
        seen.add(key)
        assert key[0] in cfg['algorithms'] and key[1] in cfg['functions'] and 1<=key[2]<=cfg['runs']
        assert r['nfev']==cfg['max_fes'] and r['audit_evaluations']==1
        expected=int(np.random.SeedSequence([cfg['seed'],2014,r['function'],r['run']]).generate_state(1)[0])
        assert r['seed']==expected
        objective=problems[r['function']]
        x=np.asarray(r['x'],float)
        assert x.shape==(10,) and np.isfinite(x).all()
        assert np.all(x>=objective.lb) and np.all(x<=objective.ub)
        value=float(objective.evaluate(x));max_abs=max(max_abs,abs(value-r['fun']))
        assert np.isclose(value,r['fun'],atol=1e-9,rtol=1e-12)
        assert np.isclose(max(0.,r['fun']-r['optimum']),r['error'],atol=1e-9,rtol=1e-12)
        h=np.asarray(r['history'],float)
        assert h.shape[1]==2 and np.isfinite(h).all()
        assert h[0,0]==100 and h[-1,0]==cfg['max_fes']
        assert np.all(np.diff(h[:,0])>0) and np.all(np.diff(h[:,1])<=0)
        assert h[-1,1]==r['fun']
        records+=1
    expected={(algo,fid,run) for algo in cfg['algorithms'] for fid in cfg['functions'] for run in range(1,cfg['runs']+1)}
    assert seen==expected and records==a.expected and manifest['record_count']==a.expected
    for name,digest in cfg['source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    original=json.loads((ROOT/'improvement/frozen_original_sha256.json').read_text())
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in original['sha256'].items())
    result=dict(author='殷明骏',passed=True,records=records,complete_matrix=True,
                all_budgets_exact=True,all_solutions_reevaluated=True,
                all_histories_checked=True,all_seeds_checked=True,
                source_hashes_match=True,frozen_original_files_unchanged=len(original['sha256']),
                max_absolute_reevaluation_difference=max_abs)
    target=a.results/'verification.json';target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
