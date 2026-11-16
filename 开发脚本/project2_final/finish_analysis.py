"""Continue this authorized experiment job through verified report rendering.

This is a single current job, not a recurring automation. It never changes
algorithm code or kills optimization jobs. Final visual acceptance and ZIP
publication remain pending the assistant's inspection of rendered pages.
Author: 殷明骏, 202483890029.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
PYTHON = str(ROOT/'.venv/bin/python')
STATUS = ROOT/'output/pipeline_status.json'
START = time.monotonic()
TIMEOUT_SECONDS = 12*3600


def status(stage, **extra):
    row = dict(author='殷明骏', student_id='202483890029', stage=stage,
               elapsed_seconds=round(time.monotonic()-START), **extra)
    STATUS.write_text(json.dumps(row, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(row, ensure_ascii=False), flush=True)


def alive(pid, fragment):
    path = Path('/proc')/str(pid)
    if not path.exists():
        return False
    try:
        command = (path/'cmdline').read_bytes().replace(b'\x00', b' ').decode()
        state = (path/'stat').read_text().split()[2]
        return fragment in command and state != 'Z'
    except FileNotFoundError:
        return False


def run(script, *args, log=None):
    command = [PYTHON, str(ROOT/script), *map(str, args)]
    target = ROOT/'logs'/(log or Path(script).stem+'.log')
    with target.open('w') as f:
        result = subprocess.run(command, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'{script} failed ({result.returncode}); see {target.name}')


def main():
    # Read PIDs only from this invocation's command line after observing them live.
    if len(sys.argv) != 3:
        raise ValueError('require coursework PID and native-reference PID')
    targets = [(int(sys.argv[1]), 'code/run_project2.py', ROOT/'results/coursework/manifest.json'),
               (int(sys.argv[2]), 'run_pems_native.py', ROOT/'results/pems_native_reference/manifest.json')]
    status('waiting_for_formal_matrices', targets=[p for p, _, _ in targets])
    while True:
        states = []
        for pid, fragment, manifest in targets:
            completed = manifest.exists() and 'completed_utc' in json.loads(manifest.read_text())
            live = alive(pid, fragment)
            states.append(dict(pid=pid, alive=live, completed=completed))
            if not completed and not live:
                raise RuntimeError(f'experiment {pid} is terminal before completing its matrix')
        if all(s['completed'] for s in states):
            break
        if time.monotonic()-START > TIMEOUT_SECONDS:
            status('observation_timeout', process_states=states, note='optimization processes left running; no auto-restart')
            return
        # This background process does not block the assistant's UI tools.
        time.sleep(20)
    status('independent_solution_audit')
    run('verify_records.py', '--datasets', 'results/coursework', '--output', 'output/coursework_validation.json', log='coursework_validation.log')
    run('verify_records.py', '--datasets', 'results/pems_native_reference', '--output', 'output/pems_native_validation.json', log='pems_native_validation.log')
    status('full_budget_selected_replay')
    run('replay_selected.py')
    status('statistics')
    run('analyze_project2.py')
    # One declaration immediately before the first PDF authoring operation:
    # thirty scientific curve PDFs plus the report.
    marker = ROOT/'output/pdf_authoring_started.json'
    if not marker.exists():
        node = '/home/yinwhcmy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
        declaration = '/home/yinwhcmy/.codex/plugins/cache/openai-primary-runtime/pdf/26.1105.12137/skills/pdf/container_tools/mark_artifact_operation_started.mjs'
        subprocess.run([node, declaration, '--operation-kind', 'create', '--expected-output-count', '31', '--output-format', 'pdf'], check=True)
        marker.write_text(json.dumps(dict(operation='create', expected_output_count=31, author='殷明骏'))+'\n')
    status('figures')
    run('plot_project2.py')
    for fid in range(1, 31):
        pdf = ROOT/'output/curves'/f'F{fid:02d}.pdf'
        run('tools/audit_pdf_text.py', pdf, '--min-pt', '5', '--json', log=f'F{fid:02d}_font_audit.log')
        run('tools/audit_figure_collisions.py', pdf, '--json-out', str(pdf.with_suffix('.collision.json')),
            log=f'F{fid:02d}_collision.log')
    status('report')
    run('build_report.py')
    status('rendered_qa')
    run('render_report.py')
    status('awaiting_visual_inspection', note='not complete; rendered pages must be inspected, then package and completion audit run')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        status('needs_repair', error=str(e))
        raise
