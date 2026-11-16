"""Bounded hourly cron execution; never used as manual evidence. Author: 殷明骏."""
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TAG = '# PROJECT3_YINMINGJUN_HOURLY'


def now():
    return datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')


def crontab():
    p = subprocess.run(['crontab', '-l'], text=True, capture_output=True)
    if p.returncode and 'no crontab for' not in p.stderr:
        raise RuntimeError(p.stderr)
    return p.stdout


def save_crontab(text):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.crontab') as f:
        f.write(text); f.flush()
        subprocess.run(['crontab', f.name], check=True)


def remove_job():
    current = crontab()
    remaining = ''.join(line+'\n' for line in current.splitlines() if TAG not in line)
    save_crontab(remaining)
    (ROOT/'evidence/crontab_after.txt').write_text(crontab())


def ancestors():
    result = []
    pid = os.getpid()
    while pid > 1:
        try:
            process = Path('/proc')/str(pid)
            cmd = (process/'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace').strip()
            status = (process/'status').read_text().splitlines()
            ppid = int(next(s.split()[1] for s in status if s.startswith('PPid:')))
            result.append(dict(pid=pid, ppid=ppid, command=cmd))
            pid = ppid
        except (FileNotFoundError, StopIteration):
            break
    return result


def install():
    config_path = ROOT/'cron/schedule.json'
    if config_path.exists():
        raise RuntimeError('Schedule already exists; inspect it before installing another testing period')
    current = crontab()
    if TAG in current:
        raise RuntimeError('Project3 entry already exists')
    (ROOT/'evidence/crontab_before.txt').write_text(current)
    # A single hourly expression starts at the next 10-minute boundary at least
    # five minutes away. It stops after three successes or a six-hour deadline.
    stamp = datetime.now(ZoneInfo('Asia/Shanghai'))
    first = stamp.replace(second=0, microsecond=0) + timedelta(minutes=5)
    first += timedelta(minutes=(-first.minute) % 10)
    config = dict(author='殷明骏', installed_at=now(), timezone='Asia/Shanghai',
                  first_due=first.isoformat(), deadline=(first+timedelta(hours=6)).isoformat(),
                  target_successes=3, budget=100000, populations=[50,100,150],
                  expected_times=[(first+timedelta(hours=i)).isoformat() for i in range(3)])
    # Double quotes preserve the workspace space; the observed workspace path
    # has no shell interpolation characters. Cron uses the host Asia/Shanghai TZ.
    entry = f'{first.minute} * * * * /bin/bash "{ROOT}/cron/run_scheduled.sh" >> "{ROOT}/cron/scheduled.log" 2>&1 {TAG}\n'
    (ROOT/'cron/crontab.txt').write_text(entry)
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n')
    save_crontab(current.rstrip('\n')+'\n'+entry if current else entry)
    (ROOT/'evidence/crontab_installed.txt').write_text(crontab())
    print(json.dumps(config, ensure_ascii=False, indent=2))


def execute():
    config = json.loads((ROOT/'cron/schedule.json').read_text())
    stamp = datetime.now(ZoneInfo('Asia/Shanghai'))
    if stamp < datetime.fromisoformat(config['first_due']):
        return
    if stamp > datetime.fromisoformat(config['deadline']):
        print(f'SCHEDULE_EXPIRED timestamp={now()}', flush=True)
        remove_job()
        return
    receipts = sorted((ROOT/'cron').glob('success_*.json'))
    if len(receipts) >= 3:
        remove_job()
        return
    ancestry = ancestors()
    if not any(Path(r['command'].split()[0]).name == 'cron' for r in ancestry if r['command']):
        raise RuntimeError('Scheduled evidence requires a real cron ancestor; manual invocation rejected')
    attempt = stamp.strftime('%Y%m%dT%H%M%S')
    sequence = len(receipts)+1
    output = ROOT/'output'/f'cron_{sequence}_{attempt}'
    provenance = dict(started_at=now(), sequence=sequence, source='system crontab',
                      ancestors=ancestry, output=str(output.relative_to(ROOT)))
    (ROOT/'cron'/f'attempt_{attempt}.json').write_text(json.dumps(provenance, indent=2)+'\n')
    print(f'CRON_START timestamp={now()} sequence={sequence} directory={output.name}', flush=True)
    result = subprocess.run(['/bin/bash', str(ROOT/'run_experiments.sh'), '--output', str(output),
                             '--seed', str(20261110+sequence), '--mode', 'cron',
                             '--budget', str(config['budget']), '--workers', '6'])
    if result.returncode:
        print(f'CRON_FAILED timestamp={now()} sequence={sequence} exit={result.returncode}', flush=True)
        sys.exit(result.returncode)
    assert json.loads((output/'validation.json').read_text())['passed']
    assert 'BATCH_SUCCESS ' in (output/'experiment.log').read_text()
    provenance.update(completed_at=now(), passed=True, records=90)
    (ROOT/'cron'/f'success_{sequence:02d}.json').write_text(json.dumps(provenance, indent=2)+'\n')
    print(f'CRON_SUCCESS timestamp={now()} sequence={sequence} validated_records=90', flush=True)
    if sequence == 3:
        remove_job()
        print(f'SCHEDULE_COMPLETE timestamp={now()} successful_executions=3', flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['install']:
        install()
    elif not sys.argv[1:]:
        execute()
    else:
        raise SystemExit('Usage: scheduler.py [install]')
