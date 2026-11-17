"""Archive-backed potential/elite DE revision. Author: 殷明骏.

Two selected strategy groups: stochastic potential/elite guidance (PEMS-DE
inspired) and success-history two-phase parameter control (DLS-DE inspired).
Archive and parent-midpoint repair support the current-to-pbest backbone.
The frozen PGE-DE implementation remains in ../code/team_de.py.
"""
import numpy as np

VARIANTS = ('APE', 'APE_no_potential', 'APE_no_control')


def positive_cauchy(rng, center, scale=.1):
    f = center + scale*rng.standard_cauchy(len(center))
    while (bad := f <= 0).any():
        f[bad] = center[bad] + scale*rng.standard_cauchy(int(bad.sum()))
    return np.minimum(f, 1.)


def minimize(objective, bounds, *, max_fes=100000, population_size=100,
             seed=0, variant='APE', trace_interval=1000):
    box = np.asarray(bounds, float)
    if (box.ndim != 2 or box.shape[1] != 2 or len(box) < 1
            or not np.isfinite(box).all() or np.any(box[:, 0] >= box[:, 1])
            or variant not in VARIANTS or not isinstance(population_size, int)
            or population_size < 4 or not isinstance(max_fes, int)
            or max_fes < population_size or trace_interval < 1):
        raise ValueError('invalid configuration')
    n, d = population_size, len(box)
    lo, hi = box.T
    rng = np.random.default_rng(seed)
    x = rng.uniform(lo, hi, (n, d))

    def evaluate(points):
        values = np.asarray([objective(row) for row in points], float)
        if values.shape != (len(points),) or not np.isfinite(values).all():
            raise ValueError('objective must return finite scalar values')
        return values

    fit = evaluate(x)
    gain_previous = np.zeros(n)
    archive = np.empty((0, d))
    mf, mcr = np.full(6, .5), np.full(6, .5)
    cursor, sr, fes = 0, .5, n
    history = [[fes, float(fit.min())]]
    next_trace = fes + trace_interval
    diag = dict(initial_population=n, min_population=n, max_population=n,
                generations=0, accepted=0, potential_guides=0,
                elite_guides=0, repaired_coordinates=0, max_archive=0,
                phase1_evaluations=0, phase2_evaluations=0,
                archive_draws=0, parameter_updates=0)
    while fes < max_fes:
        count = min(n, max_fes-fes)
        ids = np.arange(count)
        parents = x[:count].copy()
        order = np.argsort(fit, kind='stable')
        ratio = fes/max_fes
        elite = order[:max(2, int(np.floor(.11*n+.5)))]
        guide_ids = elite[rng.integers(len(elite), size=count)]
        # Improvement identifies candidates, while the fitness gate prevents a
        # fast-improving but still poor member from steering the whole search.
        eligible = np.flatnonzero((gain_previous > 0) & (fit <= np.median(fit)))
        potential = np.zeros(count, bool)
        if variant != 'APE_no_potential' and len(eligible):
            potential = rng.random(count) < .25*(1-ratio)
            guide_ids[potential] = eligible[rng.integers(len(eligible), size=int(potential.sum()))]
        diag['potential_guides'] += int(potential.sum())
        diag['elite_guides'] += count-int(potential.sum())
        memory_rows = rng.integers(6, size=count)
        if variant == 'APE_no_control':
            factors, cr = np.full(count, .5), np.full(count, .9)
        else:
            if ratio < .3:
                perturb = np.sin(2*np.pi*rng.random(count))*(mf.mean()-mf.min())
                factors = np.clip(.35+.4*sr/(.1+sr)+perturb, .35, .65)
                diag['phase1_evaluations'] += count
            else:
                factors = positive_cauchy(rng, mf[memory_rows])
                diag['phase2_evaluations'] += count
            cr = np.clip(mcr[memory_rows] + .1*rng.standard_normal(count), 0, 1)
        r1 = rng.integers(n, size=count)
        while (bad := r1 == ids).any():
            r1[bad] = rng.integers(n, size=int(bad.sum()))
        union = np.concatenate((x, archive))
        r2 = rng.integers(len(union), size=count)
        while (bad := (r2 == ids) | (r2 == r1)).any():
            r2[bad] = rng.integers(len(union), size=int(bad.sum()))
        diag['archive_draws'] += int((r2 >= n).sum())
        mutant = parents + factors[:, None]*(x[guide_ids]-parents+x[r1]-union[r2])
        mask = rng.random((count, d)) < cr[:, None]
        mask[ids, rng.integers(d, size=count)] = True
        trial = np.where(mask, mutant, parents)
        diag['repaired_coordinates'] += int(((trial < lo) | (trial > hi)).sum())
        trial = np.where(trial < lo, (parents+lo)/2,
                         np.where(trial > hi, (parents+hi)/2, trial))
        values = evaluate(trial)
        gains = fit[:count]-values
        accepted = gains > 0
        gain_previous[:] = 0
        gain_previous[ids[accepted]] = gains[accepted]
        if accepted.any():
            archive = np.concatenate((archive, parents[accepted]))
            capacity = int(np.floor(1.6*n+.5))
            if len(archive) > capacity:
                archive = archive[rng.choice(len(archive), capacity, replace=False)]
            diag['max_archive'] = max(diag['max_archive'], len(archive))
            if variant != 'APE_no_control':
                weights = gains[accepted]/gains[accepted].sum()
                sf, scr = factors[accepted], cr[accepted]
                mf[cursor] = np.sum(weights*sf*sf)/np.sum(weights*sf)
                mcr[cursor] = np.sum(weights*scr)
                cursor = (cursor+1) % 6
                diag['parameter_updates'] += 1
            x[ids[accepted]], fit[ids[accepted]] = trial[accepted], values[accepted]
        sr = float(accepted.mean())
        diag['accepted'] += int(accepted.sum())
        diag['generations'] += 1
        fes += count
        if fes >= next_trace or fes == max_fes:
            history.append([fes, float(fit.min())])
            next_trace = fes+trace_interval
    best = int(fit.argmin())
    diag['final_f_memory'], diag['final_cr_memory'] = mf.tolist(), mcr.tolist()
    return dict(x=x[best].tolist(), fun=float(fit[best]), nfev=fes,
                history=history, diagnostics=diag)
