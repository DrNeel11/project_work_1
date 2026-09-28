"""Exact scalar-observation preposterior scoring for allocated-risk certificates.

This is a separate certificate rule, not an exact solver for model.py's summed
tail rule. Constraints and risk allocations must be fixed before observing.
"""
from dataclasses import dataclass
from math import erfc, inf, isfinite, sqrt
from statistics import NormalDist


@dataclass(frozen=True)
class Constraint:
    mean: float
    variance: float
    loading: float  # Cov(target, standardized scalar observation)
    lower: float
    upper: float
    alpha: float

    def interval(self):
        """Innovation values satisfying allocated one/two-sided tail bounds."""
        if not all(isfinite(x) for x in (self.mean, self.variance, self.loading, self.alpha)):
            raise ValueError("finite moments and alpha required")
        if not 0 < self.alpha < .5 or self.lower >= self.upper:
            raise ValueError("invalid risk allocation or bounds")
        residual = self.variance-self.loading**2
        if residual < -1e-12 or self.variance < 0:
            raise ValueError("inconsistent joint Gaussian covariance")
        sides = int(self.lower != -inf)+int(self.upper != inf)
        if not sides:
            return -inf, inf
        margin = NormalDist().inv_cdf(1-self.alpha/sides)*sqrt(max(0., residual))
        lo, hi = self.lower+margin-self.mean, self.upper-margin-self.mean
        if lo > hi:
            return inf, -inf
        if self.loading == 0:
            return (-inf, inf) if lo <= 0 <= hi else (inf, -inf)
        bounds = lo/self.loading, hi/self.loading
        return min(bounds), max(bounds)


def gaussian_mass(lo, hi):
    if lo >= hi:
        return 0.
    if lo >= 0:
        return .5*(erfc(lo/sqrt(2))-erfc(hi/sqrt(2)))
    if hi <= 0:
        return .5*(erfc(-hi/sqrt(2))-erfc(-lo/sqrt(2)))
    return 1-.5*erfc(hi/sqrt(2))-.5*erfc(-lo/sqrt(2))


def compile_prefixes(days):
    """Each day's constraints extend the certified prefix; O(total constraints)."""
    lo, hi = -inf, inf
    result = []
    for constraints in days:
        for constraint in constraints:
            left, right = constraint.interval()
            lo, hi = max(lo, left), min(hi, right)
        result.append(dict(lower=lo, upper=hi, probability=gaussian_mass(lo, hi)))
    return result


def expected_days(days):
    return sum(item['probability'] for item in compile_prefixes(days))


def remote_view_score(memory, weights, noise, regions=range(4), risk=.05):
    """Physical stability score; no reset of direct anchors, no calibration lease.

    A scalar camera/reference reading can inform other regions through covariance.
    Fixed full-horizon allocations guarantee a union bound <= risk per region.
    A public dependency revocation must separately prohibit certificate issuance.
    """
    if noise <= 0 or not 0 < risk < .5:
        raise ValueError('positive measurement noise and risk in (0,.5) required')
    s = memory.settings
    ph = [sum(row[j]*w for j, w in weights) for row in memory.cov]
    innovation_sd = sqrt(noise**2+sum(ph[j]*w for j, w in weights))
    output = []
    for i in regions:
        h, r, a = memory.indices(i)
        horizon = max(0, s.max_gap-(memory.day-memory.last_direct[i]))
        days = []
        # Includes current-time constraints in every positive-length prefix.
        alpha = risk/(2*(horizon+1))
        current = []
        for k in range(horizon+1):
            process = k*s.health_noise**2+(k-1)*k*(2*k-1)/6*s.rate_noise**2
            mean = memory.mean[h]+k*memory.mean[r]
            variance = memory.cov[h][h]+2*k*memory.cov[h][r]+k*k*memory.cov[r][r]+process
            loading = (ph[h]+k*ph[r])/innovation_sd
            constraints = [Constraint(mean, variance, loading, -inf, s.damage_limit, alpha),
                Constraint(mean-memory.mean[a],
                    max(0., variance+memory.cov[a][a]-2*(memory.cov[h][a]+k*memory.cov[r][a])),
                    loading-ph[a]/innovation_sd, -s.change_limit, s.change_limit, alpha)]
            if k == 0:
                current = constraints
            else:
                days.append((current if k == 1 else [])+constraints)
        output.append(dict(region=i, expected_days=expected_days(days), prefixes=compile_prefixes(days)))
    return dict(expected_days=sum(x['expected_days'] for x in output), regions=output)
