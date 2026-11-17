"""Complete confirmation analysis with declared test families. Author: 殷明骏."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import sys
import numpy as np
from scipy.stats import friedmanchisquare, binomtest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from analyze_adaptive_de import load, summarize, compare, csv_write, ranks

MAIN = ['DE','DSPDE','DLSDE','PEMSDE','TEAM','APE']
ABLATION = ['APE','APE_no_potential','APE_no_control']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',type=Path,default=Path(__file__).parent/'results/validation')
    a=p.parse_args()
    revision=Path(__file__).parent
    contract=json.loads((revision/'validation_contract.json').read_text())
    manifest=json.loads((a.results/'manifest.json').read_text())
    cfg=manifest['config']
    assert manifest.get('record_count') == 4800
    assert cfg['seed']==contract['master_seed'] and cfg['runs']==20
    assert cfg['algorithms']==sorted(set(MAIN+ABLATION))
    assert cfg['functions']==list(range(1,31)) and cfg['max_fes']==100000 and cfg['population_size']==100
    for name,digest in contract['source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
        assert cfg['source_sha256'][name]==digest
    rows=load(a.results)
    assert len(rows)==4800
    output=revision/'analysis';output.mkdir(exist_ok=True)
    main_stats=summarize(rows,MAIN)
    ablation_stats=summarize(rows,ABLATION)
    csv_write(output/'validation_statistics.csv',main_stats)
    csv_write(output/'validation_ablation_statistics.csv',ablation_stats)
    tests=[]
    for controls,family in [(['DE','TEAM'],'primary'),(['DSPDE','DLSDE','PEMSDE'],'paper_controls'),(ABLATION[1:],'ablation')]:
        tests.extend(compare(rows,'APE',controls,family))
    csv_write(output/'validation_paired_tests.csv',tests)
    rank_summary=[dict(algorithm=algo,mean_rank=float(np.mean([r['rank'] for r in main_stats if r['algorithm']==algo]))) for algo in MAIN]
    csv_write(output/'validation_ranks.csv',rank_summary)
    ablation_ranks=[dict(algorithm=algo,mean_rank=float(np.mean([r['rank'] for r in ablation_stats if r['algorithm']==algo]))) for algo in ABLATION]
    csv_write(output/'validation_ablation_ranks.csv',ablation_ranks)
    counts=[]
    for control in MAIN[:-1]+ABLATION[1:]:
        group=[r for r in tests if r['comparison']==control]
        counts.append(dict(comparison=control,family=group[0]['family'],
                           wins=sum(r['reference_result']=='win' for r in group),
                           not_detected=sum(r['reference_result']=='not_detected' for r in group),
                           losses=sum(r['reference_result']=='loss' for r in group)))
    csv_write(output/'validation_comparison_counts.csv',counts)
    sensitivity=[]
    for fid in range(1,17):
        means=[next(r['mean'] for r in main_stats if r['function']==fid and r['algorithm']==algo) for algo in MAIN]
        for algo,rank in zip(MAIN,ranks(means)):
            sensitivity.append(dict(function=fid,algorithm=algo,rank=float(rank)))
    sensitivity_ranks=[dict(algorithm=algo,mean_rank=float(np.mean([r['rank'] for r in sensitivity if r['algorithm']==algo]))) for algo in MAIN]
    csv_write(output/'validation_f01_f16_ranks.csv',sensitivity_ranks)
    matrix=np.array([[next(r['rank'] for r in main_stats if r['function']==fid and r['algorithm']==algo) for algo in MAIN] for fid in range(1,31)])
    stat,pvalue=friedmanchisquare(*matrix.T)
    result=dict(author='殷明骏',independent_runs_per_function=20,formal_records=4800,
                master_seed=cfg['seed'],mean_ranks=rank_summary,ablation_mean_ranks=ablation_ranks,
                comparisons=counts,f01_f16_mean_ranks=sensitivity_ranks,
                omnibus_friedman=dict(statistic=float(stat),p=float(pvalue),scope='Six methods over thirty functions; not a pairwise superiority test'),
                primary_family_tests=60,paper_control_family_tests=90,ablation_family_tests=60,
                caveat='Mean ranks are descriptive. Corrected per-function tests support only the comparisons and functions actually detected.')
    (output/'validation_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
