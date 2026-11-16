"""DLS-DE, Chen & Meng (2026), equations (3), (8)-(17), Algorithms 4-6.

See reference/implementation_notes.md for all underspecified paper conventions.
Only NumPy is needed to use this optimizer with an arbitrary scalar objective.
"""
from dataclasses import dataclass
from typing import Callable
import numpy as np


VARIANTS = ("dls_de", "no_learning", "no_two_phase", "fixed_sigma",
            "fitness_weights", "binomial", "de")


@dataclass
class Result:
    x: np.ndarray
    fun: float
    nfev: int
    history: list
    diagnostics: dict


def round_half_up(x):
    """MATLAB-compatible rounding for nonnegative population/archive sizes."""
    return int(np.floor(x + 0.5))


def initial_population_size(dimension):
    return max(4, round_half_up(25 * np.log(dimension) * np.sqrt(dimension)))


def exponential_mask(rng, count, dimension, cr):
    """One contiguous circular block; at least one mutant coordinate per row."""
    # Pre-sampling unused uniforms changes RNG consumption, not the distribution.
    lengths = 1 + np.cumprod(rng.random((count, dimension - 1)) < cr[:, None],
                            axis=1).sum(axis=1)
    starts = rng.integers(dimension, size=count)
    offsets = (np.arange(dimension)[None, :] - starts[:, None]) % dimension
    return offsets < lengths[:, None]


def cauchy_positive(rng, centers, scales):
    """Resample nonpositive F; cap positive F at 1 (SHADE convention)."""
    centers, scales = np.broadcast_arrays(centers, scales)
    values = centers + scales * rng.standard_cauchy(centers.shape)
    while (bad := values <= 0).any():
        values[bad] = centers[bad] + scales[bad] * rng.standard_cauchy(int(bad.sum()))
    return np.minimum(values, 1.0)


def repair(trial, parents, lower, upper):
    """SHADE-style midpoint repair of out-of-bounds trial coordinates."""
    return np.where(trial < lower, (parents + lower) / 2,
                    np.where(trial > upper, (parents + upper) / 2, trial))


def successful_weights(displacements, gains=None):
    """Equation (10) uses sample SD across *all D coordinates*, including zeros."""
    raw = np.std(displacements, axis=1, ddof=1) if gains is None else gains
    total = float(raw.sum())
    return raw / total if total > 0 else np.full(len(raw), 1 / len(raw))


def update_probability(lengths, weights, dimension, population_size):
    """Equations (15)-(16), including the special all-k=1 zero vector."""
    if np.all(lengths == 1):
        return np.zeros(dimension)
    counts = np.bincount(lengths - 1, minlength=dimension)
    grouped = np.bincount(lengths - 1, weights=weights, minlength=dimension)
    v = np.divide(grouped, counts, out=np.zeros(dimension), where=counts > 0)
    xi = min(1 / population_size, 1 / dimension)
    pk = counts / len(lengths) * v / v.sum() + xi
    return pk / pk.sum()


def update_learning(lv, lf, parents_f, trials_f, predecessor_f, delta, mask):
    """Algorithm 4: record only strictly intermediate unsuccessful trials."""
    promising = (parents_f < trials_f) & (trials_f < predecessor_f)
    lv[promising] += (delta * mask)[promising]
    lf[promising] += mask[promising]
    return int(promising.sum())


def minimize(objective: Callable, bounds, *, max_fes=100_000, seed=0,
             population_size=None, min_population_size=4, memory_size=6,
             p=0.11, archive_ratio=1.6, phase_fraction=0.3,
             sigma_initial=0.05, lambda_sigma=0.1, stagnation_threshold=30,
             tau=0.3, gate="pseudocode", variant="dls_de", trace_interval=1000):
    """Generational, minimization-only DLS-DE; initialization counts towards FEs.

    The default gate follows Algorithm 5: one draw per generation, rand > tau.
    gate='text' instead implements the prose's probability tau (rand < tau).
    Equality is accepted, per Algorithm 6 lines 25-29. Learning state is removed
    alongside its individual during population reduction. Final partial
    generations evaluate only the remaining targets, never exceeding max_fes.
    'de' is a fixed-population DE/rand/1/bin, F=.5, CR=.9 baseline.
    """
    box = np.asarray(bounds, dtype=float)
    if box.ndim != 2 or box.shape[1] != 2 or len(box) < 2:
        raise ValueError("bounds must have shape (D,2), D >= 2")
    if not np.isfinite(box).all() or not (box[:, 0] < box[:, 1]).all():
        raise ValueError("finite lower < upper bounds required")
    d = len(box)
    n0 = initial_population_size(d) if population_size is None else population_size
    if (not isinstance(n0, int) or not isinstance(min_population_size, int)
            or not 4 <= min_population_size <= n0):
        raise ValueError("integer NP_init >= NP_min >= 4 required")
    if not isinstance(max_fes, int) or max_fes < n0:
        raise ValueError("max_fes must be an integer >= NP_init")
    if (variant not in VARIANTS or gate not in ("pseudocode", "text")
            or not isinstance(memory_size, int) or memory_size < 1
            or not 0 < p <= 1 or not 0 <= tau <= 1
            or not 0 <= phase_fraction <= 1 or not np.isfinite(archive_ratio)
            or archive_ratio < 0 or not np.isfinite(sigma_initial) or sigma_initial <= 0
            or not np.isfinite(lambda_sigma) or lambda_sigma <= 0
            or not isinstance(stagnation_threshold, int) or stagnation_threshold < 0
            or not isinstance(trace_interval, int) or trace_interval < 1):
        raise ValueError("invalid strategy parameters")
    rng = np.random.default_rng(seed)
    lower, upper = box.T
    x = rng.uniform(lower, upper, (n0, d))

    def evaluate(points):
        values = np.asarray([objective(row) for row in points], dtype=float)
        if values.shape != (len(points),) or not np.isfinite(values).all():
            raise ValueError("objective must return a finite scalar")
        return values

    fitness = evaluate(x)
    nfev = n0
    history = [[nfev, float(fitness.min())]]
    next_trace = nfev + trace_interval
    archive = np.empty((0, d))
    predecessor_f = fitness.copy()  # Y=P initially; only its fitness is needed.
    lv, lf = np.zeros_like(x), np.zeros_like(x, dtype=np.int64)
    ct = np.zeros(n0, dtype=np.int64)
    mf = np.full(memory_size, 0.5)
    prob = np.full((memory_size, d), 1 / d)
    memory_index, sigma, previous_sf_mean, sr = 0, sigma_initial, 0.0, 0.5
    stats = dict(generations=0, learning_trials=0, learning_records=0,
                 sigma_overrides=0, phase1_trials=0, phase2_trials=0,
                 zero_weight_fallbacks=0, accepted=0, strict_improvements=0,
                 initial_population=n0, min_population_seen=n0, max_archive=0)
    while nfev < max_fes:
        n = len(x)
        count = min(n, max_fes - nfev)
        targets = np.arange(count)
        parents = x[:count].copy()
        if variant == "de":
            donors = rng.integers(n, size=(count, 3))
            while True:
                invalid = ((donors == targets[:, None]).any(axis=1)
                           | (donors[:, 0] == donors[:, 1])
                           | (donors[:, 0] == donors[:, 2])
                           | (donors[:, 1] == donors[:, 2]))
                if not invalid.any():
                    break
                donors[invalid] = rng.integers(n, size=(int(invalid.sum()), 3))
            trial = x[donors[:, 0]] + .5 * (x[donors[:, 1]] - x[donors[:, 2]])
            mask = rng.random((count, d)) < .9
            mask[targets, rng.integers(d, size=count)] = True
            trial = np.where(mask, trial, parents)
        else:
            memory_rows = rng.integers(memory_size, size=count)
            early = nfev < phase_fraction * max_fes and variant != "no_two_phase"
            if early:
                perturb = np.sin(2 * np.pi * rng.random(count)) * (mf.mean() - mf.min())
                factors = np.clip(.35 + .4 * sr / (.1 + sr) + perturb, .35, .65)
            else:
                factors = cauchy_positive(rng, mf[memory_rows], sigma)
            stats["phase1_trials" if early else "phase2_trials"] += count
            override = (ct[:count] > 0) & (ct[:count] % 10 == 0)
            if override.any():
                factors[override] = cauchy_positive(rng, mf[memory_rows[override]], .05)
            stats["sigma_overrides"] += int(override.sum())
            expected_k = prob[memory_rows] @ np.arange(1, d + 1)
            cr = 10 * expected_k / (10 * expected_k + 1)
            if variant == "binomial":
                mask = rng.random((count, d)) < cr[:, None]
                mask[targets, rng.integers(d, size=count)] = True
            else:
                mask = exponential_mask(rng, count, d, cr)
            ranked = np.argsort(fitness, kind="stable")
            pbest_count = max(2, round_half_up(p * n))
            best = x[ranked[rng.integers(pbest_count, size=count)]]
            r1 = rng.integers(n, size=count)
            while (bad := r1 == targets).any():
                r1[bad] = rng.integers(n, size=int(bad.sum()))
            union = np.concatenate((x, archive))
            r2 = rng.integers(len(union), size=count)
            while (bad := (r2 == targets) | (r2 == r1)).any():
                r2[bad] = rng.integers(len(union), size=int(bad.sum()))
            delta = best - parents + x[r1] - union[r2]
            trial = np.where(mask, parents + factors[:, None] * delta, parents)
            # Algorithm 5 has one random gate outside the loop over individuals.
            gate_draw = rng.random()
            enabled = gate_draw > tau if gate == "pseudocode" else gate_draw < tau
            if variant != "no_learning" and enabled:
                learn = (ct[:count] > stagnation_threshold) & (lf[:count] > 0).all(axis=1)
                if learn.any():
                    delta[learn] = best[learn] - parents[learn] + lv[:count][learn] / lf[:count][learn]
                    trial[learn] = parents[learn] + factors[learn, None] * delta[learn]
                    mask[learn] = True
                    stats["learning_trials"] += int(learn.sum())
        trial = repair(trial, parents, lower, upper)
        tf = evaluate(trial)
        nfev += count
        accepted = tf <= fitness[:count]
        improved = tf < fitness[:count]
        stats["accepted"] += int(accepted.sum())
        stats["strict_improvements"] += int(improved.sum())
        if variant != "de":
            if variant != "no_learning":
                stats["learning_records"] += update_learning(
                    lv[:count], lf[:count], fitness[:count], tf,
                    predecessor_f[:count], delta, mask)
            if accepted.any():
                gains = fitness[:count][accepted] - tf[accepted]
                displacements = (trial - parents)[accepted]
                raw = gains if variant == "fitness_weights" else np.std(displacements, axis=1, ddof=1)
                if raw.sum() == 0:
                    stats["zero_weight_fallbacks"] += 1
                weights = successful_weights(displacements,
                                             gains if variant == "fitness_weights" else None)
                sf = factors[accepted]
                mf[memory_index] = np.sum(weights * sf**2) / np.sum(weights * sf)
                prob[memory_index] = update_probability(mask[accepted].sum(axis=1), weights, d, n)
                memory_index = (memory_index + 1) % memory_size
                current_sf_mean = float(sf.mean())
                if variant != "fixed_sigma":
                    center = .5 * (current_sf_mean + previous_sf_mean)
                    sigma = lambda_sigma * float(np.sqrt(np.mean((sf - center)**2)))
                # Random retention, bounded to round(1.6*current NP).
                archive = np.concatenate((archive, parents[accepted]))
                ct[targets[accepted]] = 0
                lv[targets[accepted]] = 0
                lf[targets[accepted]] = 0
                predecessor_f[targets[accepted]] = fitness[:count][accepted]
            else:
                current_sf_mean = 0.0
            previous_sf_mean = current_sf_mean
            sr = float(accepted.sum() / n)
            ct[targets[~accepted]] += 1
        chosen = targets[accepted]
        x[chosen], fitness[chosen] = trial[accepted], tf[accepted]
        if variant != "de":
            new_n = max(min_population_size,
                        round_half_up(n0 + (min_population_size - n0) * nfev / max_fes))
            new_n = min(n, new_n)
            if new_n < n:
                keep = np.argsort(fitness, kind="stable")[:new_n]
                x, fitness = x[keep], fitness[keep]
                predecessor_f, lv, lf, ct = predecessor_f[keep], lv[keep], lf[keep], ct[keep]
            capacity = round_half_up(archive_ratio * new_n)
            if len(archive) > capacity:
                archive = archive[rng.choice(len(archive), capacity, replace=False)]
        stats["generations"] += 1
        stats["min_population_seen"] = min(stats["min_population_seen"], len(x))
        stats["max_archive"] = max(stats["max_archive"], len(archive))
        if nfev >= next_trace or nfev == max_fes:
            history.append([nfev, float(fitness.min())])
            next_trace = nfev + trace_interval
    stats.update(final_population=len(x), final_sigma=float(sigma),
                 final_memory_F=mf.tolist(), gate=gate)
    best_index = int(fitness.argmin())
    return Result(x[best_index].copy(), float(fitness[best_index]), nfev, history, stats)
