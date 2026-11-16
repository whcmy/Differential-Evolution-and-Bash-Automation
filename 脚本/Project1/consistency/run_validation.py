"""Independent evaluator reruns and a source-matched published basic-DE control. Author: 殷明骏."""
from pathlib import Path
import os, sys, json, hashlib, ctypes, subprocess, zipfile, csv, time
for name in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']: os.environ[name]='1'
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
from de import minimize

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,o):p.write_text(json.dumps(o,indent=2,ensure_ascii=False,allow_nan=False))
def prepare():
    work=ROOT/'native';work.mkdir(exist_ok=True)
    src=ROOT.parent/'reference/cec2014_audit'
    with zipfile.ZipFile(src/'cec14-c-code.zip') as z:
        for n in z.namelist():
            b=Path(n).name
            if '/input_data/' in n and b and (b.startswith('shift_data_') or '_D10.txt' in b):
                d=work/'input_data';d.mkdir(exist_ok=True);(d/b).write_bytes(z.read(n))
    original=(src/'official_cec14_test_func.cpp').read_text()
    portable=original.replace('#include <WINDOWS.H>','').replace('%Lf','%lf')
    (work/'portable.cpp').write_text(portable)
    (work/'wrapper.cpp').write_text('''#include "portable.cpp"
double *OShift=nullptr,*M=nullptr,*y=nullptr,*z=nullptr,*x_bound=nullptr;
int ini_flag=0,n_flag=0,func_flag=0,*SS=nullptr;
extern "C" double evaluate(double *x,int fid){double f;cec14_test_func(x,&f,10,1,fid);return f;}
''')
    subprocess.run(['g++','-O2','-fPIC','-shared',str(work/'wrapper.cpp'),'-o',str(work/'cec14.so')],check=True)

def initialize():
    global LIB, JCLASS
    os.chdir(ROOT/'native')
    LIB=ctypes.CDLL(str(ROOT/'native/cec14.so'))
    LIB.evaluate.argtypes=[ctypes.POINTER(ctypes.c_double),ctypes.c_int];LIB.evaluate.restype=ctypes.c_double
    import jpype
    jpype.startJVM(classpath=[str(ROOT/'java')])
    JCLASS=jpype.JClass('benchmarks.problemsImplementation.CEC2014.CEC2014TestFuncRotInvStudy')

def official(x,fid):
    x=np.ascontiguousarray(x,dtype=np.float64)
    return LIB.evaluate(x.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),fid)

def paper_de(obj,seed):
    # Match SOS DE("ro",'b'): mutually distinct donors may include target;
    # strict generational replacement, toroidal repair after crossover.
    rng=np.random.default_rng(seed);n=10;d=10;F=.7;CR=.3
    pop=rng.uniform(-100,100,(n,d));fit=np.array([obj(x) for x in pop]);fes=n;hist=[(fes,float(fit.min()))]
    while fes<50000:
        donors=np.array([rng.choice(n,3,replace=False) for _ in range(n)])
        mutant=pop[donors[:,0]]+F*(pop[donors[:,1]]-pop[donors[:,2]])
        mandatory=rng.integers(d,size=n);mask=rng.random((n,d))<CR;mask[np.arange(n),mandatory]=True
        trial=np.where(mask,mutant,pop)
        unit=(trial+100)/200
        unit=np.where(unit>1,unit-np.trunc(unit),np.where(unit<0,1-np.abs(unit-np.trunc(unit)),unit))
        trial=unit*200-100
        values=np.array([obj(x) for x in trial]);accepted=values<fit
        pop[accepted]=trial[accepted];fit[accepted]=values[accepted];fes+=n
        if fes%1000==0 or fes==50000:hist.append((fes,float(fit.min())))
    k=fit.argmin();return pop[k],float(fit[k]),fes,hist

def one(task):
    track,fid,run=task;t=time.perf_counter()
    if track=='official':
        old=json.loads((ROOT.parent/'results'/f'F{fid:02d}_run{run:02d}.json').read_text())
        seed=old['seed'];calls=0
        def obj(x):
            nonlocal calls;calls+=1;return official(x,fid)
        r=minimize(obj,[(-100,100)]*10,seed=seed)
        x,fun,fes,hist=r.x,r.fun,r.nfev,r.history
    else:
        seed=int(np.random.SeedSequence([20261116,2019,fid,run]).generate_state(1)[0])
        j=JCLASS(10,fid,0);calls=0
        def obj(x):
            nonlocal calls;calls+=1;return float(j.f(x.tolist()))
        x,fun,fes,hist=paper_de(obj,seed)
    assert calls==fes
    check=obj(x);assert np.isclose(check,fun,rtol=1e-12,atol=1e-8)
    return dict(track=track,function=fid,run=run,seed=seed,nfev=fes,best_fitness=fun,optimum=fid*100.,error=abs(fun-fid*100),best_x=x.tolist(),history=hist,recomputed_fitness=check,verification_fes=1,seconds=time.perf_counter()-t)

def main():
    prepare()
    frozen={str(p.relative_to(ROOT.parent)):digest(p) for p in sorted((ROOT.parent/'results').glob('*.json'))}
    frozen.update({p:digest(ROOT.parent/p) for p in ['de.py','run_experiments.py']})
    write(ROOT/'frozen_inputs.json',frozen)
    tracks={'official':range(1,31),'paper': [i for i in range(1,31) if i not in [8,10]]}
    config=dict(author='殷明骏',original_records=600,official_records=600,paper_records=560,paper_runs=20,paper_functions=list(tracks['paper']),paper_fes=50000,paper_NP=10,paper_F=.7,paper_CR=.3,paper_rotation=0,official_fes=100000,source_sha256={str(p.relative_to(ROOT)):digest(p) for p in (ROOT/'source').glob('*') if p.is_file()},optimizer_sha256=digest(ROOT.parent/'de.py'))
    write(ROOT/'manifest.json',config)
    tasks=[]
    for tr,fs in tracks.items():
        out=ROOT/f'results_{tr}';out.mkdir(exist_ok=True)
        tasks.extend((tr,f,r) for f in fs for r in range(1,21) if not (out/f'F{f:02d}_run{r:02d}.json').exists())
    with ProcessPoolExecutor(max_workers=16,initializer=initialize) as pool:
        futures=[pool.submit(one,t) for t in tasks]
        for i,ft in enumerate(as_completed(futures),1):
            r=ft.result();write(ROOT/f"results_{r['track']}"/f"F{r['function']:02d}_run{r['run']:02d}.json",r)
            if i%20==0:print(i,len(tasks),r['track'],r['function'],round(r['seconds'],2),flush=True)
    assert all(digest(ROOT.parent/p)==h for p,h in frozen.items())
    print('COMPLETE; original data and optimizer hashes unchanged',flush=True)
if __name__=='__main__':main()
