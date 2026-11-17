"""PEMS-DE: Algorithm 4, Sahu & Gupta (2026). Author: 殷明骏.

Independent correction of the delivered batch implementation. Parent donors
are frozen at generation g; archive and successful-parameter sets update after
each individual, as Algorithm 4 specifies. No historical result is overwritten.
"""
import math
import numpy as np


VARIANTS = ('PEMSDE', 'PEMS_no_peg', 'PEMS_no_mml', 'PEMS_no_ers', 'PEMS_no_cls')


def potential_guidance(pop, fit, previous_fit, ratio):
    n = len(pop)
    phi = np.divide(previous_fit-fit, fit, out=previous_fit-fit,
                    where=fit != 0)
    phi = np.nan_to_num(phi, nan=-np.inf)
    size = max(2, min(n-1, math.ceil(math.cos(ratio*math.pi/3)*math.ceil(n*.382))))
    ids = np.lexsort((fit, -phi))[:size]
    weights = fit[ids].max()-fit[ids]
    guide = (weights/weights.sum()) @ pop[ids] if weights.sum() > 0 else pop[ids[0]].copy()
    membership = np.zeros(n, bool)
    membership[ids] = True
    return guide, membership


def minimize(objective, bounds, *, max_fes=100000, population_size=None,
             seed=0, variant='PEMSDE', trace_interval=1000):
    box = np.asarray(bounds, float)
    if box.ndim != 2 or box.shape[1] != 2 or not np.isfinite(box).all() or np.any(box[:, 0] >= box[:, 1]):
        raise ValueError('invalid bounds')
    d = len(box)
    n = 6*d if population_size is None else population_size
    if variant not in VARIANTS or not isinstance(n, int) or n < 4 or max_fes < n or trace_interval < 1:
        raise ValueError('invalid configuration')
    rng = np.random.default_rng(seed)
    lo, hi = box.T
    pop = rng.uniform(lo, hi, (n, d))
    fit = np.array([objective(x) for x in pop], float)
    if not np.isfinite(fit).all():
        raise ValueError('non-finite objective')
    fes = n
    previous_fit = fit.copy()
    best_id = int(fit.argmin())
    best, best_x = float(fit[best_id]), pop[best_id].copy()
    mu_f = mu_cr = .5
    # Store sufficient statistics for weighted Lehmer/arithmetic means; these
    # are algebraically identical to retaining all successes between resets.
    sf_num = sf_den = scr_sum = 0.
    success_count = 0
    archive = np.empty((n, d))
    arc_n = 0
    stagnation = np.zeros(n, int)
    s_gen = g = 0
    history = [[fes, best]]
    next_trace = fes+trace_interval
    diag = dict(initial_population=n, min_population=n, max_population=n,
                initialization_evaluations=n, mutation_evaluations=0,
                cls_evaluations=0, ers_evaluations=0, memory_resets=0,
                narrow_f_samples=0, broad_f_samples=0, max_archive=0,
                updating='frozen generation parents; immediate archive/success updates')
    while fes < max_fes:
        ratio = fes/max_fes
        old = pop.copy()
        old_fit = fit.copy()
        generation_best = best
        if g % 20 == 0:
            sf_num = sf_den = scr_sum = 0.
            success_count = arc_n = 0
            diag['memory_resets'] += 1
        if variant != 'PEMS_no_peg':
            guide, membership = potential_guidance(old, old_fit, previous_fit, ratio)
            k = max(1, math.ceil((.25-.2*ratio)*n))
            elite = np.argsort(old_fit, kind='stable')[:k]
            pbest = old[elite[int(rng.integers(k))]].copy()
            delta = .5*math.exp(1.5*(1-ratio))-.4
            celite = delta*pbest+(1-delta)*best_x
        else:
            guide = pbest = celite = best_x.copy()
            membership = np.zeros(n, bool)
        use_ers = variant != 'PEMS_no_ers' and s_gen > 5
        for i in range(n):
            if fes >= max_fes:
                break
            individual_ratio = fes/max_fes
            # The width may change within a generation after the first success.
            scale = .1 if success_count else .5
            diag['narrow_f_samples' if success_count else 'broad_f_samples'] += 1
            f = mu_f+scale*rng.standard_cauchy()
            while not np.isfinite(f) or f <= 0:
                f = mu_f+scale*rng.standard_cauchy()
            f = min(f, 1.)
            cr = float(np.clip(mu_cr+scale*rng.standard_normal(), 0, 1))
            r1 = int(rng.integers(n-1))
            r1 += r1 >= i
            r2 = int(rng.integers(n))
            while r2 == i or r2 == r1:
                r2 = int(rng.integers(n))
            arc = archive[int(rng.integers(arc_n))] if arc_n else old[int(rng.integers(n))]
            if variant == 'PEMS_no_mml':
                mutant = old[i]+f*(guide-old[i])+.8*f*(old[r1]-arc)
            elif individual_ratio < 1/3:
                mutant = old[i]+f*(guide-old[i])+f*(old[r1]-old[r2])
            else:
                fw = (.7 if individual_ratio < .2 else .8 if individual_ratio < .4 else 1.2)*f
                target = guide if individual_ratio < 2/3 else celite
                mutant = old[i]+fw*(target-old[i])+.8*fw*(old[r1]-arc)
            if use_ers:
                trial = mutant+(rng.random()-.3)*(mutant-pbest)
                diag['ers_evaluations'] += 1
            else:
                mask = rng.random(d) <= cr
                mask[int(rng.integers(d))] = True
                trial = np.where(mask, mutant, old[i])
            trial = np.clip(trial, lo, hi)
            value = float(objective(trial))
            if not np.isfinite(value):
                raise ValueError('non-finite objective')
            fes += 1
            diag['mutation_evaluations'] += 1
            if value < old_fit[i]:
                gain = old_fit[i]-value
                sf_num += gain*f*f
                sf_den += gain*f
                scr_sum += cr
                success_count += 1
            if value <= old_fit[i]:
                pop[i], fit[i] = trial, value
                stagnation[i] = 0
                # Randomly discard one of all N+1 entries, including new parent.
                if arc_n < n:
                    archive[arc_n] = old[i]
                    arc_n += 1
                else:
                    drop = int(rng.integers(n+1))
                    if drop < n:
                        archive[drop] = old[i]
                if value < best:
                    best, best_x = value, trial.copy()
            else:
                stagnation[i] += 1
        diag['max_archive'] = max(diag['max_archive'], arc_n)
        if g % 20:
            mu_f = .1*(sf_num/sf_den)+.9*mu_f if success_count else 1-mu_f
            mu_cr = .1*(scr_sum/success_count)+.9*mu_cr if success_count else 1-mu_cr
        s_gen = 0 if use_ers or best < generation_best else s_gen+1
        if variant != 'PEMS_no_cls':
            # Eq.18 replaces a stagnant individual even if the replacement is
            # worse; best-so-far remains separately preserved.
            for i in np.flatnonzero(stagnation > 20):
                if fes >= max_fes:
                    break
                base = pop.mean(axis=0) if membership[i] else celite
                trial = np.clip(base+(.9-.8*fes/max_fes)*(base-pop[i]), lo, hi)
                value = float(objective(trial))
                if not np.isfinite(value):
                    raise ValueError('non-finite objective')
                fes += 1
                diag['cls_evaluations'] += 1
                pop[i], fit[i], stagnation[i] = trial, value, 0
                if value < best:
                    best, best_x = value, trial.copy()
        previous_fit = old_fit
        g += 1
        if fes >= next_trace or fes == max_fes:
            history.append([fes, best])
            next_trace = fes+trace_interval
    diag.update(generations=g, mu_f=float(mu_f), mu_cr=float(mu_cr))
    return dict(x=best_x.tolist(), fun=best, nfev=fes, history=history, diagnostics=diag)
