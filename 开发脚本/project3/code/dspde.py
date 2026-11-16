"""Source-grounded DSPDE reconstruction; unresolved paper details in ASSUMPTIONS.md."""
from dataclasses import dataclass, asdict
import numpy as np
from basic_de import donor_indices


@dataclass(frozen=True)
class Settings:
    population_size: int = 100
    max_fes: int = 100000
    elite_weight: float = 0.7
    regularization: float = 1e-6
    gradient_probability: float = 0.7
    linnik_alpha: float = 1.0  # selected convention, NOT an author-reported default
    linnik_v: float = 0.5      # selected convention, NOT an author-reported default
    baseline_f: float = 0.5
    baseline_cr: float = 0.9


VARIANTS = ('DSPDE', 'without_escape', 'without_linnik', 'without_social', 'frozen_roles')


def knowledge_rate(rng, ranks):
    """Eqs 21-22, one-based fitness ranks; MATLAB-style round then divide by 2."""
    phi = 0.25 + 0.55 * np.sqrt(ranks / len(ranks))
    return np.floor(rng.random(len(ranks)) * phi
                    + (rng.random(len(ranks)) <= phi) + 0.5) / 2


def linnik(rng, shape, alpha=1.0, v=0.5):
    """Eq17 with explicit real signed-power convention; alpha=1 needs no extension.

    The paper supplies neither numeric alpha/v nor its random pool size.
    We generate variates directly instead of inventing a finite pool size.
    """
    u = rng.uniform(-1, 1, shape)
    z = rng.laplace(0, 1, shape)
    base = np.sin(np.pi*v/2) * np.tan(np.pi*(1-v*u)/2) - np.cos(np.pi*v/2)
    return v * z * np.sign(base) * np.abs(base)**(1/alpha)


class Gaussian:
    def __init__(self, population, epsilon=1e-6):
        self.mean = population.mean(axis=0)
        self.cov = np.atleast_2d(np.cov(population, rowvar=False, ddof=1))
        self.cov += epsilon*np.eye(population.shape[1])
        self.cholesky = np.linalg.cholesky(self.cov)
        self.precision = np.linalg.solve(self.cov, np.eye(len(self.mean)))
        self.log_normalizer = -0.5*(len(self.mean)*np.log(2*np.pi)
                                   + 2*np.log(np.diag(self.cholesky)).sum())

    def log_density_and_score(self, x):
        delta = x - self.mean
        score = -delta @ self.precision
        logpdf = self.log_normalizer + 0.5*np.sum(delta*score, axis=1)
        return logpdf, score

    def sample(self, rng, count):
        return self.mean + rng.normal(size=(count, len(self.mean))) @ self.cholesky.T


def mixture(elite, global_model, points, weight=0.7):
    """Log density and score = grad(log p), avoiding density under/overflow."""
    le, se = elite.log_density_and_score(points)
    lg, sg = global_model.log_density_and_score(points)
    a, b = np.log(weight)+le, np.log1p(-weight)+lg
    lp = np.logaddexp(a, b)
    score = np.exp(a-lp)[:, None]*se + np.exp(b-lp)[:, None]*sg
    return lp, score


def gradient_direction(log_density, score, epsilon):
    """Compute grad(p)/(norm(grad(p))+epsilon), retaining absolute density scale."""
    norms = np.linalg.norm(score, axis=1)
    lognorm = log_density + np.log(np.maximum(norms, np.finfo(float).tiny))
    direction = score / np.maximum(norms[:, None], np.finfo(float).tiny)
    # Algorithm1 uses random perturbation only when ||gradient|| <= epsilon.
    active = (norms > 0) & (lognorm > np.log(epsilon))
    factor = np.exp(lognorm - np.logaddexp(lognorm, np.log(epsilon)))
    direction *= (active*factor)[:, None]
    return direction, active


def minimize(objective, bounds, *, settings=Settings(), seed=0, variant='DSPDE', trace_interval=1000):
    if variant not in VARIANTS:
        raise ValueError(f'unknown variant: {variant}')
    box = np.asarray(bounds, dtype=float)
    n, budget = settings.population_size, settings.max_fes
    if box.ndim != 2 or box.shape[1] != 2 or not len(box) or not np.isfinite(box).all() or np.any(box[:, 0] >= box[:, 1]):
        raise ValueError('invalid bounds')
    if n < 18 or budget < n or trace_interval < 1:
        raise ValueError('require NP>=18, max_fes>=NP, positive trace_interval')
    if not (0 < settings.elite_weight < 1 and 0 <= settings.gradient_probability <= 1
            and settings.regularization > 0 and settings.linnik_alpha > 0
            and 0 < settings.linnik_v < 1 and 0 < settings.baseline_f <= 2
            and 0 <= settings.baseline_cr <= 1):
        raise ValueError('invalid algorithm settings')
    rng = np.random.default_rng(seed)
    lo, hi = box.T
    d = len(box)
    pop = rng.uniform(lo, hi, (n, d))

    def evaluate(points):
        values = np.array([objective(p) for p in points], dtype=float)
        if not np.isfinite(values).all():
            raise ValueError('objective returned a non-finite value')
        return values

    fitness = evaluate(pop)
    fes, generation = n, 0
    ng = max(6, int(np.floor(n*0.618/3+0.5)))
    if 2*ng >= n:
        raise ValueError('subgroups leave no ordinary individuals')
    initial_order = np.argsort(fitness, kind='stable')
    history = [(fes, float(fitness.min()))]
    next_trace = fes+trace_interval
    counters = {k: 0 for k in ('elite_candidates','social_candidates','inferior_candidates',
                               'escape_triggered','gradient_candidates','active_gradients',
                               'mirror_candidates','random_resets','accepted','noop_candidates')}
    max_generations = max(1, int(np.ceil((budget-n)/n)))
    while fes < budget:
        generation += 1
        progress = generation/max_generations  # FE-compatible with the paper's t/MaxIt
        order = np.argsort(fitness, kind='stable')
        ranks = np.empty(n, int); ranks[order] = np.arange(1, n+1)
        roles_order = initial_order if variant == 'frozen_roles' else order
        elite_ids, inferior_ids = roles_order[:ng], roles_order[-ng:]
        normal_ids = roles_order[ng:-ng]
        eta = knowledge_rate(rng, ranks)
        trial = pop.copy()

        # Baseline fallback is confined to the ablated subgroup.
        if variant in ('without_linnik', 'without_social'):
            ids = elite_ids if variant == 'without_linnik' else normal_ids
            donors = donor_indices(rng, n, ids)
            mutant = np.clip(pop[donors[:, 0]] + settings.baseline_f*(pop[donors[:, 1]]-pop[donors[:, 2]]), lo, hi)
            mask = rng.random((len(ids), d)) < settings.baseline_cr
            mask[np.arange(len(ids)), rng.integers(d, size=len(ids))] = True
            trial[ids] = np.where(mask, mutant, pop[ids])

        if variant != 'without_linnik':
            peer = rng.integers(n, size=ng)  # Eq18 allows any random individual
            candidate = pop[peer] + linnik(rng, (ng, d), settings.linnik_alpha, settings.linnik_v)
            mask = rng.random((ng, d)) < eta[elite_ids, None]
            trial[elite_ids] = np.where(mask, candidate, pop[elite_ids])
        if variant != 'without_social':
            peer = rng.integers(n-1, size=len(normal_ids))
            peer += peer >= normal_ids  # uniform non-self peer, Section3.5
            best = pop[order[0]]
            lam = 0.1+0.618*np.sqrt(max(0, 1-progress))
            r = rng.random((len(normal_ids), 1))
            candidate = best + lam*(best-pop[normal_ids]) + r*(pop[peer]-pop[normal_ids])
            mask = rng.random((len(normal_ids), d)) < eta[normal_ids, None]
            trial[normal_ids] = np.where(mask, candidate, pop[normal_ids])

        count = min(n, budget-fes)
        # Only create/charge counters for inferior targets actually evaluated.
        active_inferior = inferior_ids[inferior_ids < count]
        trial[active_inferior] = rng.uniform(lo, hi, (len(active_inferior), d))
        escaped = np.array([], dtype=int)
        if variant != 'without_escape' and len(active_inferior):
            model_e = Gaussian(pop[elite_ids], settings.regularization)
            model_g = Gaussian(pop, settings.regularization)
            logpdf, score = mixture(model_e, model_g, pop[active_inferior], settings.elite_weight)
            tau = 0.2*(1-0.9*progress)
            # Eq8 is misprinted. Infer low-density AND current inferior rank from prose.
            eligible = (logpdf < np.log(tau)) & (ranks[active_inferior] > n-ng)
            escaped = active_inferior[eligible]
            lp, sc = logpdf[eligible], score[eligible]
            use_gradient = rng.random(len(escaped)) < settings.gradient_probability
            grad_ids, mirror_ids = escaped[use_gradient], escaped[~use_gradient]
            step = 0.1*(1-0.9*progress)
            direction, active = gradient_direction(lp[use_gradient], sc[use_gradient], settings.regularization)
            trial[grad_ids] = pop[grad_ids]-step*direction+rng.normal(0, step, (len(grad_ids), d))
            from_elite = rng.random(len(mirror_ids)) < 0.5
            trial[mirror_ids[from_elite]] = 2*model_g.mean-model_e.sample(rng, int(from_elite.sum()))
            trial[mirror_ids[~from_elite]] = 2*model_e.mean-model_g.sample(rng, int((~from_elite).sum()))
            counters['escape_triggered'] += len(escaped)
            counters['gradient_candidates'] += len(grad_ids)
            counters['active_gradients'] += int(active.sum())
            counters['mirror_candidates'] += len(mirror_ids)
        counters['random_resets'] += len(active_inferior)-len(escaped)
        trial = np.clip(trial[:count], lo, hi)
        if not np.isfinite(trial).all():
            raise FloatingPointError('non-finite candidate')
        values = evaluate(trial)
        accepted = np.flatnonzero(values < fitness[:count])
        counters['accepted'] += len(accepted)
        counters['noop_candidates'] += int(np.all(trial == pop[:count], axis=1).sum())
        for key, ids in [('elite_candidates',elite_ids), ('social_candidates',normal_ids), ('inferior_candidates',inferior_ids)]:
            counters[key] += int((ids < count).sum())
        pop[accepted], fitness[accepted] = trial[accepted], values[accepted]
        fes += count
        if fes >= next_trace or fes == budget:
            history.append((fes, float(fitness.min())))
            next_trace = fes+trace_interval
    best = int(fitness.argmin())
    return dict(x=pop[best].tolist(), fun=float(fitness[best]), nfev=fes,
                history=history, counters=counters, generations=generation, subgroup_size=ng)
