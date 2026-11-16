import bootstrap
import unittest
import numpy as np
from dls_de import (minimize, VARIANTS, exponential_mask, update_probability,
                    successful_weights, update_learning, repair, initial_population_size,
                    cauchy_positive)


class AlgorithmTests(unittest.TestCase):
    def test_budget_bounds_recompute_and_determinism(self):
        for variant in VARIANTS:
            for budget in (12, 13, 217, 1500):
                calls = []
                def objective(x):
                    self.assertTrue(np.all(x >= -5) and np.all(x <= 5))
                    calls.append(x.copy())
                    return float(x @ x)
                a = minimize(objective, [(-5, 5)] * 5, population_size=12,
                             max_fes=budget, seed=4, variant=variant, trace_interval=50)
                b = minimize(lambda x: float(x @ x), [(-5, 5)] * 5,
                             population_size=12, max_fes=budget, seed=4,
                             variant=variant, trace_interval=50)
                self.assertEqual(len(calls), budget)
                self.assertEqual(a.nfev, budget)
                self.assertEqual(a.fun, b.fun)
                np.testing.assert_array_equal(a.x, b.x)
                self.assertAlmostEqual(a.fun, a.x @ a.x)
                self.assertEqual(a.history[-1][0], budget)
                self.assertTrue(np.all(np.diff(np.array(a.history)[:, 0]) > 0))
                self.assertTrue(np.all(np.diff(np.array(a.history)[:, 1]) <= 0))
                self.assertLessEqual(a.diagnostics["final_population"], 12)
                if variant == "no_learning":
                    self.assertEqual(a.diagnostics["learning_trials"], 0)
                if variant == "fixed_sigma":
                    self.assertEqual(a.diagnostics["final_sigma"], .05)
                if variant == "no_two_phase":
                    self.assertEqual(a.diagnostics["phase1_trials"], 0)

    def test_exponential_circular_contiguity_and_endpoints(self):
        rng = np.random.default_rng(8)
        m = exponential_mask(rng, 1000, 10, np.full(1000, .5))
        self.assertTrue(m.any(axis=1).all())
        transitions = (m != np.roll(m, 1, axis=1)).sum(axis=1)
        self.assertTrue(np.isin(transitions, [0, 2]).all())
        self.assertTrue((exponential_mask(rng, 30, 10, np.zeros(30)).sum(axis=1) == 1).all())
        self.assertTrue(exponential_mask(rng, 30, 10, np.ones(30)).all())

    def test_learning_records_unscaled_delta_only_at_crossed_coordinates(self):
        lv, lf = np.zeros((4, 3)), np.zeros((4, 3), dtype=int)
        mask = np.array([[1, 0, 1]] * 4, dtype=bool)
        count = update_learning(lv, lf, np.array([1., 1, 1, 1]),
                                np.array([2., .5, 3, 1]), np.array([3., 3, 3, 3]),
                                np.full((4, 3), 4.), mask)
        self.assertEqual(count, 1)
        np.testing.assert_array_equal(lv[0], [4, 0, 4])
        np.testing.assert_array_equal(lf[0], [1, 0, 1])
        self.assertEqual(lv[1:].sum(), 0)

    def test_equations_10_15_16_and_zero_fallback(self):
        displacement = np.array([[1., 0, 0], [2., 0, 0]])
        np.testing.assert_allclose(successful_weights(displacement), [1 / 3, 2 / 3])
        np.testing.assert_allclose(successful_weights(np.zeros((2, 3))), [.5, .5])
        np.testing.assert_array_equal(update_probability(np.array([1, 1]), np.array([.5, .5]), 3, 10), [0, 0, 0])
        actual = update_probability(np.array([1, 2, 2]), np.array([.2, .3, .5]), 3, 10)
        raw = np.array([(.2 / .6) / 3 + .1, 2 / 3 * (.4 / .6) + .1, .1])
        np.testing.assert_allclose(actual, raw / raw.sum())
        self.assertTrue((actual > 0).all())

    def test_midpoint_repair_and_population_formula(self):
        np.testing.assert_array_equal(repair(np.array([[-9., 9, 0]]), np.array([[1., -1, 2]]), -5, 5), [[-2, 2, 0]])
        self.assertEqual(initial_population_size(10), 182)
        f = cauchy_positive(np.random.default_rng(3), np.full(10000, .5), .2)
        self.assertTrue(((f > 0) & (f <= 1)).all())

    def test_equality_and_invalid_input(self):
        r = minimize(lambda x: 1., [(-1, 1)] * 3, population_size=8, max_fes=500)
        self.assertEqual(r.diagnostics["accepted"], 492)
        self.assertEqual(r.diagnostics["strict_improvements"], 0)
        self.assertEqual(r.diagnostics["learning_trials"], 0)
        for options in ({"max_fes": 1}, {"tau": 2}, {"variant": "bad"}, {"memory_size": 0}):
            with self.assertRaises(ValueError):
                minimize(lambda x: 0., [(-1, 1)] * 3, **options)
        with self.assertRaises(ValueError):
            minimize(lambda x: float("nan"), [(-1, 1)] * 3)

    def test_learning_path_is_exercised_on_multimodal_objective(self):
        def rastrigin(x):
            return float(np.sum(x*x - 10*np.cos(2*np.pi*x) + 10))
        r = minimize(rastrigin, [(-5.12, 5.12)] * 5, population_size=24,
                     max_fes=6000, stagnation_threshold=0, seed=1)
        self.assertGreater(r.diagnostics["learning_records"], 0)
        self.assertGreater(r.diagnostics["learning_trials"], 0)
        self.assertGreater(r.diagnostics["sigma_overrides"], 0)
        self.assertGreater(r.diagnostics["phase1_trials"], 0)
        self.assertGreater(r.diagnostics["phase2_trials"], 0)
        self.assertLess(r.fun, 1e-5)


class CECIntegrationTests(unittest.TestCase):
    def test_statistical_ties_and_holm_adjustment(self):
        from analyze import tolerant_ranks, holm
        np.testing.assert_allclose(tolerant_ranks([0., 1e-10, 100., 100. + 1e-10, 200.]), [1.5, 1.5, 3.5, 3.5, 5.])
        np.testing.assert_allclose(holm([.01, .04, .03]), [.03, .06, .06])

    def test_all_30_functions_small_budget(self):
        from opfunu.cec_based import cec2014
        for fid in range(1, 31):
            f = getattr(cec2014, f"F{fid}2014")(ndim=10)
            r = minimize(f.evaluate, np.column_stack((f.lb, f.ub)),
                         population_size=8, max_fes=29, seed=fid)
            self.assertEqual(f.n_fe, 29)
            self.assertTrue(np.isfinite(r.fun))
            self.assertAlmostEqual(r.fun, f.evaluate(r.x))


if __name__ == "__main__":
    unittest.main(verbosity=2)
