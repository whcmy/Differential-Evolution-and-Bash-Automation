"""Analysis of the last frozen independent sample. Author: 殷明骏."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from analyze_project2 import load,summarize,compare,csv_write


def main():
    local=Path(__file__).parent
    contract=json.loads((local/'confirmation_contract.json').read_text())
    manifest=json.loads((local/'results/confirmation/manifest.json').read_text())
    config=manifest['config'];selected=contract['selected_algorithm']
    main_methods=['DE','DSPDE','DLSDE','PEMSDE','TEAM',selected]
    removed=[selected+'_no_phase',selected+'_no_learning']
    ablation_methods=[selected,'DLSDE']+removed
    assert manifest['record_count']==4800
    assert config['seed']==contract['master_seed'] and config['runs']==20
    assert config['functions']==list(range(1,31))
    assert config['algorithms']==sorted(set(main_methods+removed))
    for name,digest in contract['source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
        assert config['source_sha256'][name]==digest
    from opfunu.cec_based import cec2014
    module=Path(cec2014.__file__)
    assert hashlib.sha256(module.read_bytes()).hexdigest()==contract['benchmark_module_sha256']
    for name,digest in contract['benchmark_data_sha256'].items():
        assert hashlib.sha256((module.parent/'data_2014'/name).read_bytes()).hexdigest()==digest
    rows=load(local/'results/confirmation');assert len(rows)==4800
    main_statistics=summarize(rows,main_methods)
    ablation_statistics=summarize(rows,ablation_methods)
    tests=[]
    for controls,family in [(['DE','DLSDE','TEAM'],'primary'),(['DSPDE','PEMSDE'],'other_paper'),(removed,'ablation')]:
        tests.extend(compare(rows,selected,controls,family))
    output=local/'analysis';output.mkdir(exist_ok=True)
    csv_write(output/'confirmation_statistics.csv',main_statistics)
    csv_write(output/'confirmation_ablation_statistics.csv',ablation_statistics)
    csv_write(output/'confirmation_paired_tests.csv',tests)
    ranks=[dict(algorithm=a,mean_rank=float(np.mean([r['rank'] for r in main_statistics if r['algorithm']==a]))) for a in main_methods]
    ablation_ranks=[dict(algorithm=a,mean_rank=float(np.mean([r['rank'] for r in ablation_statistics if r['algorithm']==a]))) for a in ablation_methods]
    csv_write(output/'confirmation_ranks.csv',ranks)
    csv_write(output/'confirmation_ablation_ranks.csv',ablation_ranks)
    counts=[]
    for control in main_methods[:-1]+removed:
        group=[r for r in tests if r['comparison']==control]
        counts.append(dict(comparison=control,family=group[0]['family'],
                           wins=sum(r['reference_result']=='win' for r in group),
                           not_detected=sum(r['reference_result']=='not_detected' for r in group),
                           losses=sum(r['reference_result']=='loss' for r in group)))
    csv_write(output/'confirmation_comparison_counts.csv',counts)
    sensitivity=[dict(algorithm=a,mean_rank=float(np.mean([r['rank'] for r in main_statistics if r['algorithm']==a and r['function']<=16]))) for a in main_methods]
    candidate_rank=next(r['mean_rank'] for r in ranks if r['algorithm']==selected)
    first=candidate_rank < min(r['mean_rank'] for r in ranks if r['algorithm']!=selected)
    result=dict(author='殷明骏',selected_algorithm=selected,master_seed=config['seed'],
                independent_runs=20,records=4800,main_methods=main_methods,
                ablation_methods=ablation_methods,mean_ranks=ranks,
                ablation_mean_ranks=ablation_ranks,comparisons=counts,
                f01_f16_mean_ranks=sensitivity,first_descriptive_rank=first,
                primary_tests=90,other_paper_tests=60,additional_ablation_tests=60,
                baseline_as_ablation='DLSDE is the shared no-added-strategy control; its canonical primary comparison is reused, never retested under another correction family.',
                scope='Complete fixed CEC2014 10D benchmark; mean ranks are descriptive, not proof of superiority on arbitrary tasks.')
    (output/'confirmation_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
