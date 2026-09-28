import math
import unittest
from dataclasses import replace

from demo_model import (Lab, SCENARIOS, STAGES, STATES, decision, factorize,
                        initial, likelihood, make_views, summarize, transition)


class BeliefTests(unittest.TestCase):
    def test_likelihood_and_transition_mass(self):
        for view in make_views():
            for state in STATES:
                probabilities = likelihood(view, state)
                self.assertAlmostEqual(sum(probabilities), 1)
                self.assertTrue(all(0 <= p <= 1 for p in probabilities))
        b = initial()
        self.assertEqual(transition(b, 0), b)
        for elapsed in (1, 6):
            moved = transition(b, elapsed)
            self.assertAlmostEqual(sum(moved), 1)
            self.assertGreater(summarize(moved)["damage"], summarize(b)["damage"])
        damaged = tuple(.25 if d else 0 for d, _, _ in STATES)
        self.assertAlmostEqual(summarize(transition(damaged, 4))["damage"], 1)

    def test_joint_memory_counterexample(self):
        positive = tuple(.25 if d == n else 0 for d, _, n in STATES)
        negative = tuple(.25 if d != n else 0 for d, _, n in STATES)
        self.assertEqual(factorize(positive), factorize(negative))
        lab = Lab(SCENARIOS[0], STAGES[5])
        self.assertEqual(decision(lab.update(positive, 1, 2))[1], "repair")
        self.assertEqual(decision(lab.update(negative, 1, 2))[1], "defer")

    def test_no_history_memory_control(self):
        scenario = SCENARIOS[0]
        beliefs = [Lab(scenario, stage).memory() for stage in STAGES[2:]]
        for b in beliefs:
            for actual, expected in zip(b, beliefs[0]):
                self.assertAlmostEqual(actual, expected)

    def test_zero_gap_temporal_control(self):
        a = Lab(SCENARIOS[1], STAGES[3]).memory()
        b = Lab(SCENARIOS[1], STAGES[4]).memory()
        self.assertEqual(a, b)

    def test_bayes_martingale(self):
        lab = Lab(SCENARIOS[0], STAGES[5])
        b = initial()
        for i in range(12):
            outcomes = list(lab.outcomes(b, i))
            self.assertAlmostEqual(sum(p for _, p, _ in outcomes), 1)
            for s in range(8):
                self.assertAlmostEqual(sum(p*post[s] for _, p, post in outcomes), b[s])


class PolicyTests(unittest.TestCase):
    def test_restricted_policy_bounds_and_endpoints(self):
        for scenario in SCENARIOS:
            def plan(stage, k=4):
                lab = Lab(scenario, stage, top_k=k)
                return lab.plan(lab.memory(), tuple(range(12)), -1, scenario["energy"], 2)
            exact, myopic = plan(STAGES[6]), plan(STAGES[5])
            sparse = plan(STAGES[7])
            self.assertLessEqual(exact["value"], sparse["value"]+1e-9)
            self.assertLessEqual(sparse["value"], myopic["value"]+1e-9)
            self.assertLessEqual(sparse["certificate"]["lower_bound"], exact["value"]+1e-9)
            self.assertLessEqual(sparse["value"]-exact["value"], sparse["certificate"]["max_regret"]+1e-9)
            self.assertAlmostEqual(plan(STAGES[7], 0)["value"], myopic["value"])
            self.assertAlmostEqual(plan(STAGES[7], 66)["value"], exact["value"])
            self.assertAlmostEqual(plan(STAGES[7], 66)["certificate"]["max_regret"], 0.)

    def test_exact_predicted_matches_true_evaluation(self):
        for scenario in SCENARIOS[:-1]:
            lab = Lab(scenario, STAGES[6])
            b = lab.memory()
            planned = lab.plan(b, tuple(range(12)), -1, scenario["energy"], 2)
            measured = lab.evaluate(b, lab.memory(True), tuple(range(12)), -1, scenario["energy"], 2)
            self.assertAlmostEqual(planned["value"], measured["cost"])
            self.assertLess(measured["calibration"], 1e-20)

    def test_all_replay_paths_reserve_return_energy(self):
        scenario = SCENARIOS[4]
        for stage in STAGES:
            lab = Lab(scenario, stage)
            replay = lab.replay(lab.memory(), lab.memory(True), 7)
            for frame in replay["frames"]:
                self.assertGreaterEqual(frame["energy"]+1e-9, lab.travel(frame["position"], -1))
                if frame["next"] >= 0:
                    self.assertIn(frame["next"], frame["feasible"])
                    self.assertNotIn(frame["next"], scenario["blocked"])

    def test_evaluate_uses_true_belief_for_terminal_loss(self):
        lab = Lab(SCENARIOS[0], STAGES[2])
        optimistic = initial(0, 0)
        damaged = initial(1)
        loss = lab.evaluate(optimistic, damaged, (), -1, 13., 0)
        self.assertEqual(loss["cost"], 100.)
        self.assertEqual(loss["missed"], 1.)

    def test_replay_shared_world(self):
        states = []
        for stage in STAGES:
            lab = Lab(SCENARIOS[1], stage)
            states.append(lab.replay(lab.memory(), lab.memory(True), 7)["state"])
        self.assertTrue(all(s == states[0] for s in states))


if __name__ == "__main__":
    unittest.main()
