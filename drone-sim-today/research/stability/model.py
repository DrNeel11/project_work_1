"""Multi-mission NBV with expiring, dependency-aware stability evidence.

Synthetic linear-Gaussian research model, not a flight controller or field guarantee.
All planner decisions use observations and propagated beliefs, never simulator truth.
"""
from dataclasses import dataclass
from math import erfc, sqrt, log
import copy
import random

REGIONS = (
    dict(name="Stable panel", mean=.18, rate=.0008, sigma=.012, rate_sigma=.0007, color="#a4d77d"),
    dict(name="Uncertain seam", mean=.24, rate=.0012, sigma=.06, rate_sigma=.009, color="#86bedc"),
    dict(name="Growing crack", mean=.43, rate=.012, sigma=.025, rate_sigma=.002, color="#e7ad79"),
    dict(name="Stable bracket", mean=.28, rate=.0004, sigma=.018, rate_sigma=.001, color="#c1a1dd"),
)
POLICIES = (
    dict(id="periodic", name="8 · Fixed revisits", added="A repeated-mission baseline", description="Inspect every region every four days; same views and inference model as the adaptive policies."),
    dict(id="snapshot", name="9 · Confidence only", added="Skip apparently known regions", description="An intentionally incomplete control: defer when the last estimate is confident and healthy, without aging the belief or enforcing a maximum audit gap."),
    dict(id="predictive", name="10 · Predictive revisits", added="Condition + rate + uncertainty", description="Issue finite deferrals from predicted change and damage risk. Physical-process uncertainty grows while the drone is absent."),
    dict(id="revocable", name="11 · Revocable + information NBV", added="Dependencies and a shared-reference action", description="A region's deferral also depends on calibration. Announced sensor changes revoke evidence; choose from the same view actions as the final stage using current marginal information gain."),
    dict(id="renewal", name="12 · Renewal-value NBV", added="Choose views by future scan burden", description="Choose among regional, complementary and shared-reference views by expected deferral-days recovered per acquisition cost. One shared check can renew multiple regions without pretending they were physically rescanned."),
)
SCENARIOS = (
    dict(id="steady", name="Mixed stability", description="Two well-estimated stable regions, one uncertain seam, and one growing crack."),
    dict(id="calibration", name="Shared evidence is revoked", description="Day 18: a publicly reported sensor-calibration event invalidates shared evidence. Its bias magnitude is unknown to the planner."),
    dict(id="local_change", name="Unannounced local change", description="Day 24: an unannounced local jump affects the stable panel. No oracle alarm is supplied: the next actual observation must discover it."),
)


@dataclass(frozen=True)
class Settings:
    days: int = 48
    max_gap: int = 16
    change_limit: float = .10
    damage_limit: float = .85
    risk_budget: float = .05
    calibration_budget: float = .05
    bias_tolerance: float = .15
    shock_hazard: float = .001
    health_noise: float = .002
    rate_noise: float = .00012
    bias_noise: float = .008
    day_budget: float = 3.
    acquisition_penalty: float = 1.


def upper_tail(mean, variance, threshold):
    if variance <= 1e-16:
        return float(mean > threshold)
    return .5*erfc((threshold-mean)/sqrt(2*variance))


def two_sided(mean, variance, threshold):
    return min(1., upper_tail(mean, variance, threshold)+upper_tail(-mean, variance, threshold))


class Memory:
    """Joint Gaussian state: [health, rate, last-direct anchor] per region + bias."""
    def __init__(self, settings=Settings()):
        self.settings = settings
        self.size = 3*len(REGIONS)+1
        self.bias = self.size-1
        self.mean = [0.]*self.size
        self.cov = [[0.]*self.size for _ in range(self.size)]
        bias_variance = .10**2
        self.cov[self.bias][self.bias] = bias_variance
        for i, region in enumerate(REGIONS):
            h, r, _ = self.indices(i)
            self.mean[h] = region["mean"]+.04
            self.mean[r] = region["rate"]
            self.cov[h][h] = region["sigma"]**2+bias_variance
            self.cov[r][r] = region["rate_sigma"]**2
            self.cov[h][self.bias] = self.cov[self.bias][h] = -bias_variance
            for j in range(i):
                self.cov[h][3*j] = self.cov[3*j][h] = bias_variance
        self.day = 0
        self.last_direct = [0]*len(REGIONS)
        self.reference_day = 0
        self.reference_center = 0.
        self.reference_valid = True
        self.version = 0
        self.lease = [None]*len(REGIONS)
        for i in range(len(REGIONS)):
            self.reset_anchor(i)

    @staticmethod
    def indices(i):
        return 3*i, 3*i+1, 3*i+2

    def clone(self):
        result = copy.copy(self)
        result.mean = self.mean[:]
        result.cov = [row[:] for row in self.cov]
        result.last_direct = self.last_direct[:]
        result.lease = self.lease[:]
        return result

    def reset_anchor(self, i):
        h, _, a = self.indices(i)
        self.mean[a] = self.mean[h]
        self.cov[a] = self.cov[h][:]
        for j in range(self.size):
            self.cov[j][a] = self.cov[j][h]
        self.cov[a][a] = self.cov[h][h]
        self.last_direct[i] = self.day

    def advance(self, freeze=False):
        self.day += 1
        if freeze:
            return
        # Sparse F P F^T for health(t+1)=health(t)+rate(t).
        old = self.cov
        left = [row[:] for row in old]
        for i in range(len(REGIONS)):
            h, r, _ = self.indices(i)
            self.mean[h] += self.mean[r]
            left[h] = [old[h][j]+old[r][j] for j in range(self.size)]
        new = [row[:] for row in left]
        for i in range(len(REGIONS)):
            h, r, _ = self.indices(i)
            for j in range(self.size):
                new[j][h] = left[j][h]+left[j][r]
            new[h][h] += self.settings.health_noise**2
            new[r][r] += self.settings.rate_noise**2
        new[self.bias][self.bias] += self.settings.bias_noise**2
        self.cov = new

    def observe(self, weights, noise, value):
        ph = [sum(self.cov[i][j]*w for j, w in weights) for i in range(self.size)]
        predicted = sum(self.mean[j]*w for j, w in weights)
        variance = noise**2+sum(ph[j]*w for j, w in weights)
        residual = value-predicted
        for i in range(self.size):
            self.mean[i] += ph[i]*residual/variance
        self.cov = [[self.cov[i][j]-ph[i]*ph[j]/variance for j in range(self.size)]
                    for i in range(self.size)]
        return residual/sqrt(variance)

    def sensor_event(self, revoke=True):
        # Known event, unknown jump: no true bias or region condition is read here.
        self.cov[self.bias][self.bias] += .20**2
        if revoke:
            self.reference_valid = False
            self.version += 1

    def certify(self, i, dependencies=True):
        s = self.settings
        h, r, a = self.indices(i)
        age = self.day-self.last_direct[i]
        limit = max(0, s.max_gap-age)
        if dependencies and not self.reference_valid:
            return dict(expires=self.day-1, days=0, reason="reference revoked", risk=1., calibration=1., version=self.version)
        sum_local = sum_calibration = 0.
        best, risk, calibration, reason = -1, 0., 0., "audit limit"
        accepted_risk = accepted_calibration = None
        for k in range(limit+1):
            process = k*s.health_noise**2+(k-1)*k*(2*k-1)/6*s.rate_noise**2
            health_mean = self.mean[h]+k*self.mean[r]
            health_var = self.cov[h][h]+2*k*self.cov[h][r]+k*k*self.cov[r][r]+process
            change_mean = health_mean-self.mean[a]
            change_var = health_var+self.cov[a][a]-2*(self.cov[h][a]+k*self.cov[r][a])
            sum_local += upper_tail(health_mean, health_var, s.damage_limit)+two_sided(change_mean, change_var, s.change_limit)
            # A union bound handles arbitrary unmodeled jumps; absence is not evidence.
            risk = min(1., sum_local+1-(1-s.shock_hazard)**(age+k))
            sum_calibration += two_sided(self.mean[self.bias]-self.reference_center,
                                         self.cov[self.bias][self.bias]+k*s.bias_noise**2,
                                         s.bias_tolerance)
            calibration = min(1., sum_calibration)
            if risk > s.risk_budget:
                reason = "change / condition uncertainty"
                break
            if dependencies and calibration > s.calibration_budget:
                reason = "shared calibration uncertainty"
                break
            best = k
            accepted_risk, accepted_calibration = risk, calibration
        return dict(expires=self.day+best, days=max(0, best), reason=reason,
                    risk=accepted_risk, calibration=accepted_calibration if dependencies else 0.,
                    next_risk=risk, next_calibration=calibration if dependencies else 0., version=self.version)

    def renew(self, dependencies=True):
        # Issuance only follows actual observations/maintenance, never a clock tick.
        self.lease = [dict(self.certify(i, dependencies), issued=self.day,
                           dependencies=[f"region:{i}:last-direct", "growth-model"]+
                           ([f"reference:version:{self.version}"] if dependencies else []))
                      for i in range(len(REGIONS))]

    def valid(self, i):
        item = self.lease[i]
        return bool(item and item["expires"] > self.day and item["version"] == self.version)

    def service(self, i):
        h, r, a = self.indices(i)
        for index in (h, r, a):
            for j in range(self.size):
                self.cov[index][j] = self.cov[j][index] = 0.
        self.mean[h], self.mean[r] = .12, .0008
        self.cov[h][h], self.cov[r][r] = .012**2, .001**2
        self.reset_anchor(i)


def action_set(memory):
    actions = []
    for i in range(len(REGIONS)):
        h, _, _ = memory.indices(i)
        actions.append(dict(name=f"Region {i}: oblique", kind="regional", region=i, cost=1.,
                            readings=[([(h, 1.), (memory.bias, 1.)], .025)]))
        actions.append(dict(name=f"Region {i}: complementary pair", kind="pair", region=i, cost=1.8,
                            readings=[([(h, 1.), (memory.bias, 1.)], .025),
                                      ([(h, 1.), (memory.bias, -1.)], .025)]))
    actions.append(dict(name="Shared reference", kind="reference", region=None, cost=.6,
                        readings=[([(memory.bias, 1.)], .015)]))
    return actions


def finish_acquisition(memory, action):
    if action["region"] is not None:
        memory.reset_anchor(action["region"])
    if action["kind"] in ("reference", "pair"):
        memory.reference_center = memory.mean[memory.bias]
        memory.reference_day = memory.day
        memory.reference_valid = True


def hypothetical(memory, action):
    """Three-point Gaussian quadrature per reading, approximate preposterior utility."""
    branches = [(1., memory.clone())]
    for weights, noise in action["readings"]:
        expanded = []
        for probability, b in branches:
            mean = sum(b.mean[j]*w for j, w in weights)
            variance = noise**2+sum(u*v*b.cov[i][j] for i, u in weights for j, v in weights)
            for z, weight in ((-sqrt(3), 1/6), (0., 2/3), (sqrt(3), 1/6)):
                child = b.clone()
                child.observe(weights, noise, mean+z*sqrt(variance))
                expanded.append((probability*weight, child))
        branches = expanded
    for probability, b in branches:
        finish_acquisition(b, action)
        yield probability, b


def due_regions(memory, policy):
    if policy == "periodic":
        return [i for i in range(len(REGIONS)) if memory.day-memory.last_direct[i] >= 4]
    if policy == "snapshot":
        return [i for i in range(len(REGIONS)) if memory.cov[3*i][3*i] > .04**2 or memory.mean[3*i] > .60]
    return [i for i in range(len(REGIONS)) if not memory.valid(i)]


def select_action(memory, policy, available, used):
    due = due_regions(memory, policy)
    if not due:
        return None, []
    candidates = [a for a in action_set(memory) if a["cost"] <= available+1e-9 and a["name"] not in used]
    if policy not in ("revocable", "renewal"):
        # Regional policies share a fixed complementary acquisition for comparisons.
        targets = sorted(due, key=lambda i: (memory.lease[i]["expires"] if memory.lease[i] else memory.last_direct[i],
                                             -memory.mean[3*i]))
        for i in targets:
            match = next((a for a in candidates if a["region"] == i and a["kind"] == "pair"), None)
            if match:
                return match, []
        return None, []
    # Service deadlines outrank acquisition savings. Without this constraint,
    # healthy easy-to-certify regions can starve a genuinely changing region.
    mandatory = [i for i in due if memory.certify(i, False)["expires"] < memory.day or
                 memory.day-memory.last_direct[i] >= memory.settings.max_gap]
    if mandatory:
        target = max(mandatory, key=lambda i: (memory.day-memory.last_direct[i] >= memory.settings.max_gap,
                                               memory.mean[3*i]+2*sqrt(max(0, memory.cov[3*i][3*i]))))
        candidates = [a for a in candidates if a["region"] == target]
    baseline = [memory.certify(i, True) for i in range(len(REGIONS))]
    before_days = sum(baseline[i]["days"] for i in due)
    ranks = []
    for action in candidates:
        if policy == "revocable":
            _, b = next(hypothetical(memory, action))
            dimensions = [3*i for i in due]+[memory.bias]
            gain = sum(.5*log(max(1e-15, memory.cov[j][j])/max(1e-15, b.cov[j][j])) for j in dimensions)
            ranks.append(dict(name=action["name"], score=gain/action["cost"],
                              expected_days=None, expected_due_resolved=None, cost=action["cost"]))
            continue
        extension = overdue_recovered = 0.
        for probability, b in hypothetical(memory, action):
            certs = [b.certify(i, True) for i in range(len(REGIONS))]
            extension += probability*(sum(certs[i]["days"] for i in due)-before_days)
            overdue_recovered += probability*sum(certs[i]["expires"] > memory.day for i in due)
        # Global positive extension only; negative outcomes are included in expectation.
        score = (extension+4*overdue_recovered)/action["cost"]-memory.settings.acquisition_penalty
        ranks.append(dict(name=action["name"], score=score, expected_days=extension,
                          expected_due_resolved=overdue_recovered, cost=action["cost"]))
    ranks.sort(key=lambda row: (-row["score"], row["cost"], row["name"]))
    if ranks:
        chosen = next(a for a in candidates if a["name"] == ranks[0]["name"])
        # Never disguise an expired certificate by declaring "no useful view".
        return chosen, ranks
    return None, ranks


def run(policy="renewal", scenario="steady", seed=17, settings=Settings()):
    memory = Memory(settings)
    dependencies = policy in ("revocable", "renewal")
    memory.renew(dependencies)
    truth_h = [r["mean"] for r in REGIONS]
    truth_r = [r["rate"] for r in REGIONS]
    true_bias = .04
    counts = [0]*len(REGIONS)
    reference_count = repairs = missed_days = false_service = regional_images = 0
    total_cost = 0.
    frames = []
    # Indexed noise provides common random numbers regardless of policy acquisitions.
    for day in range(1, settings.days+1):
        memory.advance(freeze=policy == "snapshot")
        process_rng = random.Random(seed*100000+day)
        for i in range(len(REGIONS)):
            truth_h[i] += truth_r[i]+process_rng.gauss(0, settings.health_noise)
            truth_r[i] += process_rng.gauss(0, settings.rate_noise)
        true_bias += process_rng.gauss(0, settings.bias_noise)
        event = None
        if scenario == "calibration" and day == 18:
            true_bias += .20
            event = "Public sensor-calibration alert: shared evidence revoked"
            memory.sensor_event(revoke=dependencies)
        if scenario == "local_change" and day == 24:
            truth_h[0] += .70
            event = "Unannounced physical change (simulation truth only)"
        before = [dict(c) for c in memory.lease]
        actions, used, available = [], set(), settings.day_budget
        for _ in range(3):
            action, ranking = select_action(memory, policy, available, used)
            if action is None:
                break
            old_ends = [c["expires"] for c in memory.lease]
            residuals = []
            surprises = []
            for reading, (weights, noise) in enumerate(action["readings"]):
                values = [0.]*memory.size
                for i in range(len(REGIONS)):
                    values[3*i] = truth_h[i]
                values[memory.bias] = true_bias
                measurement_rng = random.Random(seed*1000000+day*1000+(9 if action["region"] is None else action["region"])*20+reading+(10 if action["kind"] == "pair" else 0))
                measurement = sum(values[j]*w for j, w in weights)+measurement_rng.gauss(0, noise)
                predicted = sum(memory.mean[j]*w for j, w in weights)
                variance = noise**2+sum(u*v*memory.cov[a][b] for a, u in weights for b, v in weights)
                if action["region"] is not None and abs(measurement-predicted) > 4*sqrt(variance):
                    # Observation-triggered change-point fallback, shared by policies.
                    # Inflate before assimilation; never assimilate a reading twice.
                    h, r, _ = memory.indices(action["region"])
                    memory.cov[h][h] += .20**2
                    memory.cov[r][r] += .008**2
                    surprises.append(reading)
                residuals.append(memory.observe(weights, noise, measurement))
            finish_acquisition(memory, action)
            i = action["region"]
            if i is None:
                reference_count += 1
            else:
                counts[i] += 1
                regional_images += len(action["readings"])
            maintenance = None
            # Same observation-triggered service rule for every policy.
            if i is not None and upper_tail(memory.mean[3*i], memory.cov[3*i][3*i], settings.damage_limit) > .5:
                false_service += int(truth_h[i] < settings.damage_limit)
                truth_h[i], truth_r[i] = .12, .0008
                memory.service(i)
                repairs += 1
                total_cost += 6.
                maintenance = f"Region {i}: idealized maintenance reset"
            memory.renew(dependencies)
            total_cost += action["cost"]
            available -= action["cost"]
            used.add(action["name"])
            renewed = [j for j, c in enumerate(memory.lease) if c["expires"] > old_ends[j]]
            actions.append(dict(name=action["name"], region=i, kind=action["kind"], cost=action["cost"],
                                ranking=ranking[:5], renewed=renewed, residuals=residuals,
                                maintenance=maintenance, surprises=surprises))
        missed_days += sum(h >= settings.damage_limit for h in truth_h)
        regions = []
        for i, config in enumerate(REGIONS):
            h, r, a = memory.indices(i)
            certificate = memory.lease[i]
            regions.append(dict(name=config["name"], mean=memory.mean[h], sigma=sqrt(max(0, memory.cov[h][h])),
                                rate=memory.mean[r], rate_sigma=sqrt(max(0, memory.cov[r][r])),
                                age=day-memory.last_direct[i], last_direct=memory.last_direct[i],
                                certificate=certificate, valid=memory.valid(i), scans=counts[i],
                                truth=truth_h[i], true_rate=truth_r[i],
                                due=i in due_regions(memory, policy)))
        frames.append(dict(day=day, regions=regions, actions=actions, event=event,
                           bias=memory.mean[memory.bias], bias_sigma=sqrt(max(0, memory.cov[memory.bias][memory.bias])),
                           reference_day=memory.reference_day, reference_valid=memory.reference_valid,
                           version=memory.version, certificates_before=before,
                           overdue=sum(r["due"] for r in regions), idle=not actions))
    return dict(policy=policy, scenario=scenario, seed=seed, frames=frames,
                metrics=dict(region_scans=counts, reference_scans=reference_count, acquisition_cost=total_cost-6*repairs,
                             regional_images=regional_images,
                             total_cost=total_cost, repairs=repairs, false_service=false_service,
                             missed_region_days=missed_days, idle_days=sum(f["idle"] for f in frames),
                             overdue_region_days=sum(f["overdue"] for f in frames)))
