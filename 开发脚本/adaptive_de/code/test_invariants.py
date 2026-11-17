"""Budget, initialization, intervention and replay checks; 殷明骏."""
import unittest
import numpy as np
from run_adaptive_de import ALL, make_problem, optimize
import pems_de


class Invariants(unittest.TestCase):
    def test_actual_calls_saved_solution_and_history(self):
        for algorithm in ALL:
            for budget in (20, 43, 203):
                with self.subTest(algorithm=algorithm, budget=budget):
                    problem = make_problem('cec2014', 9, 10)
                    config = dict(max_fes=budget, population_size=20, population_mode='fixed')
                    r = optimize(problem, algorithm, config, 517)
                    self.assertEqual(problem.n_fe, budget)
                    self.assertEqual(r['nfev'], budget)
                    self.assertAlmostEqual(problem.evaluate(np.array(r['x'])), r['fun'], places=9)
                    h = np.array(r['history'])
                    self.assertEqual(h[-1, 0], budget)
                    self.assertEqual(h[-1, 1], r['fun'])
                    self.assertTrue(np.all(np.diff(h[:, 0]) > 0))
                    self.assertTrue(np.all(np.diff(h[:, 1]) <= 1e-9))
                    self.assertTrue(np.all(np.abs(r['x']) <= 100))

    def test_same_initial_population_and_exact_replay(self):
        initials = []
        for algorithm in ALL:
            config = dict(max_fes=20, population_size=20, population_mode='fixed')
            r = optimize(make_problem('cec2014', 9, 10), algorithm, config, 221)
            initials.append((r['x'], r['fun']))
            config['max_fes'] = 253
            first = optimize(make_problem('cec2014', 9, 10), algorithm, config, 221)
            again = optimize(make_problem('cec2014', 9, 10), algorithm, config, 221)
            self.assertEqual(first, again, algorithm)
        self.assertTrue(all(item == initials[0] for item in initials))

    def test_pems_cls_and_immediate_memory(self):
        calls = []
        def increasing_cost(x):
            calls.append(x.copy())
            return float(len(calls))
        r = pems_de.minimize(increasing_cost, [(-100, 100)]*10, max_fes=497, population_size=20, seed=3)
        self.assertEqual(len(calls), 497)
        self.assertGreater(r['diagnostics']['cls_evaluations'], 0)
        self.assertEqual(sum(r['diagnostics'][k] for k in
                         ('initialization_evaluations', 'mutation_evaluations', 'cls_evaluations')), 497)
        def sphere(x):
            return float(x @ x)
        r = pems_de.minimize(sphere, [(-100, 100)]*10, max_fes=300, population_size=20, seed=3)
        self.assertGreater(r['diagnostics']['narrow_f_samples'], 0)
        self.assertGreater(r['diagnostics']['broad_f_samples'], 0)


if __name__ == '__main__':
    unittest.main()
