import tempfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import unittest

from planning.deferral import (DeferralLedger, DeferralPlanner,
                               StabilityCertificate, accept_region_evidence)


def certificate(cell=0):
    return StabilityCertificate("wall", cell, 1., 8., 1., 10., .01, .05,
                                ("validated-frame-1",), (("calibration", 0),), "test-model-v1")


class FirstViewPlanner:
    def __init__(self, views):
        self.viewpoints = views

    def select_next(self, belief, current_id):
        return self.viewpoints[0]


class DeferralTests(unittest.TestCase):
    def test_unknown_expired_and_revoked_are_due(self):
        ledger = DeferralLedger("run")
        self.assertFalse(ledger.can_defer("wall", 0, 2))
        ledger.put(certificate())
        self.assertFalse(ledger.can_defer("wall", 0, 0))
        self.assertTrue(ledger.can_defer("wall", 0, 2))
        self.assertFalse(ledger.can_defer("wall", 0, 8))
        ledger.revoke("calibration")
        self.assertFalse(ledger.can_defer("wall", 0, 2))

    def test_scope_persistence_and_revoked_audit(self):
        ledger = DeferralLedger("deployment-A")
        ledger.put(certificate())
        ledger.revoke("calibration")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"memory.json"
            ledger.save(path)
            loaded = DeferralLedger.load(path, "deployment-A")
            self.assertEqual(len(loaded.certificates), 1)
            self.assertFalse(loaded.can_defer("wall", 0, 3))
            with self.assertRaises(ValueError):
                DeferralLedger.load(path, "deployment-B")

    def test_invalid_risk_and_audit_certificates_rejected(self):
        for change in (dict(risk_bound=.1), dict(revisit_at=20), dict(evidence_ids=()),
                       dict(issued_at=10), dict(risk_bound=float("nan"))):
            with self.assertRaises(ValueError):
                replace(certificate(), **change)

    def test_stale_dependency_cannot_be_reissued(self):
        ledger = DeferralLedger("run")
        ledger.revoke("calibration")
        with self.assertRaises(ValueError):
            ledger.put(certificate())

    def test_time_alone_cannot_extend_deferral(self):
        ledger = DeferralLedger("run")
        ledger.put(certificate())
        with self.assertRaises(ValueError):
            ledger.put(replace(certificate(), issued_at=2., revisit_at=9.))

    def test_adapter_stops_only_when_every_visible_cell_is_deferred(self):
        views = [SimpleNamespace(wall="wall", visible_cells=[0]),
                 SimpleNamespace(wall="wall", visible_cells=[0, 1])]
        baseline = FirstViewPlanner(views)
        ledger = DeferralLedger("run")
        ledger.put(certificate())
        adapter = DeferralPlanner(baseline, ledger, 2)
        self.assertIs(adapter.select_next(None, None), views[1])
        self.assertEqual(baseline.viewpoints, views)
        ledger.put(certificate(1))
        self.assertIsNone(adapter.select_next(None, None))
        self.assertIs(DeferralPlanner(baseline, ledger, 8).select_next(None, None), views[0])

    def test_detector_silence_does_not_create_evidence(self):
        ledger = DeferralLedger("run")
        view = SimpleNamespace(wall="wall", visible_cells=[0])
        accept_region_evidence(ledger, view, 1., ())
        self.assertFalse(ledger.can_defer("wall", 0, 2))
        with self.assertRaises(ValueError):
            accept_region_evidence(ledger, view, 1., (certificate(1),))
        with self.assertRaises(ValueError):
            accept_region_evidence(ledger, view, 2., (certificate(),))


if __name__ == "__main__":
    unittest.main()
