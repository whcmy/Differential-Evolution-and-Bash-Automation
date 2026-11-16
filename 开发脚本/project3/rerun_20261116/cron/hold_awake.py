"""Hold the temporary inhibitor until completion or the fixed deadline. Author: 殷明骏."""
from datetime import datetime
import json,os,time
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
config=json.loads((ROOT/'cron/schedule.json').read_text())
deadline=datetime.fromisoformat(config['deadline'])
while True:
    stamp=datetime.now(ZoneInfo('Asia/Shanghai'))
    state={'timestamp':stamp.isoformat(timespec='seconds'),'monitor_pid':os.getpid(),
           'successes':len(list((ROOT/'cron').glob('success_*.json')))}
    (ROOT/'cron/monitor_state.json').write_text(json.dumps(state,indent=2)+'\n')
    if (ROOT/'cron/COMPLETE').exists() or (ROOT/'cron/FAILED').exists() or stamp>deadline:
        print('AWAKE_GUARD_RELEASED '+state['timestamp'],flush=True)
        break
    time.sleep(30)
