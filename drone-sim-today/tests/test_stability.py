from dataclasses import replace
import unittest

from research.stability.model import (Memory, Settings, action_set,
                                     finish_acquisition, run, select_action)


class StabilityTests(unittest.TestCase):
    def calibrated(self, settings=Settings()):
        b = Memory(settings)
        b.observe([(b.bias, 1.)], .015, .04)
        finish_acquisition(b, action_set(b)[-1])
        b.renew()
        return b

    def test_rate_uncertainty_shortens_stable_region_deferral(self):
        b = self.calibrated()
        certain = b.certify(0, False)["days"]
        b.cov[1][1] = .02**2
        self.assertLess(b.certify(0, False)["days"], certain)

    def test_high_confidence_in_damage_does_not_allow_deferral(self):
        b = self.calibrated()
        b.mean[0] = 1.
        b.cov[0][0] = .00001
        b.reset_anchor(0)
        self.assertLess(b.certify(0)["expires"], b.day)

    def test_absence_grows_uncertainty_without_renewing_evidence(self):
        b = self.calibrated()
        expiry, variance = b.lease[0]["expires"], b.cov[0][0]
        for _ in range(5):
            b.advance()
        self.assertGreater(b.cov[0][0], variance)
        self.assertEqual(b.lease[0]["expires"], expiry)
        self.assertEqual(b.last_direct[0], 0)

    def test_shared_reference_preserves_direct_audit_age(self):
        b = self.calibrated()
        for _ in range(8):
            b.advance()
        ages = b.last_direct[:]
        b.sensor_event()
        self.assertTrue(all(not b.valid(i) for i in range(4)))
        b.observe([(b.bias, 1.)], .015, .07)
        finish_acquisition(b, action_set(b)[-1])
        b.renew()
        self.assertEqual(b.last_direct, ages)
        self.assertTrue(b.reference_valid)
        for i, cert in enumerate(b.lease):
            self.assertLessEqual(cert["expires"], ages[i]+b.settings.max_gap)

    def test_accepted_bounds_obey_budgets(self):
        b = self.calibrated()
        for i in range(4):
            certificate = b.certify(i)
            if certificate["expires"] >= b.day:
                self.assertLessEqual(certificate["risk"], b.settings.risk_budget)
                self.assertLessEqual(certificate["calibration"], b.settings.calibration_budget)

    def test_shock_floor_shortens_deferral(self):
        b = self.calibrated()
        normal = b.certify(0, False)["days"]
        b.settings = replace(b.settings, shock_hazard=.03)
        self.assertLess(b.certify(0, False)["days"], normal)

    def test_critical_due_region_cannot_be_starved_by_healthy_renewals(self):
        b = self.calibrated()
        b.mean[6] = .9
        b.reset_anchor(2)
        b.renew()
        action, _ = select_action(b, "renewal", 3., set())
        self.assertEqual(action["region"], 2)

    def test_stable_regions_are_scanned_less_than_growing_region(self):
        result = run()
        counts = result["metrics"]["region_scans"]
        self.assertLess(counts[0], counts[2])
        self.assertLess(counts[3], counts[2])
        self.assertGreater(result["metrics"]["idle_days"], 0)

    def test_daily_budget_and_covariance_are_valid(self):
        result = run(scenario="calibration")
        for frame in result["frames"]:
            self.assertLessEqual(sum(a["cost"] for a in frame["actions"]), 3.+1e-9)
            self.assertTrue(all(r["sigma"] >= 0 and r["rate_sigma"] >= 0 for r in frame["regions"]))
        b = self.calibrated()
        for _ in range(10):
            b.advance()
            b.observe([(0, 1.), (b.bias, 1.)], .025, .23)
        for i in range(b.size):
            self.assertGreaterEqual(b.cov[i][i], -1e-12)
            for j in range(b.size):
                self.assertAlmostEqual(b.cov[i][j], b.cov[j][i])


if __name__ == "__main__":
    unittest.main()
