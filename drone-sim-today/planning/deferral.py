"""Opt-in, evidence-backed suppression of views of stable regions.

This adapter does not infer stability from absent detector boxes. A calibrated
region observer must issue certificates; unknown, expired and revoked cells
always remain eligible. JSON persistence is independent of defect databases.
"""
from copy import copy
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class StabilityCertificate:
    wall: str
    cell: int
    issued_at: float
    revisit_at: float
    last_direct_at: float
    max_audit_gap: float
    risk_bound: float
    risk_budget: float
    evidence_ids: tuple
    dependencies: tuple  # pairs of (dependency name, observed version)
    model_id: str

    def __post_init__(self):
        numeric = (self.issued_at, self.revisit_at, self.last_direct_at,
                   self.max_audit_gap, self.risk_bound, self.risk_budget)
        if not all(math.isfinite(x) for x in numeric):
            raise ValueError("Certificate values must be finite")
        if not self.last_direct_at <= self.issued_at < self.revisit_at:
            raise ValueError("Certificate must have a past direct observation and a future deadline")
        if self.max_audit_gap <= 0 or self.revisit_at > self.last_direct_at+self.max_audit_gap:
            raise ValueError("Deferral exceeds its physical audit limit")
        if not 0 <= self.risk_bound <= self.risk_budget < 1:
            raise ValueError("Certificate exceeds its risk budget")
        if not self.evidence_ids or not self.model_id or not self.wall or self.cell < 0:
            raise ValueError("Region, evidence and model provenance are required")
        if len({name for name, _ in self.dependencies}) != len(self.dependencies):
            raise ValueError("Duplicate dependency names")


class DeferralLedger:
    def __init__(self, scope):
        if not scope:
            raise ValueError("A deployment/experiment scope is required")
        self.scope = scope
        self.certificates = {}
        self.versions = {}

    def put(self, certificate):
        key = certificate.wall, certificate.cell
        old = self.certificates.get(key)
        if old and certificate.issued_at < old.issued_at:
            raise ValueError("Cannot replace evidence with an older certificate")
        if old and certificate.revisit_at > old.revisit_at and set(certificate.evidence_ids) <= set(old.evidence_ids):
            raise ValueError("Extending a deferral requires new evidence provenance")
        for name, version in certificate.dependencies:
            if version != self.versions.get(name, 0):
                raise ValueError("Certificate depends on a revoked or unknown evidence version")
        self.certificates[key] = certificate

    def can_defer(self, wall, cell, now):
        if not math.isfinite(now):
            raise ValueError("Inspection time must be finite")
        certificate = self.certificates.get((wall, cell))
        return bool(certificate and certificate.issued_at <= now < certificate.revisit_at and
                    all(self.versions.get(name, 0) == version for name, version in certificate.dependencies))

    def revoke(self, dependency):
        self.versions[dependency] = self.versions.get(dependency, 0)+1

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(schema=1, scope=self.scope, versions=self.versions,
                       certificates=[asdict(c) for c in self.certificates.values()])
        temporary = path.with_suffix(path.suffix+".tmp")
        temporary.write_text(json.dumps(payload, indent=2, allow_nan=False)+"\n", encoding="utf-8")
        temporary.replace(path)

    @classmethod
    def load(cls, path, expected_scope):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema") != 1 or data.get("scope") != expected_scope:
            raise ValueError("Deferral memory schema/scope does not match this run")
        result = cls(expected_scope)
        result.versions = data["versions"]
        for item in data["certificates"]:
            item["evidence_ids"] = tuple(item["evidence_ids"])
            item["dependencies"] = tuple(tuple(pair) for pair in item["dependencies"])
            certificate = StabilityCertificate(**item)
            # Retain revoked records for audit; can_defer checks their versions.
            result.certificates[certificate.wall, certificate.cell] = certificate
        return result


class DeferralPlanner:
    """Wrap an existing planner without modifying its candidate list or utility."""
    def __init__(self, planner, ledger, inspection_time):
        if not math.isfinite(inspection_time):
            raise ValueError("Inspection time must be finite")
        self.planner, self.ledger, self.inspection_time = planner, ledger, inspection_time

    def select_next(self, belief, current_id):
        eligible = [v for v in self.planner.viewpoints if any(
            not self.ledger.can_defer(v.wall, cell, self.inspection_time)
            for cell in v.visible_cells)]
        if not eligible:
            return None  # complete deferral; mission runner must stop acquisition
        delegate = copy(self.planner)
        delegate.viewpoints = eligible
        return delegate.select_next(belief, current_id)


def accept_region_evidence(ledger, viewpoint, now, certificates):
    """A regional observer may certify only cells actually in its view."""
    certificates = tuple(certificates)
    for item in certificates:
        if item.wall != viewpoint.wall or item.cell not in viewpoint.visible_cells:
            raise ValueError("Regional observer returned evidence outside the acquired view")
        if item.issued_at != now or item.last_direct_at != now:
            raise ValueError("Regional evidence must carry this acquisition's timestamp")
    for item in certificates:
        ledger.put(item)
