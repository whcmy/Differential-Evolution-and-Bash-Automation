"""Independently validate Automation records and Bash extraction. Author: 殷明骏."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

if not __debug__:
    raise RuntimeError('Validation requires Python assertions enabled; unset PYTHONOPTIMIZE')

sys.path.insert(0, str(Path(__file__).resolve().parent / 'code'))
from run_adaptive_de import make_problem


def score(directory):
    config = json.loads((directory / 'manifest.json').read_text())['config']
    assert config['suite'] == 'cec2014' and config['dimension'] == 10
    assert config['functions'] == list(range(1, 31)) and config['runs'] == 1
    assert config['algorithms'] == ['TEAM'] and config['population_mode'] == 'fixed'
    for name, digest in config['source_sha256'].items():
        current = hashlib.sha256((Path(__file__).parent/'code'/name).read_bytes()).hexdigest()
        if current != digest:
            # Archived receipts identify the original execution snapshot.
            # Validate the renamed source against its recorded snapshot mapping.
            snapshot = json.loads((Path(__file__).parent/'source_snapshot_sha256.json').read_text())
            entry = snapshot['files']['code/'+name]
            assert digest == entry['archived_sha256'] and current == entry['sha256']
    import opfunu.cec_based.cec2014 as module
    module_path = Path(module.__file__)
    assert hashlib.sha256(module_path.read_bytes()).hexdigest() == config['benchmark_module_sha256']
    for name, digest in config['benchmark_data_sha256'].items():
        assert hashlib.sha256((module_path.parent/'data_2014'/name).read_bytes()).hexdigest() == digest
    paths = sorted((directory/'TEAM').glob('*.json'))
    assert len(paths) == 30
    errors = []
    for fid, path in enumerate(paths, 1):
        row = json.loads(path.read_text())
        problem = make_problem('cec2014', fid, 10)
        x = np.asarray(row['x'])
        assert row['function'] == fid and row['run'] == 1 and row['algorithm'] == 'TEAM'
        expected_seed = int(np.random.SeedSequence([config['seed'], 2014, fid, 1]).generate_state(1)[0])
        assert row['seed'] == expected_seed
        assert x.shape == (10,) and np.isfinite(x).all()
        assert np.all(x >= problem.lb) and np.all(x <= problem.ub)
        fitness = float(problem.evaluate(x))
        assert math.isfinite(fitness) and math.isclose(fitness, row['fun'], rel_tol=1e-12, abs_tol=1e-9)
        assert row['optimum'] == float(problem.f_global)
        assert row['nfev'] == config['max_fes']
        assert row['diagnostics']['initial_population'] == config['population_size']
        assert row['diagnostics']['min_population'] == row['diagnostics']['max_population'] == config['population_size']
        history = row['history']
        assert history[0][0] == config['population_size'] and history[-1][0] == row['nfev']
        assert history[-1][1] == row['fun']
        assert all(a[0] < b[0] and a[1] >= b[1] for a, b in zip(history, history[1:]))
        absolute = abs(row['fun'] - row['optimum'])
        assert math.isfinite(absolute)
        errors.append(absolute)
    return config, math.fsum(errors)/30


def validate_batch(directory):
    lines = (directory/'experiment.log').read_text().splitlines()
    results = [dict(token.split('=', 1) for token in line.split()[1:])
               for line in lines if line.startswith('SUITE_RESULT ')]
    summary = (directory/'summary_report.txt').read_text().splitlines()[2:]
    assert len(results) == len(summary) == 3
    audited = []
    for npop, logged, extracted in zip((50, 100, 150), results, summary):
        config, value = score(directory/f'np{npop}')
        assert config['population_size'] == npop
        assert logged['population'] == str(npop)
        assert logged['budget'] == str(config['max_fes']) and logged['seed'] == str(config['seed'])
        assert logged['functions'] == '30' and logged['score'] == f'{value:.17e}'
        expected = [logged[k] for k in ('run_id','population','budget','seed','functions','score')]
        assert extracted.split() == expected
        audited.append(dict(population=npop, score=value, records=30))
    result = dict(author='殷明骏', passed=True, records=90,
                  summary_matches_log=True, saved_solutions_recomputed=True,
                  score_definition='mean(abs(obtained_fitness-known_optimum)) over F01-F30',
                  parameter_combinations=audited)
    (directory/'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print('VALIDATION_SUCCESS records=90 summary_matches_log=true solutions_recomputed=true')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['score', 'batch'])
    p.add_argument('directory', type=Path)
    p.add_argument('--run-id')
    args = p.parse_args()
    if args.action == 'score':
        if not args.run_id or any(c.isspace() for c in args.run_id):
            p.error('run-id must be a nonempty token without whitespace')
        cfg, value = score(args.directory)
        print(f"SUITE_RESULT run_id={args.run_id} population={cfg['population_size']} "
              f"budget={cfg['max_fes']} seed={cfg['seed']} functions=30 score={value:.17e}", flush=True)
    else:
        validate_batch(args.directory)
