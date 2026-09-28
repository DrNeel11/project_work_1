import math
import random
import unittest
from research.stability.exact_renewal import Constraint, compile_prefixes, expected_days, gaussian_mass, remote_view_score
from research.stability.model import Memory


class ExactRenewalTests(unittest.TestCase):
    def test_narrow_event_missed_by_three_node_quadrature(self):
        c = Constraint(0, 1, 1, .2, .3, .01)
        exact = expected_days([[c]])
        self.assertAlmostEqual(exact, gaussian_mass(.2, .3))
        self.assertGreater(exact, .038)
        self.assertTrue(all(not .2 <= z <= .3 for z in [-math.sqrt(3), 0, math.sqrt(3)]))
        competitor = expected_days([[Constraint(0, 1, 1, -.01, .01, .01)]])
        self.assertGreater(exact, competitor)
        # Quadrature gives the competitor weight 2/3 at its central node.
        self.assertLess(competitor, 2/3)

    def test_prefixes_and_negative_loading(self):
        a = Constraint(0, 1, 1, -1, 1, .01)
        b = Constraint(0, 1, -1, -.5, 0, .01)
        rows = compile_prefixes([[a], [b]])
        self.assertEqual((rows[1]['lower'], rows[1]['upper']), (0, .5))
        self.assertAlmostEqual(expected_days([[a], [b]]), gaussian_mass(-1, 1)+gaussian_mass(0, .5))

    def test_impossible_and_uninformative(self):
        self.assertEqual(expected_days([[Constraint(0, 1, 0, -.1, .1, .01)]]), 0)
        self.assertEqual(expected_days([[Constraint(0, 0, 0, -1, 1, .01)]]), 1)
        with self.assertRaises(ValueError):
            Constraint(0, .1, 1, -1, 1, .01).interval()

    def test_independent_monte_carlo_conditional_chance_rule(self):
        from statistics import NormalDist
        c = Constraint(.2, 1, .8, -.7, 1.3, .2)
        rng = random.Random(43)
        margin = NormalDist().inv_cdf(.9)*.6
        count = sum(-.7+margin <= .2+.8*rng.gauss(0, 1) <= 1.3-margin for _ in range(100000))
        self.assertAlmostEqual(expected_days([[c]]), count/100000, delta=.005)

    def test_remote_reference_preserves_audit_age(self):
        m = Memory()
        before = m.last_direct[:]
        result = remote_view_score(m, [(m.bias, 1)], .015)
        self.assertGreater(result['expected_days'], 0)
        self.assertEqual(m.last_direct, before)
        m.day = m.settings.max_gap+1
        self.assertEqual(remote_view_score(m, [(m.bias, 1)], .015)['expected_days'], 0)
        self.assertLess(m.certify(0)['expires'], m.day)
