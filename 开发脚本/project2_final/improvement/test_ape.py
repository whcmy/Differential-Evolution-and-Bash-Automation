"""Budget, state and objective-contract checks. Author: 殷明骏."""
import unittest
import numpy as np
import ape_de


class Checks(unittest.TestCase):
    def test_budget_partial_generation_bounds_and_replay(self):
        for variant in ape_de.VARIANTS:
            observed = []
            def objective(x):
                self.assertTrue(np.all(x >= -3) and np.all(x <= 2))
                observed.append(x.copy())
                return float(x@x)
            kwargs = dict(max_fes=813, population_size=20, seed=6, variant=variant, trace_interval=41)
            r = ape_de.minimize(objective, [(-3,2)]*4, **kwargs)
            self.assertEqual(len(observed), 813)
            self.assertEqual(r['nfev'], 813)
            self.assertEqual(r['history'][-1][0], 813)
            self.assertTrue(np.all(np.diff(np.array(r['history'])[:,1]) <= 0))
            self.assertAlmostEqual(np.dot(r['x'],r['x']),r['fun'])
            other = ape_de.minimize(lambda x: float(x@x), [(-3,2)]*4, **kwargs)
            self.assertEqual(r, other)
            self.assertLessEqual(r['diagnostics']['max_archive'], 32)

    def test_constant_objective_does_not_corrupt_memory(self):
        for variant in ape_de.VARIANTS:
            r = ape_de.minimize(lambda x: 4., [(-1,1)]*3, max_fes=109, population_size=10, variant=variant)
            self.assertEqual(r['fun'],4.)
            self.assertEqual(r['diagnostics']['accepted'],0)
            self.assertTrue(np.isfinite(r['diagnostics']['final_f_memory']).all())

    def test_nonfinite_objective_rejected(self):
        with self.assertRaises(ValueError):
            ape_de.minimize(lambda x: float('nan'), [(-1,1)]*3)


if __name__ == '__main__': unittest.main()
