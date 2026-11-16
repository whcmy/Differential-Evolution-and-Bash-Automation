#!/usr/bin/env bash
# Author and last editor: 殷明骏
set -Eeuo pipefail
export LC_ALL=C TZ=Asia/Shanghai
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PYTHON=${PROJECT3_PYTHON:-"$ROOT/../project2_final/.venv/bin/python"}
OUTPUT=""; BUDGET=100000; SEED=20261110; WORKERS=6; MODE=manual
POPULATIONS=(50 100 150)
usage() {
    echo 'Usage: ./run_experiments.sh [--output NEW_DIR] [--budget FES] [--seed N] [--workers N] [--mode manual|cron]'
    echo 'Runs Project2 PGE-DE on every CEC2014 function in 10D with NP=50,100,150.'
    echo 'Default: 100000 evaluations per function; a fresh timestamped directory.'
    echo 'PROJECT3_PYTHON can select a compatible numerical Python environment.'
}
while (($#)); do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --output|--budget|--seed|--workers|--mode)
            (($# >= 2)) || { echo "Missing value for $1" >&2; exit 2; }
            case "$1" in
                --output) OUTPUT=$2 ;; --budget) BUDGET=$2 ;; --seed) SEED=$2 ;;
                --workers) WORKERS=$2 ;; --mode) MODE=$2 ;;
            esac
            shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done
for value in "$BUDGET" "$SEED" "$WORKERS"; do
    [[ $value =~ ^(0|[1-9][0-9]{0,9})$ ]] || { echo 'Expected an unsigned integer (max 10 digits)' >&2; exit 2; }
done
((BUDGET >= 150 && BUDGET <= 100000000 && WORKERS >= 1 && WORKERS <= 64)) || { echo 'Invalid budget or worker count' >&2; exit 2; }
[[ $MODE == manual || $MODE == cron ]] || { echo 'Invalid mode' >&2; exit 2; }
[[ -x $PYTHON ]] || { echo "Python is not executable: $PYTHON" >&2; exit 2; }
for tool in grep awk date mkdir; do command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 2; }; done
"$PYTHON" -c 'import numpy, scipy, opfunu' >/dev/null
[[ -n $OUTPUT ]] || OUTPUT="$ROOT/output/manual_$(date +%Y%m%dT%H%M%S)_$$"
mkdir -p -- "$(dirname -- "$OUTPUT")"
mkdir -- "$OUTPUT" || { echo 'Output must be a new directory; old logs are never appended to a new batch.' >&2; exit 2; }
OUTPUT=$(cd -- "$OUTPUT" && pwd)
LOG="$OUTPUT/experiment.log"
RUN_ID=$(basename -- "$OUTPUT")
trap 'rc=$?; echo "BATCH_FAILED timestamp=$(date -Is) batch=$RUN_ID exit=$rc" >> "$LOG"; exit "$rc"' ERR
echo "BATCH_START timestamp=$(date -Is) batch=$RUN_ID mode=$MODE seed=$SEED functions=30 dimension=10 budget=$BUDGET" >> "$LOG"
for NP in "${POPULATIONS[@]}"; do
    RUN="${RUN_ID}_np${NP}"
    echo "RUN_START timestamp=$(date -Is) run_id=$RUN algorithm=TEAM population=$NP budget=$BUDGET seed=$SEED" >> "$LOG"
    echo "Running $RUN: PGE-DE, NP=$NP, FEs=$BUDGET, seed=$SEED, CEC2014 F01-F30"
    "$PYTHON" "$ROOT/code/run_project2.py" \
        --suite cec2014 --algorithms TEAM --runs 1 --dimension 10 \
        --population-size "$NP" --population-mode fixed --max-fes "$BUDGET" \
        --seed "$SEED" --workers "$WORKERS" --output "$OUTPUT/np$NP" >> "$LOG" 2>&1
    "$PYTHON" "$ROOT/verify_batch.py" score "$OUTPUT/np$NP" --run-id "$RUN" >> "$LOG" 2>&1
done
echo 'Project3 mean absolute errors across CEC2014 F01-F30' > "$OUTPUT/summary_report.txt"
echo 'run_id population budget seed functions mean_absolute_error' >> "$OUTPUT/summary_report.txt"
grep '^SUITE_RESULT ' "$LOG" | awk '
function die() { print "Invalid SUITE_RESULT line" > "/dev/stderr"; exit 1 }
{
    delete v
    for (i=2; i<=NF; i++) {
        if (split($i, pair, "=") != 2 || pair[1] in v) die()
        v[pair[1]]=pair[2]
    }
    if (v["functions"] != 30 || v["score"] !~ /^[0-9]+([.][0-9]+)?[eE][+-][0-9]+$/) die()
    if (v["run_id"] == "" || v["population"] !~ /^[0-9]+$/ || v["budget"] !~ /^[0-9]+$/ || v["seed"] !~ /^[0-9]+$/) die()
    print v["run_id"], v["population"], v["budget"], v["seed"], v["functions"], v["score"]
    count++
}
END { if (count != 3) exit 1 }
' >> "$OUTPUT/summary_report.txt"
"$PYTHON" "$ROOT/verify_batch.py" batch "$OUTPUT" >> "$LOG" 2>&1
echo "BATCH_SUCCESS timestamp=$(date -Is) batch=$RUN_ID mode=$MODE combinations=3 functions_per_combination=30" >> "$LOG"
cat -- "$OUTPUT/summary_report.txt"
echo "Validated batch: $OUTPUT"
