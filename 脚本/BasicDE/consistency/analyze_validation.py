"""Source-matched basic-DE comparison and paired evaluator checks. Author: 殷明骏."""
from pathlib import Path
import json,csv,sys,hashlib,re
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import run_validation as rv

def write(p,rows):
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def load(track):return [json.loads(p.read_text()) for p in sorted((ROOT/('results_'+track)).glob('F*.json'))]
def main():
    a=[json.loads(p.read_text()) for p in sorted((ROOT.parent/'results').glob('F*.json'))];b=load('official');c=load('paper')
    assert len(a)==len(b)==600 and len(c)==560
    text=(ROOT/'source/rotation_extended.txt').read_text()
    table=text.split('Table 1:')[1].split('Table 2:')[0]
    ref={}
    for line in table.splitlines():
        m=re.match(r'\s*f(\d+)\s+',line)
        if not m:continue
        vals=re.findall(r'\d+\.\d+e\s*[+−-]\s*\d+',line)
        if vals:
            v=[float(x.replace(' ','').replace('−','-')) for x in vals];ref[int(m[1])]=(v[2],v[3])
    assert len(ref)==28
    write(ROOT/'published_basic_de.csv',[dict(function=f,paper_mean=m,paper_std=s,paper_runs=30,table=1) for f,(m,s) in ref.items()])
    rows=[];paired=[]
    for fid in range(1,31):
        aa=[r for r in a if r['function']==fid];bb=[r for r in b if r['function']==fid]
        x=np.array([r['error'] for r in aa]);y=np.array([r['error'] for r in bb])
        for ar,br in zip(aa,bb):
            assert ar['seed']==br['seed'] and ar['nfev']==br['nfev']==100000
            paired.append(dict(function=fid,run=ar['run'],seed=ar['seed'],opfunu_error=ar['error'],official_error=br['error']))
        rows.append(dict(function=fid,opfunu_mean=x.mean(),opfunu_std=x.std(ddof=1),official_best=y.min(),official_median=np.median(y),official_mean=y.mean(),official_worst=y.max(),official_std=y.std(ddof=1),official_variance=y.var(ddof=1),paired_log_ratio_median=np.median(np.log10((y+1e-8)/(x+1e-8)))))
    write(ROOT/'evaluator_summary.csv',rows);write(ROOT/'paired_results.csv',paired)
    comp=[]
    for fid,(pm,ps) in ref.items():
        x=np.array([r['error'] for r in c if r['function']==fid]);m=x.mean();s=x.std(ddof=1)
        # A descriptive, pre-analysis scale: numerical tolerance or one reported SD.
        rounding=0.0 if pm==0 else 0.5*10**(np.floor(np.log10(abs(pm)))-2)
        tolerance=max(1e-8,ps)+rounding
        near=bool(abs(m-pm)<=tolerance)
        comp.append(dict(function=fid,best=x.min(),median=np.median(x),mean=m,worst=x.max(),std=s,population_std=x.std(ddof=0),variance=x.var(ddof=1),paper_mean=pm,paper_std=ps,absolute_gap=abs(m-pm),paper_rounding_halfwidth=rounding,within_one_sd_without_rounding=bool(abs(m-pm)<=max(1e-8,ps)),descriptive_tolerance=tolerance,within_one_paper_sd=near,relative_mean_gap=abs(m-pm)/max(abs(pm),1e-8)))
    write(ROOT/'paper_comparison.csv',comp)
    rv.initialize()
    from opfunu.cec_based import cec2014
    probes=[];solution_checks=[]
    rng=np.random.default_rng(20261116)
    pts=np.vstack((rng.uniform(-100,100,(200,10)),np.zeros((1,10)),np.full((1,10),-100),np.full((1,10),100)))
    for fid in range(1,31):
        op=getattr(cec2014,f'F{fid}2014')(ndim=10)
        xx=np.vstack((pts,op.x_global))
        v=np.array([op.evaluate(x) for x in xx]);w=np.array([rv.official(x,fid) for x in xx])
        mismatch=~np.isclose(v,w,rtol=1e-10,atol=1e-8)
        probes.append(dict(function=fid,points=len(xx),mismatches=int(mismatch.sum()),max_abs_difference=abs(v-w).max(),max_relative_difference=(abs(v-w)/np.maximum(1,abs(w))).max()))
        for row in [r for r in b if r['function']==fid]:
            value=rv.official(row['best_x'],fid)
            solution_checks.append(dict(track='official',function=fid,run=row['run'],difference=value-row['best_fitness'],passed=bool(np.isclose(value,row['best_fitness'],rtol=1e-12,atol=1e-8))))
        if fid in ref:
            j=rv.JCLASS(10,fid,0)
            for row in [r for r in c if r['function']==fid]:
                value=j.f(row['best_x'])
                solution_checks.append(dict(track='paper',function=fid,run=row['run'],difference=value-row['best_fitness'],passed=bool(np.isclose(value,row['best_fitness'],rtol=1e-12,atol=1e-8))))
    write(ROOT/'pointwise_validation.csv',probes);write(ROOT/'solution_checks.csv',solution_checks)
    frozen=json.loads((ROOT/'frozen_inputs.json').read_text());assert all(rv.digest(ROOT.parent/p)==h for p,h in frozen.items())
    for track,rs,budget in [('official',b,100000),('paper',c,50000)]:
        for r in rs:
            assert r['nfev']==budget and r['history'][-1][0]==budget
            assert np.isfinite(r['best_x']).all() and max(r['best_x'])<=100 and min(r['best_x'])>=-100
            assert all(y[1]<=x[1] for x,y in zip(r['history'],r['history'][1:]))
    assert all(r['passed'] for r in solution_checks)
    d=dict(author='殷明骏',original_runs=600,official_runs=600,paper_runs=560,total_runs=1760,new_optimization_fes=88000000,pointwise_probes=sum(r['points'] for r in probes),mismatch_functions=[r['function'] for r in probes if r['mismatches']],saved_solutions_recomputed=len(solution_checks),all_solution_checks_pass=True,frozen_inputs_unchanged=True,paper_comparison_functions=len(comp),within_band_without_rounding=sum(r['within_one_sd_without_rounding'] for r in comp),descriptively_close_functions=[r['function'] for r in comp if r['within_one_paper_sd']],outside_descriptive_band=[r['function'] for r in comp if not r['within_one_paper_sd']],criterion='Absolute mean gap <= max(1e-8, published population standard deviation) + half a unit in the last published mean digit; descriptive scale only, not equivalence testing',paper_benchmark='Non-rotated CEC2014RotInvStudy, not the standard protocol suite; F8 and F10 excluded by the source',source_repository='https://github.com/facaraff/SOS',source_commit='cf7c793dce5b5bd04a916797dc221ed4be7751ce')
    (ROOT/'verification.json').write_text(json.dumps(d,indent=2,ensure_ascii=False));print(json.dumps(d,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
