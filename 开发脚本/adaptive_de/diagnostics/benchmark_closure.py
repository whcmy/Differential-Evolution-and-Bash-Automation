"""Independent CEC2014 source audit. Author: 殷明骏, 202483890029."""
from pathlib import Path
import csv
import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import zipfile
import numpy as np
from opfunu.cec_based import cec2014

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'source/cec2014_reference'
OUT = ROOT/'output/diagnostics'
WORK = ROOT/'template_work/native_cec14'

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def write_csv(path, rows):
    with Path(path).open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def build_library():
    WORK.mkdir(parents=True, exist_ok=True)
    data=WORK/'input_data'; data.mkdir(exist_ok=True)
    with zipfile.ZipFile(SOURCE/'cec14-c-code.zip') as z:
        for name in z.namelist():
            base=Path(name).name
            if '/input_data/' in name and base and (base.startswith('shift_data_') or '_D10.txt' in base):
                (data/base).write_bytes(z.read(name))
    original=(SOURCE/'official_cec14_test_func.cpp').read_text()
    # The Windows include is unused by the evaluator; retain the original file.
    portable=original.replace('#include <WINDOWS.H>', '// Unused Windows header omitted for Linux compilation')
    # MSVC treats long double as double. On GCC, %Lf would write 16 bytes
    # through a double*; use the correct double scanner on Linux.
    assert portable.count('%Lf') == 5
    portable=portable.replace('%Lf','%lf')
    (WORK/'portable_cec14.cpp').write_text(portable)
    wrapper='''#include "portable_cec14.cpp"
double *OShift=nullptr,*M=nullptr,*y=nullptr,*z=nullptr,*x_bound=nullptr;
int ini_flag=0,n_flag=0,func_flag=0,*SS=nullptr;
extern "C" double evaluate_cec14(double *x, int fid) {
  double f; cec14_test_func(x, &f, 10, 1, fid); return f;
}
'''
    (WORK/'wrapper.cpp').write_text(wrapper)
    subprocess.run(['g++','-std=c++11','-O2','-fPIC','-shared',str(WORK/'wrapper.cpp'),'-o',str(WORK/'cec14.so')],check=True)
    lib=ctypes.CDLL(str(WORK/'cec14.so'))
    lib.evaluate_cec14.argtypes=[ctypes.POINTER(ctypes.c_double),ctypes.c_int]
    lib.evaluate_cec14.restype=ctypes.c_double
    def evaluate(x,fid):
        x=np.ascontiguousarray(x,dtype=np.float64)
        return lib.evaluate_cec14(x.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),fid)
    return evaluate

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    old=ROOT.parent/'dls_de_reference'
    target=ROOT/'legacy/dls_reference'
    if not target.exists(): shutil.copytree(old/'results_reference',target)
    for n in ['run_reference.py','benchmark_audit.py','reference/benchmark_audit.json','reference/benchmark_pointwise_audit.csv']:
        shutil.copy2(old/n,SOURCE/Path(n).name)
    evaluate=build_library()
    os.chdir(WORK)
    points=np.random.default_rng(2014).uniform(-100,100,(20,10))
    probes=[]; checks=[]; comparisons=[]
    for fid in range(1,31):
        f=getattr(cec2014,f'F{fid}2014')(ndim=10)
        xs=np.vstack((points,np.zeros(10),f.x_global))
        a=np.array([f.evaluate(x) for x in xs]); b=np.array([evaluate(x,fid) for x in xs])
        probes.append(dict(function=fid,points=len(xs),mismatches=int((~np.isclose(a,b,rtol=1e-10,atol=1e-8)).sum()),
                           max_abs_difference=float(abs(a-b).max()),opfunu_zero=float(a[-2]),official_zero=float(b[-2])))
        ref=[]; protocol=[]
        for run in range(1,21):
            r=json.loads((target/'dls_de'/f'F{fid:02d}_run{run:02d}.json').read_text())
            c=json.loads((ROOT/'legacy/dls_native/results/dls_de'/f'F{fid:02d}_run{run:02d}.json').read_text())
            actual=evaluate(r['best_x'],fid)
            checks.append(dict(function=fid,run=run,seed=r['seed'],stored=r['best_fitness'],official=actual,
                               difference=actual-r['best_fitness'],passed=bool(np.isclose(actual,r['best_fitness'],rtol=1e-10,atol=1e-8)),
                               matched_seed=r['seed']==c['seed'],budget_pass=r['nfev']==c['nfev']==100000))
            ref.append(r['error']); protocol.append(c['error'])
        comparisons.append(dict(function=fid,opfunu_mean=float(np.mean(protocol)),opfunu_std=float(np.std(protocol,ddof=1)),
                                cpp_mean=float(np.mean(ref)),cpp_std=float(np.std(ref,ddof=1)),
                                cpp_median=float(np.median(ref)),cpp_worst=float(max(ref)),n=20))
    with (ROOT/'source/paper_tables/dlsde_table12.csv').open(encoding='utf-8-sig') as f:
        papers={int(r['function']):r for r in csv.DictReader(f)}
    for r in comparisons:
        p=papers[r['function']]; r['paper_mean']=float(p['paper_mean']); r['paper_std']=float(p['paper_std'])
        r['opfunu_difference']=r['opfunu_mean']-r['paper_mean']; r['cpp_difference']=r['cpp_mean']-r['paper_mean']
    write_csv(OUT/'cec2014_pointwise.csv',probes)
    write_csv(OUT/'dls_reference_solution_checks.csv',checks)
    write_csv(OUT/'dls_evaluator_comparison.csv',comparisons)
    manifest=json.loads((target/'manifest.json').read_text())
    hash_match=sha(ROOT/'code/dls_de.py')==manifest['config']['source_sha256']['dls_de.py']
    result=dict(author='殷明骏',student_id='202483890029',pointwise_probes=660,
                mismatch_functions=[r['function'] for r in probes if r['mismatches']],
                reference_records=600,reference_solution_passes=sum(r['passed'] for r in checks),
                max_reference_absolute_difference=max(abs(r['difference']) for r in checks),
                optimizer_hash_matches=hash_match,all_seeds_and_budgets_match=all(r['matched_seed'] and r['budget_pass'] for r in checks),
                original_source_sha256=sha(SOURCE/'official_cec14_test_func.cpp'),
                portability_change='Unused WINDOWS.H include removed and five fscanf %Lf specifiers corrected to %lf for double pointers on GCC; equations and original source unchanged',
                passed=hash_match and all(r['passed'] and r['matched_seed'] and r['budget_pass'] for r in checks),
                scope='Finite point and solution validation; optimizer trajectories were not all replayed under this newly compiled evaluator.')
    (OUT/'benchmark_closure.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
