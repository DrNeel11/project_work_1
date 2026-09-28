import unittest
from nbv import VIEWS, branches, decision, entropy, evaluate, prior, solve


class PlannerTests(unittest.TestCase):
    def test_bayes_martingale(self):
        b = prior()
        for view in VIEWS:
            outcomes = list(branches(b, view))
            self.assertAlmostEqual(sum(p for p, _ in outcomes), 1)
            for i in range(4):
                self.assertAlmostEqual(sum(p * post[i] for p, post in outcomes), b[i])

    def test_complementarity(self):
        b = prior()
        for view in VIEWS[:2]:
            self.assertAlmostEqual(sum(p * entropy(post) for p, post in branches(b, view)), entropy(b))
        self.assertEqual(solve(b, (0, 1), 1)[1], "stop")
        self.assertLess(solve(b, (0, 1), 2)[0], decision(b)[0])

    def test_exact_evaluation_matches_solver(self):
        for d in (.05, .2, .5):
            for n in (0., .5):
                b = prior(d, n)
                self.assertAlmostEqual(evaluate(b, (0, 1, 2), 2, "pair_aware")[0],
                                       solve(b, (0, 1, 2), 2)[0])

    def test_stop_with_known_state_or_zero_budget(self):
        self.assertEqual(solve(prior(0), (0, 1, 2), 2), (0., "stop"))
        self.assertEqual(solve(prior(), (0, 1, 2), 0)[1], "stop")


if __name__ == "__main__":
    unittest.main()
