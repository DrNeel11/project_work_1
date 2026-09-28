"""Small additive proof stage: exact duration versus observation quadrature."""
import json
from math import sqrt
from .exact_renewal import Constraint, expected_days, remote_view_score
from .model import Memory


def main():
    candidates = {}
    for name, lo, hi in [('A', .2, .3), ('B', -.01, .01)]:
        exact = expected_days([[Constraint(0, 1, 1, lo, hi, .01)]])
        approximate = sum(w for z, w in [(-sqrt(3), 1/6), (0, 2/3), (sqrt(3), 1/6)] if lo <= z <= hi)
        candidates[name] = dict(exact=exact, three_node=approximate)
    memory = Memory()
    shared = remote_view_score(memory, [(memory.bias, 1)], .015)
    print(json.dumps(dict(stage=13, candidates=candidates,
        exact_choice=max(candidates, key=lambda k: candidates[k]['exact']),
        quadrature_choice=max(candidates, key=lambda k: candidates[k]['three_node']),
        shared_reference_expected_region_days=shared['expected_days'],
        direct_inspection_times=memory.last_direct,
        scope='allocated-risk scalar Gaussian physical certificate; see PROOF.md'), indent=2))


if __name__ == '__main__':
    main()
