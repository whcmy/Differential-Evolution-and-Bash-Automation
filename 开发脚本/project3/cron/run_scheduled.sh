#!/usr/bin/env bash
# Author and last editor: 殷明骏
set -Eeuo pipefail
export PATH=/usr/bin:/bin LC_ALL=C TZ=Asia/Shanghai
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
exec 9>"$ROOT/cron/scheduled.lock"
flock -n 9 || exit 0
PYTHON=${PROJECT3_PYTHON:-"$ROOT/../project2_final/.venv/bin/python"}
"$PYTHON" "$ROOT/cron/scheduler.py"
