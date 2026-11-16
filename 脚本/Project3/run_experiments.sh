#!/usr/bin/env bash
# Author and last editor: 殷明骏
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export PROJECT3_PYTHON=${PROJECT3_PYTHON:-$(command -v python3)}
exec /bin/bash "$ROOT/original_run_experiments.sh" "$@"
