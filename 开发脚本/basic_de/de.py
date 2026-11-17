"""Basic, generational DE/rand/1/bin. No adaptive or elite strategies."""
from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass
class DEResult:
    x: np.ndarray
    fun: float
    nfev: int
    history: list[tuple[int, float]]


def donor_indices(rng: np.random.Generator, size: int, targets: np.ndarray) -> np.ndarray:
    """Uniform ordered triples, mutually distinct and excluding each target."""
    donors = rng.integers(size, size=(len(targets), 3))
    while True:
        invalid = ((donors == targets[:, None]).any(axis=1)
                   | (donors[:, 0] == donors[:, 1])
                   | (donors[:, 0] == donors[:, 2])
                   | (donors[:, 1] == donors[:, 2]))
        if not invalid.any():
            return donors
        donors[invalid] = rng.integers(size, size=(int(invalid.sum()), 3))


def minimize(objective: Callable, bounds, *, population_size: int = 100,
             max_fes: int = 100_000, f: float = 0.5, cr: float = 0.9,
             seed: int = 0, trace_interval: int = 1000) -> DEResult:
    """Minimize an objective with exactly max_fes calls, including initialization.

    All donors come from the preceding generation. Out-of-bounds coordinates
    are clipped to the box. A final incomplete generation evaluates only the
    remaining targets. Ties retain the parent, matching strict greedy selection.
    """
    box = np.asarray(bounds, dtype=float)
    if box.ndim != 2 or box.shape[1] != 2 or not len(box):
        raise ValueError("bounds must have shape (dimension, 2)")
    if not np.isfinite(box).all() or not (box[:, 0] < box[:, 1]).all():
        raise ValueError("bounds must be finite with lower < upper")
    if not isinstance(population_size, int) or population_size < 4:
        raise ValueError("population_size must be an integer >= 4")
    if not isinstance(max_fes, int) or max_fes < population_size:
        raise ValueError("max_fes must be an integer >= population_size")
    if not 0 < f <= 2 or not 0 <= cr <= 1:
        raise ValueError("require 0 < F <= 2 and 0 <= CR <= 1")
    if trace_interval < 1:
        raise ValueError("trace_interval must be positive")
    rng = np.random.default_rng(seed)
    lower, upper = box.T
    dimension = len(box)
    population = rng.uniform(lower, upper, (population_size, dimension))

    def evaluate(points):
        values = np.array([objective(x) for x in points], dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("objective returned a non-finite value")
        return values

    fitness = evaluate(population)
    nfev = population_size
    history = [(nfev, float(fitness.min()))]
    next_trace = nfev + trace_interval
    while nfev < max_fes:
        count = min(population_size, max_fes - nfev)
        targets = np.arange(count)
        donors = donor_indices(rng, population_size, targets)
        mutant = (population[donors[:, 0]]
                  + f * (population[donors[:, 1]] - population[donors[:, 2]]))
        mutant = np.clip(mutant, lower, upper)
        mask = rng.random((count, dimension)) < cr
        mask[np.arange(count), rng.integers(dimension, size=count)] = True
        trial = np.where(mask, mutant, population[:count])
        trial_fitness = evaluate(trial)
        accepted = np.flatnonzero(trial_fitness < fitness[:count])
        population[accepted] = trial[accepted]
        fitness[accepted] = trial_fitness[accepted]
        nfev += count
        if nfev >= next_trace or nfev == max_fes:
            history.append((nfev, float(fitness.min())))
            next_trace = nfev + trace_interval
    best = int(fitness.argmin())
    return DEResult(population[best].copy(), float(fitness[best]), nfev, history)
