"""Exact, dependency-free reference experiment for complementary inspection views."""
from dataclasses import dataclass
from functools import lru_cache
from math import log2
import json

# State is (critical deterioration, persistent appearance artifact).
STATES = ((0, 0), (0, 1), (1, 0), (1, 1))


@dataclass(frozen=True)
class View:
    name: str
    error: float
    cost: float
    mode: str

    def likelihood(self, state, observation):
        damage, artifact = state
        signal = {"contrast": damage ^ artifact,
                  "reference": artifact, "direct": damage}[self.mode]
        return 1 - self.error if observation == signal else self.error


VIEWS = (View("oblique_contrast", .02, 1., "contrast"),
         View("reference_patch", .02, 1., "reference"),
         View("direct_noisy", .30, 1., "direct"))


def prior(damage=.2, artifact=.5):
    return tuple((damage if d else 1-damage) *
                 (artifact if n else 1-artifact) for d, n in STATES)


def branches(belief, view):
    for observation in (0, 1):
        weights = tuple(p * view.likelihood(s, observation)
                        for p, s in zip(belief, STATES))
        probability = sum(weights)
        if probability:
            yield probability, tuple(w / probability for w in weights)


def decision(belief):
    """Repair costs 20; leaving critical damage costs 100; repair is perfect."""
    defer = 100 * sum(p for p, (d, _) in zip(belief, STATES) if d)
    return (20., "repair") if defer >= 20 else (defer, "defer")


def entropy(belief):
    p = sum(w for w, (d, _) in zip(belief, STATES) if d)
    return -sum(q * log2(q) for q in (p, 1-p) if q > 0)


@lru_cache(None)
def solve(belief, remaining, budget):
    """Exact adaptive finite-horizon Bayes policy, with optional stopping."""
    best = (decision(belief)[0], "stop")
    if budget <= 0:
        return best
    for index in remaining:
        view = VIEWS[index]
        rest = tuple(i for i in remaining if i != index)
        cost = view.cost + sum(p * solve(b, rest, budget-1)[0]
                               for p, b in branches(belief, view))
        if cost < best[0] - 1e-12:
            best = cost, view.name
    return best


def choose(belief, remaining, budget, policy):
    if not remaining or budget == 0:
        return "stop"
    if policy == "pair_aware":
        return solve(belief, remaining, budget)[1]
    if policy == "myopic_voi":
        return solve(belief, remaining, 1)[1]
    if policy == "damage_entropy":
        gains = [(entropy(belief) - sum(p * entropy(b) for p, b in
                  branches(belief, VIEWS[i])), i) for i in remaining]
        gain, index = max(gains)
        return VIEWS[index].name if gain > 1e-12 else "stop"
    if policy == "no_inspection":
        return "stop"
    raise ValueError(policy)


def evaluate(belief, remaining, budget, policy):
    """Enumerate all observation outcomes; no Monte Carlo or hidden-state access."""
    action = choose(belief, remaining, budget, policy)
    if action == "stop":
        return decision(belief)[0], 0.
    index = next(i for i in remaining if VIEWS[i].name == action)
    rest = tuple(i for i in remaining if i != index)
    cost, count = VIEWS[index].cost, 1.
    for probability, posterior in branches(belief, VIEWS[index]):
        child_cost, child_count = evaluate(posterior, rest, budget-1, policy)
        cost += probability * child_cost
        count += probability * child_count
    return cost, count


def experiment():
    results = []
    for damage in (.05, .2, .5):
        for artifact in (0., .5):
            belief = prior(damage, artifact)
            for policy in ("no_inspection", "damage_entropy", "myopic_voi", "pair_aware"):
                cost, count = evaluate(belief, (0, 1, 2), 2, policy)
                results.append(dict(damage_prior=damage, artifact_prior=artifact,
                                    policy=policy, first_view=choose(belief, (0, 1, 2), 2, policy),
                                    expected_total_cost=round(cost, 6),
                                    expected_views=round(count, 6)))
    return results


if __name__ == "__main__":
    print(json.dumps(experiment(), indent=2))
