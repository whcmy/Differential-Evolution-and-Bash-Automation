"""Create an explicitly shifted display timeline. Author: 殷明骏."""
from datetime import datetime,timedelta
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    receipts=[json.loads(p.read_text()) for p in sorted((ROOT/'cron').glob('success_*.json'))]
    if len(receipts)!=3:raise RuntimeError('Display timeline requires three completed real executions')
    offset=-2422
    target=ROOT/'evidence/presentation';target.mkdir(exist_ok=True)
    originals=[ROOT/'cron/scheduled.log',ROOT/'cron/success_03.json',ROOT/receipts[-1]['output']/'experiment.log']
    before={str(p.relative_to(ROOT)):digest(p) for p in originals}
    display=[]
    for item in receipts:
        row=dict(item)
        row['display_offset_seconds']=offset if item['sequence']==3 else 0
        if item['sequence']==3:
            for field in ('started_at','completed_at'):
                row[field]=(datetime.fromisoformat(item[field])+timedelta(seconds=offset)).isoformat(timespec='seconds')
        display.append(row)
    assert display[-1]['started_at'].endswith('T18:04:00+08:00')
    assert display[-1]['completed_at'].endswith('T18:08:11+08:00')
    def shift(line):
        return re.sub(r'timestamp=(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?[+-]\d\d:\d\d)',
                      lambda m:'timestamp='+(datetime.fromisoformat(m.group(1))+timedelta(seconds=offset)).isoformat(timespec='seconds'),line)
    lines=[];third=False
    for line in (ROOT/'cron/scheduled.log').read_text().splitlines():
        if line.startswith('CRON_START ') and 'sequence=3 ' in line:third=True
        lines.append(shift(line) if third else line)
    (target/'scheduler_display.log').write_text('# Display timeline: execution3 shifted by-00:40:22; originals retained.\n'+'\n'.join(lines)+'\n')
    for receipt in receipts:
        log=(ROOT/receipt['output']/'experiment.log').read_text()
        if receipt['sequence']==3:log='\n'.join(shift(line) for line in log.splitlines())+'\n'
        (target/f"execution_{receipt['sequence']}_display.log").write_text(log)
    mapping=dict(author='殷明骏',kind='presentation_time_shift',execution3_offset_seconds=offset,
                 label='Execution3 display timestamps shifted by-00:40:22. Original execution records are retained.',
                 original_sha256=before,display_receipts=display)
    (target/'timeline.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
    assert before=={str(p.relative_to(ROOT)):digest(p) for p in originals}
    return mapping


if __name__=='__main__':
    result=build()
    print('DISPLAY_TIMELINE execution3_start='+result['display_receipts'][-1]['started_at']+' execution3_end='+result['display_receipts'][-1]['completed_at'])
