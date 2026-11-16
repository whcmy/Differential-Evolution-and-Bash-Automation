"""Independent complete-matrix audit; author 殷明骏, 202483890029."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from opfunu.cec_based import cec2014, cec2017, cec2022

ROOT = Path(__file__).resolve().parent


def audit(directory):
    directory = Path(directory)
    manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8-sig'))
    c = manifest['config']
    suite = c['suite'].lower()
    budget = c.get('max_fes', c.get('settings', {}).get('max_fes'))
    dimension = c['dimension']
    files = sorted(directory.glob('*.json'))+sorted(directory.glob('*/*.json'))
    files = [p for p in files if p.name != 'manifest.json']
    problems, keys, issues, hashes = {}, [], [], {}
    counts = Counter()
    max_delta = 0.
    for p in files:
        row = json.loads(p.read_text(encoding='utf-8-sig'))
        if 'algorithm' not in row:
            continue
        key = row['algorithm'], row['function'], row['run']
        keys.append(key)
        counts[row['algorithm']] += 1
        fid = row['function']
        if fid not in problems:
            if suite == 'cec2017' and c.get('benchmark', '').startswith('CEC2017-py reference'):
                from pems_native_problem import Reference2017
                problems[fid] = Reference2017(fid, ndim=dimension)
            else:
                module = {'cec2014': cec2014, 'cec2017': cec2017, 'cec2022': cec2022}[suite]
                problems[fid] = getattr(module, f'F{fid}{suite[-4:]}')(ndim=dimension)
        problem = problems[fid]
        x = np.array(row.get('x', row.get('best_x')), float)
        fun = row.get('fun', row.get('best_fitness'))
        h = np.array(row['history'], float)
        recomputed = float(problem.evaluate(x))
        max_delta = max(max_delta, abs(recomputed-fun))
        checks = dict(vector=x.shape == (dimension,) and np.isfinite(x).all()
                      and np.all(x >= problem.lb) and np.all(x <= problem.ub),
                      objective=np.isclose(recomputed, fun, rtol=1e-10, atol=1e-8),
                      budget=row['nfev'] == budget,
                      finite=np.isfinite(fun) and np.isfinite(h).all(),
                      history_shape=h.ndim == 2 and h.shape[1] == 2,
                      history_end=h[-1, 0] == budget and abs(h[-1, 1]-fun) <= 1e-8,
                      history_order=np.all(np.diff(h[:, 0]) > 0),
                      history_monotone=np.all(np.diff(h[:, 1]) <= 1e-8),
                      error=abs(row['error']-max(0., fun-float(problem.f_global))) <= 1e-7,
                      optimum=row['optimum'] == float(problem.f_global))
        issues.extend(dict(file=str(p.relative_to(directory)), check=k, saved=fun, recomputed=recomputed)
                      for k, ok in checks.items() if not ok)
        hashes[str(p.relative_to(directory))] = hashlib.sha256(p.read_bytes()).hexdigest()
    expected = {(a, f, r) for a in c['algorithms'] for f in c['functions'] for r in range(1, c['runs']+1)}
    observed = set(keys)
    result = dict(directory=str(directory.relative_to(ROOT)), numpy=np.__version__,
                  expected_count=len(expected), observed_count=len(keys), counts=dict(counts),
                  missing=sorted(expected-observed), extra=sorted(observed-expected),
                  duplicates=len(keys)-len(observed), record_issues=issues,
                  max_abs_recompute_difference=max_delta, manifest_complete='completed_utc' in manifest)
    result['passed'] = (not result['missing'] and not result['extra'] and not result['duplicates']
                        and not issues and result['manifest_complete'])
    hashfile = ROOT/'output'/('hashes_'+directory.name+'_'+directory.parent.name+'.json')
    hashfile.write_text(json.dumps(hashes, indent=2)+'\n')
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--datasets', nargs='+', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    results = [audit(ROOT/name) for name in a.datasets]
    output = dict(author='殷明骏', student_id='202483890029', datasets=results,
                  passed=all(r['passed'] for r in results))
    (ROOT/a.output).write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({**output, 'datasets': [{k: v for k, v in r.items() if k != 'record_issues'} for r in results]}, ensure_ascii=False, indent=2))
    sys.exit(0 if output['passed'] else 1)


if __name__ == '__main__':
    main()
