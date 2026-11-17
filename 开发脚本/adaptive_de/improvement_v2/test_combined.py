"""Checks for preserved backbone and charged rescue calls. Author: 殷明骏."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import dls_de
import dls_combined


class Checks(unittest.TestCase):
    def test_plain_matches_frozen_backbone(self):
        kw=dict(population_size=20,min_population_size=20,max_fes=2023,seed=8)
        obj=lambda x: float(x@x)
        a=dls_de.minimize(obj,[(-4,3)]*5,**kw)
        b=dls_combined.minimize(obj,[(-4,3)]*5,revision='plain',**kw)
        self.assertTrue(np.array_equal(a.x,b.x))
        self.assertEqual((a.fun,a.nfev,a.history),(b.fun,b.nfev,b.history))

    def test_every_call_charged_and_history_monotone(self):
        for revision in ['cls','dual']:
            calls=[]
            def obj(x):
                self.assertTrue(np.all(x>=-4) and np.all(x<=3))
                calls.append(1);return float(x@x)
            r=dls_combined.minimize(obj,[(-4,3)]*5,population_size=20,min_population_size=20,
                                   max_fes=2023,seed=9,revision=revision)
            self.assertEqual(len(calls),2023);self.assertEqual(r.nfev,2023)
            self.assertEqual(r.history[-1][0],2023)
            self.assertTrue(np.all(np.diff(np.asarray(r.history)[:,1])<=0))
            self.assertAlmostEqual(r.fun,float(r.x@r.x))

    def test_rescue_uses_remaining_budget(self):
        calls=[]
        def objective(x):calls.append(1);return 1.
        r=dls_combined.minimize(objective,[(-4,3)]*5,population_size=20,min_population_size=20,
                               max_fes=603,seed=4,revision='cls')
        self.assertGreater(r.diagnostics['rescue_evaluations'],0)
        self.assertEqual(len(calls),603)
        self.assertEqual(r.nfev,603)


if __name__=='__main__':unittest.main()
