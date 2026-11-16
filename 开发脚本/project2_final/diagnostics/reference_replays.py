"""Reference-evaluator trajectory checks. Author 殷明骏, 202483890029."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
from concurrent.futures import ProcessPoolExecutor, as_completed
import ctypes
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
from dls_de import minimize

def one(task):
    fid,run=task
    saved=json.loads((ROOT/'legacy/dls_reference/dls_de'/f'F{fid:02d}_run{run:02d}.json').read_text())
    work=ROOT/'template_work/native_cec14';os.chdir(work)
    lib=ctypes.CDLL(str(work/'cec14.so'));lib.evaluate_cec14.argtypes=[ctypes.POINTER(ctypes.c_double),ctypes.c_int];lib.evaluate_cec14.restype=ctypes.c_double
    calls=0
    def objective(x):
        nonlocal calls
        calls+=1;x=np.ascontiguousarray(x,dtype=np.float64)
        return lib.evaluate_cec14(x.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),fid)
    r=minimize(objective,[(-100.,100.)]*10,max_fes=100000,seed=saved['seed'])
    exact=r.fun==saved['best_fitness'] and np.array_equal(r.x,saved['best_x']) and r.history==saved['history']
    a,b=np.asarray(r.history),np.asarray(saved['history'])
    return dict(function=fid,run=run,seed=saved['seed'],nfev=r.nfev,observed_calls=calls,exact=bool(exact),
                original_fitness=saved['best_fitness'],replay_fitness=r.fun,absolute_difference=abs(r.fun-saved['best_fitness']),
                fitness_agrees=bool(np.isclose(r.fun,saved['best_fitness'],rtol=1e-10,atol=1e-8)),
                solution_max_abs_difference=float(np.max(abs(r.x-np.array(saved['best_x'])))),
                history_shapes_match=a.shape==b.shape,
                history_max_abs_difference=float(np.max(abs(a-b))) if a.shape==b.shape else None,
                history_agrees=bool(np.allclose(a,b,rtol=1e-10,atol=1e-8)) if a.shape==b.shape else False)

def main():
    tasks=[(f,r) for f in [29,30] for r in range(1,21)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(one,tasks))
    audit=dict(author='殷明骏',student_id='202483890029',replays=40,functions=[29,30],
               all_exact=all(r['exact'] for r in results),all_budgets_passed=all(r['nfev']==r['observed_calls']==100000 for r in results),
               all_final_values_agree=all(r['fitness_agrees'] for r in results),
               all_histories_agree=all(r['history_agrees'] for r in results),
               results=results)
    (ROOT/'output/diagnostics/reference_replays.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print({k:v for k,v in audit.items() if k!='results'})

if __name__=='__main__':main()
