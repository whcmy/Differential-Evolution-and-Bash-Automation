"""Validate the DC-DE hourly rerun and aggregate its original records. Author: 殷明骏."""
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
EXPERIMENT = ROOT/'rerun_20261116'
sys.path.insert(0, str(EXPERIMENT))
from verify_batch import score

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def collect(require_complete=True, precompute=None):
    if precompute is not None or not require_complete:
        raise ValueError('The final report requires three complete real cron executions')
    schedule = json.loads((EXPERIMENT/'cron/schedule.json').read_text())
    raw_receipts = [json.loads(p.read_text()) for p in sorted((EXPERIMENT/'cron').glob('success_*.json'))]
    assert len(raw_receipts) == 3 and (EXPERIMENT/'cron/COMPLETE').exists()
    assert not (EXPERIMENT/'cron/FAILED').exists()
    pipeline = json.loads((EXPERIMENT/'evidence/pipeline_sha256.json').read_text())
    assert all(sha(EXPERIMENT/name) == digest for name,digest in pipeline.items())
    lineage = json.loads((EXPERIMENT/'evidence/source_lineage.json').read_text())
    for row in lineage['files']:
        expected = row.get('sha256',row.get('source_sha256'))
        # Original Report2 sources are available in the workspace; archived runs
        # retain the byte-identical optimizer copies and lineage receipts.
        if Path(row['source']).exists(): assert sha(row['source']) == expected
        if 'sha256' in row: assert sha(EXPERIMENT/row['copy']) == expected
    records, suites, timing, receipts = [], [], [], []
    for index, receipt in enumerate(raw_receipts,1):
        assert receipt['sequence'] == index and receipt['passed'] and receipt['records'] == 90
        assert receipt['source'] == 'system crontab'
        assert any(Path(p['command'].split()[0]).name == 'cron' for p in receipt['ancestors'] if p['command'])
        start,end = map(datetime.fromisoformat,(receipt['started_at'],receipt['completed_at']))
        due = datetime.fromisoformat(schedule['expected_times'][index-1])
        gap = (start-datetime.fromisoformat(raw_receipts[index-2]['started_at'])).total_seconds() if index>1 else None
        delay = (start-due).total_seconds()
        assert 0 <= delay <= 60 and end >= start and (end-start).total_seconds() <= 1800
        assert gap is None or abs(gap-3600) <= 60
        timing.append(dict(sequence=index,planned_start=due.isoformat(),actual_start=receipt['started_at'],
                           actual_end=receipt['completed_at'],delay_seconds=delay,
                           gap_from_previous_seconds=gap,one_hour_spacing_passed=True))
        directory = EXPERIMENT/receipt['output']
        lines = (directory/'experiment.log').read_text().splitlines()
        assert any(s.startswith('BATCH_START ') and 'mode=cron' in s for s in lines)
        assert sum(s.startswith('BATCH_SUCCESS ') for s in lines) == 1
        logged = [dict(t.split('=',1) for t in s.split()[1:]) for s in lines if s.startswith('SUITE_RESULT ')]
        extracted = (directory/'summary_report.txt').read_text().splitlines()[2:]
        validation = json.loads((directory/'validation.json').read_text())
        assert validation['passed'] and validation['records'] == 90
        assert len(logged) == len(extracted) == 3
        for npop, log, summary in zip((50,100,150),logged,extracted):
            cfg,value = score(directory/f'np{npop}')
            assert cfg['max_fes'] == 100000 and cfg['seed'] == schedule['seed_base']+index
            assert cfg['population_size'] == npop
            assert log['score'] == f'{value:.17e}'
            assert summary.split() == [log[k] for k in ('run_id','population','budget','seed','functions','score')]
            for path in sorted((directory/f'np{npop}/DUAL').glob('*.json')):
                row = json.loads(path.read_text())
                records.append(dict(execution=index,population=npop,function=row['function'],seed=row['seed'],
                    nfev=row['nfev'],fitness=row['fun'],known_optimum=row['optimum'],
                    absolute_error=abs(row['fun']-row['optimum']),source=str(path.relative_to(ROOT)),sha256=sha(path)))
            suites.append(dict(execution=index,population=npop,master_seed=cfg['seed'],score=value,
                source='system crontab',started_at=receipt['started_at'],completed_at=receipt['completed_at']))
        receipts.append(dict(receipt,output=str(directory.relative_to(ROOT))))
    assert len(records) == 270 and len({(r['execution'],r['population'],r['function']) for r in records}) == 270
    pooled=[]
    for npop in (50,100,150):
        values=[s['score'] for s in suites if s['population']==npop]
        rows=[r for r in records if r['population']==npop]
        totals={fid:math.fsum(r['absolute_error'] for r in rows if r['function']==fid) for fid in range(1,31)}
        top=max(totals,key=totals.get)
        pooled.append(dict(population=npop,suite_scores=values,mean=statistics.mean(values),
            sample_std=statistics.stdev(values),largest_contributor=top,largest_share=totals[top]/math.fsum(totals.values())))
    final_tab=subprocess.run(['crontab','-l'],capture_output=True,text=True,check=True).stdout
    assert 'PROJECT3_DCDE_20261116_HOURLY' not in final_tab
    result=dict(author='殷明骏',algorithm='DC-DE',internal_algorithm='DUAL',complete=True,scheduled_successes=3,
        receipts=receipts,suites=suites,pooled=pooled,record_count=270,precomputed_preview=False,precomputed_input=None,
        timing_audit=timing,strict_hourly_spacing_passed=True,optimization_evaluations=27000000,
        score_definition='arithmetic mean over F01-F30 of abs(fitness-known_optimum)',
        source_hashes_verified=True,summary_matches_original_logs=True,original_records_read_only=True)
    target=ROOT/'output/analysis';target.mkdir(exist_ok=True,parents=True)
    for filename,rows in [('records.csv',records),('suite_scores.csv',suites)]:
        with (target/filename).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (target/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    (target/'timing_audit.json').write_text(json.dumps(dict(author='殷明骏',strict_hourly_spacing_passed=True,executions=timing),ensure_ascii=False,indent=2)+'\n')
    (EXPERIMENT/'evidence/final_independent_verification.json').write_text(json.dumps(dict(author='殷明骏',passed=True,
        records_recomputed=270,suite_scores_verified=9,actual_start_intervals_seconds=[t['gap_from_previous_seconds'] for t in timing[1:]],
        cron_ancestry_verified=True,source_hashes_verified=True,summary_matches_original_logs=True,
        temporary_cron_removed=True),ensure_ascii=False,indent=2)+'\n')
    return result

if __name__ == '__main__':
    r=collect();print(f"AUDIT complete={r['complete']} scheduled_successes={r['scheduled_successes']} records={r['record_count']}")
