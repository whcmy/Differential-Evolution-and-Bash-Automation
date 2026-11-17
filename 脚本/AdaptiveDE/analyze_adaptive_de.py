"""Source-backed statistics; author 殷明骏, 202483890029."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import csv
import json
from pathlib import Path
import numpy as np
from scipy.stats import rankdata, wilcoxon

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'output'
FINAL = ['DE', 'DSPDE', 'DLSDE', 'PEMSDE', 'TEAM']
DISPLAY = {'DE': 'DE', 'DSPDE': 'DSPDE', 'DLSDE': 'DLS-DE (fixed NP)',
           'PEMSDE': 'PEMS-DE', 'TEAM': 'PGE-DE'}


def csv_write(path, rows):
    rows = list(rows)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def load(path):
    rows = []
    for p in sorted(Path(path).rglob('*.json')):
        r = json.loads(p.read_text(encoding='utf-8-sig'))
        if 'algorithm' not in r:
            continue
        r['fun'] = r.get('fun', r.get('best_fitness'))
        r['x'] = r.get('x', r.get('best_x'))
        rows.append(r)
    return rows


def ranks(values):
    values = np.asarray(values)
    order = np.argsort(values, kind='stable')
    output = np.empty(len(values), float)
    start = 0
    while start < len(order):
        stop = start+1
        while stop < len(order) and np.isclose(values[order[stop]], values[order[start]], atol=1e-8, rtol=1e-10):
            stop += 1
        output[order[start:stop]] = (start+1+stop)/2
        start = stop
    return output


def summarize(rows, algorithms):
    output = []
    functions = sorted({r['function'] for r in rows})
    for fid in functions:
        summaries = []
        for algorithm in algorithms:
            group = sorted([r for r in rows if r['function'] == fid and r['algorithm'] == algorithm], key=lambda r: r['run'])
            if len(group) != 20 or [r['run'] for r in group] != list(range(1, 21)):
                raise ValueError(f'incomplete group {algorithm}, {fid}: {len(group)}')
            y = np.array([r['error'] for r in group])
            summaries.append(dict(function=fid, algorithm=algorithm, n=len(y), best=float(y.min()),
                                  median=float(np.median(y)), mean=float(y.mean()), worst=float(y.max()),
                                  std=float(y.std(ddof=1)), variance=float(y.var(ddof=1))))
        for r, rank in zip(summaries, ranks([r['mean'] for r in summaries])):
            r['rank'] = float(rank)
        output.extend(summaries)
    return output


def holm(values):
    order = np.argsort(values, kind='stable')
    out = np.empty(len(values))
    prior = 0.
    for i, j in enumerate(order):
        prior = max(prior, min(1., (len(values)-i)*values[j]))
        out[j] = prior
    return out


def compare(rows, reference, variants, family):
    output = []
    for fid in sorted({r['function'] for r in rows}):
        a = sorted([r for r in rows if r['function'] == fid and r['algorithm'] == reference], key=lambda r: r['run'])
        for variant in variants:
            b = sorted([r for r in rows if r['function'] == fid and r['algorithm'] == variant], key=lambda r: r['run'])
            assert len(a) == len(b) == 20
            assert [r['seed'] for r in a] == [r['seed'] for r in b]
            y, z = np.array([r['error'] for r in a]), np.array([r['error'] for r in b])
            diff = y-z
            diff[np.abs(diff) <= 1e-8+1e-10*np.maximum(np.abs(y), np.abs(z))] = 0
            nz = diff[diff != 0]
            if len(nz):
                test = wilcoxon(diff, alternative='two-sided', zero_method='wilcox', method='auto')
                p, statistic = float(test.pvalue), float(test.statistic)
                weights = rankdata(np.abs(nz))
                effect = float(np.sum(weights*np.sign(nz))/np.sum(weights))
            else:
                p, statistic, effect = 1., 0., 0.
            output.append(dict(family=family, function=fid, reference=reference, comparison=variant,
                               n_pairs=20, nonzero_pairs=len(nz), mean_difference=float((y-z).mean()),
                               reference_mean=float(y.mean()), comparison_mean=float(z.mean()),
                               median_difference=float(np.median(y-z)), rank_biserial=effect,
                               statistic=statistic, p_raw=p))
    for row, adjusted in zip(output, holm([r['p_raw'] for r in output])):
        row['p_holm'] = float(adjusted)
        row['reference_result'] = ('win' if row['rank_biserial'] < 0 else 'loss') if adjusted < .05 else 'not_detected'
    return output


def paper_comparison(rows, algorithm, paper_path, mode):
    summaries = summarize(rows, [algorithm])
    lookup = {r['function']: r for r in summaries}
    output = []
    with Path(paper_path).open(encoding='utf-8-sig') as f:
        for ref in csv.DictReader(f):
            fid = int(ref.get('function', ref.get('func')))
            r = lookup[fid]
            mean, sd = float(ref['dspde_mean'] if mode == 'fitness' else ref['paper_mean']), float(ref['dspde_std'] if mode == 'fitness' else ref['paper_std'])
            measured = r['mean']+(float(next(x['optimum'] for x in rows if x['function'] == fid)) if mode == 'fitness' else 0)
            best = min(x['fun'] if mode == 'fitness' else x['error'] for x in rows
                       if x['function'] == fid and x['algorithm'] == algorithm)
            output.append(dict(function=fid, algorithm=algorithm, quantity=mode, course_runs=20,
                               paper_runs=20 if mode == 'fitness' else 51,
                               reproduced_best=best, paper_mean=mean, reproduced_mean=measured, mean_difference=measured-mean,
                               paper_std=sd, reproduced_std=r['std'], std_difference=r['std']-sd,
                               relative_mean_difference=(measured-mean)/abs(mean) if abs(mean) > 1e-12 else 'NA_zero_reference'))
    return output


def main():
    for name in ['common_benchmark_validation.json', 'pems_native_validation.json', 'legacy_dls_validation.json', 'legacy_dsp_validation.json']:
        if not json.loads((OUT/name).read_text())['passed']:
            raise RuntimeError(f'verification gate not passed: {name}')
    protocol = load(ROOT/'results/common_benchmark')
    pems = load(ROOT/'results/pems_native_reference')
    dsp_native = load(ROOT/'legacy/dsp_native')
    dsp_ablation = load(ROOT/'legacy/dsp_ablation')
    dls = load(ROOT/'legacy/dls_native')
    groups = {
        'final': (protocol, FINAL),
        'pems_ablation': (protocol, ['PEMSDE', 'PEMS_no_peg', 'PEMS_no_mml', 'PEMS_no_ers', 'PEMS_no_cls']),
        'team_ablation': (protocol, ['TEAM', 'TEAM_no_peg', 'TEAM_no_phase', 'TEAM_no_escape']),
        'dsp_ablation': (dsp_ablation, ['DE', 'DSPDE', 'without_escape', 'without_linnik', 'without_social', 'frozen_roles']),
        'dls_ablation': (dls, ['dls_de', 'no_learning', 'no_two_phase', 'fixed_sigma', 'fitness_weights', 'binomial', 'de']),
        'pems_native': (pems, ['PEMSDE']),
        'dsp_native': (dsp_native, ['DSPDE']),
        'dls_native': (dls, ['dls_de']),
    }
    summary = {}
    for name, (data, algorithms) in groups.items():
        values = summarize(data, algorithms)
        csv_write(OUT/f'{name}_statistics.csv', values)
        average = [dict(algorithm=a, mean_rank=float(np.mean([r['rank'] for r in values if r['algorithm'] == a]))) for a in algorithms]
        csv_write(OUT/f'{name}_ranks.csv', average)
        summary[name] = dict(algorithms=algorithms, average_ranks=average)
    tests = {}
    for name, rows, reference, variants in [
        ('final', protocol, 'TEAM', FINAL[:-1]),
        ('pems_ablation', protocol, 'PEMSDE', groups['pems_ablation'][1][1:]),
        ('team_ablation', protocol, 'TEAM', groups['team_ablation'][1][1:]),
        ('dsp_ablation', dsp_ablation, 'DSPDE', groups['dsp_ablation'][1][2:]),
        ('dls_ablation', dls, 'dls_de', groups['dls_ablation'][1][1:-1]),
    ]:
        comparisons = compare(rows, reference, variants, name)
        csv_write(OUT/f'{name}_paired_tests.csv', comparisons)
        counts = []
        for a in variants:
            selected = [r for r in comparisons if r['comparison'] == a]
            counts.append(dict(comparison=a, reference_wins=sum(r['reference_result'] == 'win' for r in selected),
                               no_difference_detected=sum(r['reference_result'] == 'not_detected' for r in selected),
                               reference_losses=sum(r['reference_result'] == 'loss' for r in selected),
                               mean_better=sum(r['mean_difference'] < -(1e-8+1e-10*max(abs(r['reference_mean']),abs(r['comparison_mean']))) for r in selected),
                               mean_worse=sum(r['mean_difference'] > 1e-8+1e-10*max(abs(r['reference_mean']),abs(r['comparison_mean'])) for r in selected)))
        csv_write(OUT/f'{name}_comparison_counts.csv', counts)
        tests[name] = counts
    for name, rows, algorithm, filename, mode in [
        ('dsp', dsp_native, 'DSPDE', 'dspde_table7.csv', 'fitness'),
        ('dls', dls, 'dls_de', 'dlsde_table12.csv', 'error'),
        ('pems', pems, 'PEMSDE', 'pemsde_table2.csv', 'error'),
    ]:
        comparison = paper_comparison(rows, algorithm, ROOT/'source/paper_tables'/filename, mode)
        csv_write(OUT/f'{name}_paper_comparison.csv', comparison)
    runs = []
    for r in protocol:
        runs.append({key: r[key] for key in ['algorithm', 'function', 'run', 'seed', 'fun', 'optimum', 'error', 'nfev', 'seconds']})
    csv_write(OUT/'coursework_runs.csv', runs)
    report = dict(author='殷明骏', student_id='202483890029', summaries=summary, comparisons=tests,
                  new_formal_runs=len(protocol)+len(pems), legacy_runs=len(dls)+len(dsp_native)+len(dsp_ablation),
                  final_comparison_runs=3000, numpy=np.__version__)
    (OUT/'analysis_summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
