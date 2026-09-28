"""Small exact inspection laboratory. No external dependencies or hidden-state planning."""
from dataclasses import dataclass, asdict
from itertools import product, combinations
from math import erf, sqrt, hypot, log2, cos, sin, pi
from time import perf_counter
import random

STATES = tuple(product((0, 1), repeat=3))  # damage, fast deterioration, artifact polarity
BASE = (-3., 0.)
HAZARD = (.015, .16)
REPAIR, FAILURE = 20., 100.


@dataclass(frozen=True)
class Stage:
    name: str
    added: str
    policy: str
    memory: str
    status: str
    explanation: str


STAGES = (
    Stage("Coverage", "Geometric coverage", "coverage", "none", "Established baseline",
          "Visit the view exposing the most unseen schematic surface patches per travel cost."),
    Stage("Uncertainty", "Damage information gain", "entropy", "none", "Established baseline",
          "Choose a view by expected damage entropy reduction. More certainty need not change an intervention."),
    Stage("Decision value", "Maintenance loss and stopping", "myopic", "none", "Established baseline",
          "Acquire only when expected maintenance savings exceed acquisition and travel cost."),
    Stage("Snapshot memory", "Reuse historical observations", "myopic", "snapshot", "Established ingredient",
          "Replay historical observations but assume damage never evolves. Keep damage/rate and artifact marginals separately."),
    Stage("Temporal memory", "Time and deterioration rate", "myopic", "temporal", "Established ingredient",
          "Propagate damage using a latent slow/fast rate between timestamped observations and to today."),
    Stage("Joint memory", "Damage–artifact dependencies", "myopic", "joint", "Established ingredient",
          "Retain the complete joint posterior. Evidence about an artifact can now revise the damage belief."),
    Stage("Complementary NBV", "Adaptive two-view lookahead", "exact", "joint", "Strong established comparator",
          "Enumerate feasible first views and all outcome-dependent second views. This is standard finite-horizon planning."),
    Stage("Sparse pair graph", "Memory-conditioned pair proposals", "graph", "joint", "Candidate contribution — unverified",
          "Use belief covariances with future failure risk to shortlist view pairs, then score them with exact maintenance loss. Keep every singleton and stopping."),
)


@dataclass(frozen=True)
class View:
    name: str
    x: float
    y: float
    damage: float
    nuisance: float
    offset: float
    noise: float
    patches: tuple

    def signal(self, state):
        d, _, n = state
        return self.offset + self.damage*d + self.nuisance*(n-.5)


def make_views(count=12):
    if count < 3:
        raise ValueError("At least three candidate views are required")
    views = []
    for i in range(count):
        angle = 2*pi*i/count
        kind = i % 3
        # Schematic pose-dependent responses, not a physical optics model.
        d, n, offset, noise = ((1., .8+.2*cos(angle), 0., .13),
                              (0., 1., .5, .10),
                              (1., 0., 0., .62))[kind]
        views.append(View(f"{'contrast reference direct'.split()[kind]}_{i:02d}",
                          2*cos(angle), 2*sin(angle), d, n, offset,
                          noise+.015*(i//3), tuple({i % 8, (i+1) % 8})))
    return tuple(views)


def initial(damage=.12, fast=.35, artifact=.5):
    return tuple((damage if d else 1-damage)*(fast if r else 1-fast)*
                 (artifact if n else 1-artifact) for d, r, n in STATES)


def normalize(weights):
    total = sum(weights)
    if total <= 0:
        raise ValueError("Observation has zero probability under the model")
    return tuple(w/total for w in weights)


def factorize(b):
    """Preserve p(d,r) and p(n); discard only their dependence."""
    dr = {(d, r): sum(p for p, (dd, rr, _) in zip(b, STATES)
                     if (d, r) == (dd, rr)) for d, r in product((0, 1), repeat=2)}
    pn = [sum(p for p, (_, _, nn) in zip(b, STATES) if nn == n) for n in (0, 1)]
    return tuple(dr[d, r]*pn[n] for d, r, n in STATES)


def transition(b, elapsed, flip=.02):
    """Irreversible damage; fixed latent rate; symmetric artifact Markov process."""
    if elapsed < 0:
        raise ValueError("Timestamps must be nondecreasing")
    change_n = (1-(1-2*flip)**elapsed)/2
    out = [0.]*len(STATES)
    for weight, (d, r, n) in zip(b, STATES):
        pd = 1. if d else 1-(1-HAZARD[r])**elapsed
        for j, (dd, rr, nn) in enumerate(STATES):
            if rr == r:
                out[j] += weight*(pd if dd else 1-pd)*(1-change_n if nn == n else change_n)
    return tuple(out)


def likelihood(view, state):
    mu = view.signal(state)
    cdf = lambda edge: .5*(1+erf((edge-mu)/(view.noise*sqrt(2))))
    lo, hi = cdf(.25), cdf(.75)
    return lo, hi-lo, 1-hi


def risk_state(state, horizon=1.):
    d, r, _ = state
    return 1. if d else 1-(1-HAZARD[r])**horizon


def expected_risk(b):
    return sum(p*risk_state(s) for p, s in zip(b, STATES))


def decision(b):
    loss = FAILURE*expected_risk(b)
    return (REPAIR, "repair") if loss >= REPAIR else (loss, "defer")


def entropy(b):
    p = sum(w for w, (d, _, _) in zip(b, STATES) if d)
    return -sum(q*log2(q) for q in (p, 1-p) if q > 0)


def summarize(b):
    marginals = [sum(p*s[i] for p, s in zip(b, STATES)) for i in range(3)]
    cov = sum(p*s[0]*s[2] for p, s in zip(b, STATES))-marginals[0]*marginals[2]
    return dict(damage=marginals[0], fast=marginals[1], artifact=marginals[2],
                covariance=cov, failure=expected_risk(b), joint=list(b))


SCENARIOS = (
    dict(id="ambiguous", name="Fresh inspection", description="No history. This control isolates view selection from memory.",
         history=[], now=0, energy=13., blocked=[], flip=.02),
    dict(id="correlated", name="An ambiguous old image", description="A middle-valued contrast observation links damage and artifact polarity. Factorizing memory loses that link.",
         history=[(0, 0, 1)], now=0, energy=13., blocked=[], flip=.02),
    dict(id="aging", name="Reassuring, then unvisited", description="Old reassuring evidence becomes stale after six time units. Temporal prediction should challenge snapshot memory.",
         history=[(0, 2, 0), (1, 2, 0)], now=7, energy=13., blocked=[], flip=.02),
    dict(id="artifact", name="Reference evidence available", description="A historical reference observation informs the shared artifact; damage evidence arrives later.",
         history=[(0, 1, 2), (1, 0, 1)], now=2, energy=13., blocked=[], flip=.02),
    dict(id="tight", name="Limited travel budget", description="Blocked candidates and return reserve can make an informative pair infeasible. Geometry is held fixed across stages.",
         history=[(0, 0, 1)], now=1, energy=6.8, blocked=[1, 4, 7, 10], flip=.02),
    dict(id="shift", name="Unexpected artifact drift", description="Stress test: the world changes artifact polarity faster than the planner assumes. More memory is not guaranteed to help.",
         history=[(0, 1, 2), (0, 0, 1)], now=4, energy=13., blocked=[], flip=.45),
)


class Lab:
    def __init__(self, scenario, stage, count=12, top_k=4):
        self.scenario, self.stage = scenario, stage
        self.views, self.top_k = make_views(count), top_k
        self.tables = tuple(tuple(likelihood(v, s) for s in STATES) for v in self.views)
        self.expansions = 0
        self.proposal_pairs = 0
        self.bound_checks = 0

    def update(self, b, i, outcome, project=False):
        post = normalize([p*self.tables[i][s][outcome] for s, p in enumerate(b)])
        return factorize(post) if project and self.stage.memory in ("snapshot", "temporal") else post

    def outcomes(self, b, i):
        self.expansions += 1
        for y in range(3):
            p = sum(w*self.tables[i][s][y] for s, w in enumerate(b))
            if p > 0:
                yield y, p, self.update(b, i, y)

    def memory(self, truth=False):
        mode = "joint" if truth else self.stage.memory
        b, clock = initial(), 0
        if mode != "none":
            for time, view, y in self.scenario["history"]:
                b = transition(b, time-clock if mode != "snapshot" else 0,
                               self.scenario["flip"] if truth else .02)
                b = self.update(b, view, y, project=not truth)
                clock = time
        b = transition(b, self.scenario["now"]-clock if mode != "snapshot" else 0,
                       self.scenario["flip"] if truth else .02)
        return factorize(b) if mode in ("snapshot", "temporal") else b

    def position(self, i):
        return BASE if i == -1 else (self.views[i].x, self.views[i].y)

    def travel(self, x, i):
        a, b = self.position(x), self.position(i)
        return hypot(a[0]-b[0], a[1]-b[1])

    def cost(self, x, i):
        return .6+.15*self.travel(x, i)

    def feasible(self, remaining, x, energy):
        return tuple(i for i in remaining if i not in self.scenario["blocked"] and
                     self.travel(x, i)+.25+self.travel(i, -1) <= energy+1e-10)

    def stop(self, b, x):
        return decision(b)[0]+.15*self.travel(x, -1)

    def next_energy(self, energy, x, i):
        return energy-self.travel(x, i)-.25

    def proposals(self, b, remaining, x, energy):
        """Linear regression variance-reduction surrogate; exact loss scores later."""
        target = [risk_state(s) for s in STATES]
        def cov(a, c):
            return sum(p*u*v for p, u, v in zip(b, a, c))-sum(p*u for p, u in zip(b, a))*sum(p*v for p, v in zip(b, c))
        signals = {i: [self.views[i].signal(s) for s in STATES] for i in remaining}
        variances = {i: cov(signals[i], signals[i])+self.views[i].noise**2 for i in remaining}
        relevance = {i: cov(target, signals[i]) for i in remaining}
        ranked = []
        for i, j in combinations(remaining, 2):
            self.proposal_pairs += 1
            routes = []
            for a, c in ((i, j), (j, i)):
                if c in self.feasible((c,), a, self.next_energy(energy, x, a)):
                    routes.append(self.cost(x, a)+self.cost(a, c)+.15*self.travel(c, -1))
            if not routes:
                continue
            a, c, cross = variances[i], variances[j], cov(signals[i], signals[j])
            u, v = relevance[i], relevance[j]
            gain = max(0., (c*u*u-2*cross*u*v+a*v*v)/(a*c-cross*cross))
            single = u*u/a+v*v/c
            # Synergy is diagnostic only; it is not added to the proposal reward.
            ranked.append(dict(i=i, j=j, score=gain/min(routes), proxy_gain=gain,
                               proxy_synergy=gain-single))
        ranked.sort(key=lambda edge: (-edge["score"], edge["i"], edge["j"]))
        return ranked[:self.top_k]

    def plan(self, b, remaining, x, energy, budget):
        feasible = self.feasible(remaining, x, energy)
        stop = self.stop(b, x)
        if budget == 0 or not feasible:
            return dict(action=-1, value=stop, scores=[], edges=[])
        policy = self.stage.policy
        if policy == "coverage":
            seen = {p for i in range(len(self.views)) if i not in remaining for p in self.views[i].patches}
            scores = [(len(set(self.views[i].patches)-seen)/self.cost(x, i), i) for i in feasible]
            gain, action = max(scores, key=lambda pair: (pair[0], -pair[1]))
            return dict(action=action if gain > 0 else -1, value=None,
                        scores=[dict(i=i, score=s) for s, i in scores], edges=[])
        if policy == "entropy":
            scores = [( (entropy(b)-sum(p*entropy(post) for _, p, post in self.outcomes(b, i)))/self.cost(x, i), i) for i in feasible]
            gain, action = max(scores, key=lambda pair: (pair[0], -pair[1]))
            return dict(action=action if gain > 1e-10 else -1, value=None,
                        scores=[dict(i=i, score=s) for s, i in scores], edges=[])
        edges = self.proposals(b, feasible, x, energy) if policy == "graph" and budget > 1 else []
        best, lower_best, action, scores = stop, stop, -1, []
        for i in feasible:
            rest = tuple(j for j in remaining if j != i)
            next_energy = self.next_energy(energy, x, i)
            value = self.cost(x, i)
            lower_value = value
            for _, probability, posterior in self.outcomes(b, i):
                future = self.stop(posterior, i)
                lower_future = future
                if budget > 1 and policy in ("exact", "graph"):
                    seconds = self.feasible(rest, i, next_energy)
                    all_seconds = seconds
                    if policy == "graph":
                        seconds = tuple(j for j in seconds if any({i, j} == {e["i"], e["j"]} for e in edges))
                    for j in seconds:
                        candidate = self.cost(i, j)+sum(p*self.stop(post, j) for _, p, post in self.outcomes(posterior, j))
                        future = min(future, candidate)
                    lower_future = future
                    if policy == "graph":
                        # Perfect latent-state information is an optimistic relaxation,
                        # not access to simulator truth. Future failure remains stochastic.
                        clairvoyant = sum(p*min(REPAIR, FAILURE*risk_state(s))
                                          for p, s in zip(posterior, STATES))
                        for j in all_seconds:
                            if j not in seconds:
                                self.bound_checks += 1
                                lower_future = min(lower_future, self.cost(i, j)+
                                                   .15*self.travel(j, -1)+clairvoyant)
                value += probability*future
                lower_value += probability*lower_future
            scores.append(dict(i=i, score=value))
            lower_best = min(lower_best, lower_value)
            if value < best-1e-10:
                best, action = value, i
        certificate = dict(lower_bound=lower_best, upper_bound=best,
                           max_regret=max(0., best-lower_best)) if policy == "graph" else None
        return dict(action=action, value=best, scores=scores, edges=edges, certificate=certificate)

    def evaluate(self, b, truth, remaining, x, energy, budget):
        """Score the policy under the true conditional belief, never its own confidence."""
        plan = self.plan(b, remaining, x, energy, budget)
        i = plan["action"]
        if i == -1:
            repair = decision(b)[1] == "repair"
            failure = expected_risk(truth)
            return dict(cost=(REPAIR if repair else FAILURE*failure)+.15*self.travel(x, -1),
                        views=0., missed=0. if repair else failure,
                        unnecessary=(1-failure) if repair else 0.,
                        calibration=(expected_risk(b)-failure)**2,
                        distance=self.travel(x, -1))
        result = dict(cost=self.cost(x, i), views=1., missed=0., unnecessary=0., calibration=0., distance=self.travel(x, i))
        for y in range(3):
            p = sum(w*self.tables[i][s][y] for s, w in enumerate(truth))
            if p == 0:
                continue
            child = self.evaluate(self.update(b, i, y), self.update(truth, i, y, False),
                                  tuple(j for j in remaining if j != i), i,
                                  self.next_energy(energy, x, i), budget-1)
            for key in result:
                result[key] += p*child[key]
        return result

    def replay(self, b, truth, seed):
        rng = random.Random(seed)
        state_index = rng.choices(range(8), weights=truth)[0]
        # A fixed draw per candidate shares potential observations across policies.
        uniforms = [rng.random() for _ in self.views]
        frames, remaining, x, energy = [], tuple(range(len(self.views))), -1, self.scenario["energy"]
        for step in range(3):
            plan = self.plan(b, remaining, x, energy, 2-step)
            i = plan["action"]
            frame = dict(step=step, belief=summarize(b), position=x, energy=energy,
                         next=i, plan=plan, feasible=list(self.feasible(remaining, x, energy)),
                         decision=decision(b)[1])
            if i == -1:
                frames.append(frame)
                break
            probabilities = self.tables[i][state_index]
            y = 0 if uniforms[i] < probabilities[0] else 1 if uniforms[i] < sum(probabilities[:2]) else 2
            frame["observation"] = y
            frames.append(frame)
            b = self.update(b, i, y)
            energy, x = self.next_energy(energy, x, i), i
            remaining = tuple(j for j in remaining if j != i)
        return dict(state=list(STATES[state_index]), frames=frames)


def run_stage(scenario, stage, count=12, top_k=4, seed=7):
    lab = Lab(scenario, stage, count, top_k)
    b, truth = lab.memory(), lab.memory(True)
    remaining = tuple(range(count))
    start = perf_counter()
    first = lab.plan(b, remaining, -1, scenario["energy"], 2)
    elapsed = (perf_counter()-start)*1000
    work = dict(branch_expansions=lab.expansions, proxy_pairs=lab.proposal_pairs,
                bound_checks=lab.bound_checks, root_ms=elapsed)
    evaluation = lab.evaluate(b, truth, remaining, -1, scenario["energy"], 2)
    return dict(stage=asdict(stage), prior=summarize(b), truth=summarize(truth),
                first=first, work=work, metrics=evaluation, replay=lab.replay(b, truth, seed))
