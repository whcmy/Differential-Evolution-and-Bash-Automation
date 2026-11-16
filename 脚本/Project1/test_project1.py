"""Algorithm invariants, exact budget accounting and CEC integration checks."""
import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/project1-matplotlib")
import unittest
import numpy as np
from opfunu.cec_based import cec2014
from de import donor_indices, minimize
from summarize import statistics_row


class TestDE(unittest.TestCase):
    def test_donors(self):
        rng = np.random.default_rng(12)
        for size in (4, 5, 100):
            targets = np.arange(size)
            for _ in range(20):
                donors = donor_indices(rng, size, targets)
                self.assertTrue(np.all(donors != targets[:, None]))
                self.assertTrue(np.all(np.diff(np.sort(donors, axis=1), axis=1) > 0))

    def test_budget_bounds_monotonic_and_reproducibility(self):
        for budget in (20, 21, 53, 4000):
            seen = []
            def sphere(x):
                seen.append(x.copy())
                self.assertTrue(np.all((-2 <= x) & (x <= 3)))
                return float(x @ x)
            a = minimize(sphere, [(-2, 3)] * 4, population_size=20,
                         max_fes=budget, seed=2, trace_interval=20)
            self.assertEqual(len(seen), budget)
            self.assertEqual(a.nfev, budget)
            self.assertTrue(np.all(np.diff([v for _, v in a.history]) <= 0))
            self.assertEqual(a.history[-1][0], budget)
            b = minimize(lambda x: float(x @ x), [(-2, 3)] * 4,
                         population_size=20, max_fes=budget, seed=2, trace_interval=20)
            np.testing.assert_array_equal(a.x, b.x)
            self.assertEqual(a.fun, b.fun)
            if budget == 4000:
                self.assertLess(a.fun, 1e-8)

    def test_cr_zero_still_takes_one_mutant_coordinate(self):
        seen = []
        minimize(lambda x: seen.append(x.copy()) or float(x @ x),
                 [(-100, 100)] * 8, population_size=20, max_fes=40, cr=0, seed=3)
        differences = np.count_nonzero(np.array(seen[20:]) != np.array(seen[:20]), axis=1)
        np.testing.assert_array_equal(differences, np.ones(20))

    def test_cec_optima_and_budget(self):
        for i in range(1, 31):
            problem = getattr(cec2014, f"F{i}2014")(ndim=10)
            self.assertAlmostEqual(problem.evaluate(problem.x_global), problem.f_global, places=7)
            problem.n_fe = 0
            result = minimize(problem.evaluate, np.column_stack([problem.lb, problem.ub]),
                              population_size=10, max_fes=23, seed=i)
            self.assertEqual(problem.n_fe, 23)
            self.assertEqual(result.nfev, 23)

    def test_invalid_configuration(self):
        for kwargs in (dict(population_size=3), dict(max_fes=99), dict(f=0), dict(cr=1.1)):
            with self.assertRaises(ValueError):
                minimize(lambda x: 0, [(-1, 1)], **kwargs)

    def test_sample_statistics(self):
        row = statistics_row([1.0, 2.0, 3.0, 4.0])
        self.assertEqual(row['median'], 2.5)
        self.assertEqual(row['mean'], 2.5)
        self.assertAlmostEqual(row['variance'], 5 / 3)
        self.assertAlmostEqual(row['std'], np.sqrt(5 / 3))
        self.assertEqual(statistics_row([7.0, 7.0])['variance'], 0.0)
        self.assertIsNone(statistics_row([7.0])['variance'])


if __name__ == "__main__":
    unittest.main()
