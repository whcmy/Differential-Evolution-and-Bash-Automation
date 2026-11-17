"""PGE-DE: potential guidance + two-phase F + probabilistic escape.

Author: 殷明骏, 202483890029. This is a common_benchmark combination, not a
claim of a new published optimization theory. Fixed population, binomial
crossover CR=.9, success-history memory H=6, no population reduction.
"""
import numpy as np
from basic_de import donor_indices
from dls_de import cauchy_positive
from dspde import Gaussian, mixture, gradient_direction
from pems_de import potential_guidance

VARIANTS = ('TEAM', 'TEAM_no_peg', 'TEAM_no_phase', 'TEAM_no_escape')


def minimize(objective, bounds, *, max_fes=100000, population_size=100,
             seed=0, variant='TEAM', trace_interval=1000):
    box = np.asarray(bounds, float)
    n = population_size
    if (variant not in VARIANTS or box.ndim != 2 or box.shape[1] != 2
            or not np.isfinite(box).all() or np.any(box[:, 0] >= box[:, 1])
            or n < 18 or max_fes < n or trace_interval < 1):
        raise ValueError('invalid configuration')
    rng = np.random.default_rng(seed)
    lo, hi = box.T
    d = len(box)
    x = rng.uniform(lo, hi, (n, d))
    fit = np.array([objective(p) for p in x], float)
    if not np.isfinite(fit).all():
        raise ValueError('non-finite objective')
    previous_fit = fit.copy()
    fes, index, sr = n, 0, .5
    mf = np.full(6, .5)
    ng = max(6, int(np.floor(n*.618/3+.5)))
    history = [[fes, float(fit.min())]]
    next_trace = fes+trace_interval
    diag = dict(initial_population=n, min_population=n, max_population=n,
                phase1_evaluations=0, phase2_evaluations=0, escape_evaluations=0,
                gradient_evaluations=0, mirror_evaluations=0, generations=0)
    while fes < max_fes:
        ratio = fes/max_fes
        count = min(n, max_fes-fes)
        targets = np.arange(count)
        old_fit = fit.copy()
        order = np.argsort(fit, kind='stable')
        if variant != 'TEAM_no_peg':
            guide, _ = potential_guidance(x, fit, previous_fit, ratio)
        else:
            k = max(2, int(np.floor(.11*n+.5)))
            guide = x[order[rng.integers(k, size=count)]]
        if ratio < .3 and variant != 'TEAM_no_phase':
            perturb = np.sin(2*np.pi*rng.random(count))*(mf.mean()-mf.min())
            factors = np.clip(.35+.4*sr/(.1+sr)+perturb, .35, .65)
            diag['phase1_evaluations'] += count
        else:
            factors = cauchy_positive(rng, mf[rng.integers(6, size=count)], .05)
            diag['phase2_evaluations'] += count
        donors = donor_indices(rng, n, targets)
        mutant = x[:count]+factors[:, None]*(guide-x[:count]+x[donors[:, 1]]-x[donors[:, 2]])
        mask = rng.random((count, d)) < .9
        mask[targets, rng.integers(d, size=count)] = True
        trial = np.where(mask, mutant, x[:count])
        escaped = np.empty(0, int)
        if variant != 'TEAM_no_escape':
            inferior = order[-ng:]
            inferior = inferior[inferior < count]
            elite_model = Gaussian(x[order[:ng]], 1e-6)
            global_model = Gaussian(x, 1e-6)
            lp, score = mixture(elite_model, global_model, x[inferior], .7)
            eligible = lp < np.log(.2*(1-.9*ratio))
            escaped = inferior[eligible]
            lp, score = lp[eligible], score[eligible]
            gradient = rng.random(len(escaped)) < .7
            gids, mids = escaped[gradient], escaped[~gradient]
            step = .1*(1-.9*ratio)
            direction, _ = gradient_direction(lp[gradient], score[gradient], 1e-6)
            trial[gids] = x[gids]-step*direction+rng.normal(0, step, (len(gids), d))
            which = rng.random(len(mids)) < .5
            trial[mids[which]] = 2*global_model.mean-elite_model.sample(rng, int(which.sum()))
            trial[mids[~which]] = 2*elite_model.mean-global_model.sample(rng, int((~which).sum()))
            diag['escape_evaluations'] += len(escaped)
            diag['gradient_evaluations'] += len(gids)
            diag['mirror_evaluations'] += len(mids)
        trial = np.clip(trial, lo, hi)
        values = np.array([objective(p) for p in trial], float)
        if not np.isfinite(values).all():
            raise ValueError('non-finite objective')
        accepted = values < fit[:count]
        # Escape candidates do not arise from their sampled F, so they must
        # not train its success memory.
        learn = accepted.copy()
        learn[escaped] = False
        if learn.any():
            gain = fit[:count][learn]-values[learn]
            f = factors[learn]
            mf[index] = float(np.sum(gain*f*f)/np.sum(gain*f))
            index = (index+1) % 6
        sr = float(learn.sum()/count)
        chosen = targets[accepted]
        x[chosen], fit[chosen] = trial[accepted], values[accepted]
        previous_fit = old_fit
        fes += count
        diag['generations'] += 1
        if fes >= next_trace or fes == max_fes:
            history.append([fes, float(fit.min())])
            next_trace = fes+trace_interval
    best = int(fit.argmin())
    return dict(x=x[best].tolist(), fun=float(fit[best]), nfev=fes, history=history, diagnostics=diag)
