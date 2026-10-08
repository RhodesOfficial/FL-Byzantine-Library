"""D §2.1 reference/scoring primitives. No budget or protocol commit here.

An event receives only already eligible arrivals. Gate 0.4 must filter budget
waiters before calling it, then supply final coefficients to the pure writer.
"""
from dataclasses import dataclass
import math
from typing import Mapping

import torch

DOMAIN_ATOL = 1e-10


@dataclass(frozen=True)
class ReferenceConfig:
    projection_buckets: int = 32
    projection_seed: int = 0
    sigma_min: float = .05
    e_ready: float = .5
    kappa_u: float = .1
    z_cut: float = 3.
    clip_reference: float = 1.
    eta_reference: float = .1
    n_boot: int = 3
    specification: str = "D2_PRIME_DESIGN:2.1/phase0.3-v1"

    def __post_init__(self):
        for value in (self.projection_buckets, self.n_boot):
            if type(value) is not int or value < 1:
                raise ValueError("dimensions and bootstrap count must be positive integers")
        if type(self.projection_seed) is not int or not 0 <= self.projection_seed < 2**63:
            raise ValueError("projection seed must be a nonnegative 63-bit integer")
        for value in (self.sigma_min, self.e_ready, self.kappa_u, self.z_cut,
                      self.clip_reference, self.eta_reference):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("reference parameters must be finite and positive")
        if self.sigma_min > .25 or self.e_ready > 1 or self.eta_reference > 1:
            raise ValueError("reference parameters outside their domains")

    @property
    def dimension(self):
        return self.projection_buckets + 1


@dataclass(frozen=True)
class FeatureMap:
    buckets: tuple
    signs: tuple
    bucket_count: int

    def __post_init__(self):
        object.__setattr__(self, "buckets", tuple(self.buckets))
        object.__setattr__(self, "signs", tuple(self.signs))
        if type(self.bucket_count) is not int or self.bucket_count < 1:
            raise ValueError("invalid bucket count")
        if not self.buckets or len(self.buckets) != len(self.signs):
            raise ValueError("invalid feature map lengths")
        if any(type(h) is not int or not 0 <= h < self.bucket_count for h in self.buckets):
            raise ValueError("invalid feature bucket")
        if any(type(s) is not int or s not in (-1, 1) for s in self.signs):
            raise ValueError("invalid feature sign")

    @classmethod
    def generate(cls, model_dimension, config):
        if type(model_dimension) is not int or model_dimension < 1:
            raise ValueError("invalid model dimension")
        rng = torch.Generator(device="cpu").manual_seed(config.projection_seed)
        buckets = torch.randint(config.projection_buckets, (model_dimension,), generator=rng)
        signs = 2 * torch.randint(2, (model_dimension,), generator=rng) - 1
        return cls(tuple(buckets.tolist()), tuple(signs.tolist()), config.projection_buckets)


def vector(value, dimension):
    x = torch.as_tensor(value, dtype=torch.float64, device="cpu").clone()
    if x.shape != (dimension,) or not torch.isfinite(x).all():
        raise ValueError("expected a finite vector of the declared dimension")
    return x


def clip_l2(value, bound):
    if not math.isfinite(bound) or bound <= 0:
        raise ValueError("invalid clipping bound")
    x = torch.as_tensor(value, dtype=torch.float64, device="cpu").clone()
    if x.ndim != 1 or not x.numel() or not torch.isfinite(x).all():
        raise ValueError("invalid clipping vector")
    norm = x.norm().item()
    if not math.isfinite(norm):
        raise ValueError("nonfinite vector norm")
    return x * min(1., bound / norm) if norm else x


def features(clipped_delta, mapping, model_bound):
    if not math.isfinite(model_bound) or model_bound <= 0:
        raise ValueError("invalid model clipping bound")
    delta = vector(clipped_delta, len(mapping.buckets))
    norm = delta.norm().item()
    if not math.isfinite(norm) or norm > model_bound * (1 + DOMAIN_ATOL):
        raise ValueError("feature input must already be full-norm clipped")
    sums = torch.zeros(mapping.bucket_count, dtype=torch.float64)
    sums.scatter_add_(0, torch.tensor(mapping.buckets), delta * torch.tensor(mapping.signs))
    projected = (sums * (math.sqrt(mapping.bucket_count) / model_bound)).clamp(-1., 1.)
    return tuple(torch.cat((projected, torch.tensor([norm / model_bound], dtype=torch.float64))).tolist())


@dataclass(frozen=True)
class ReferenceState:
    mu: tuple
    sigma: tuple
    evidence: float

    def __post_init__(self):
        object.__setattr__(self, "mu", tuple(self.mu))
        object.__setattr__(self, "sigma", tuple(self.sigma))
        if not self.mu or len(self.mu) != len(self.sigma):
            raise ValueError("invalid reference dimensions")
        if not all(math.isfinite(x) for x in (*self.mu, *self.sigma, self.evidence)):
            raise ValueError("nonfinite reference")

    @classmethod
    def initial(cls, config):
        return cls((0.,) * config.dimension, (.25,) * config.dimension, 0.)

    @property
    def uncertainty(self):
        return 1 - self.evidence

    def ready(self, config):
        return self.evidence >= config.e_ready

    def normalized(self):
        root = math.sqrt(len(self.mu))
        return torch.tensor((*[x / root for x in self.mu],
                             *[x / root for x in self.sigma], self.evidence), dtype=torch.float64)


def validate_state(state, config):
    if len(state.mu) != config.dimension:
        raise ValueError("reference dimension mismatch")
    if (any(not -1-DOMAIN_ATOL <= x <= 1+DOMAIN_ATOL for x in state.mu)
        or any(not config.sigma_min-DOMAIN_ATOL <= x <= 1+DOMAIN_ATOL for x in state.sigma)
        or not -DOMAIN_ATOL <= state.evidence <= 1+DOMAIN_ATOL):
        raise ValueError("reference domain violation; no post-write projection is allowed")


@dataclass(frozen=True)
class ColdStatistics:
    center: tuple
    scale: tuple


def cold_statistics(feature_rows, config):
    if len(feature_rows) < config.n_boot:
        return None
    rows = torch.stack([vector(x, config.dimension) for x in feature_rows])
    # torch.median chooses the lower middle for even n; D requires their mean.
    def median(values):
        ordered = values.sort(dim=0).values
        n = len(ordered)
        return (ordered[(n-1)//2] + ordered[n//2]) / 2
    center = median(rows)
    scale = median((rows-center).abs()).clamp(config.sigma_min, 1.)
    return ColdStatistics(tuple(center.tolist()), tuple(scale.tolist()))


def score_feature(feature, source, cold, config):
    validate_state(source, config)
    x = vector(feature, config.dimension)
    if (x.abs() > 1+DOMAIN_ATOL).any() or x[-1] < -DOMAIN_ATOL:
        raise ValueError("feature outside declared domain")
    if source.ready(config):
        residual = x - torch.tensor(source.mu, dtype=torch.float64)
        denominator = torch.tensor(source.sigma, dtype=torch.float64).square()
        denominator += (config.kappa_u * source.uncertainty)**2
        z = (residual.square() / denominator).mean().sqrt().item()
        path = "source"
    elif cold is None:
        return "waiting", None, None
    else:
        center, scale = vector(cold.center, config.dimension), vector(cold.scale, config.dimension)
        if (scale < config.sigma_min).any() or (scale > 1).any():
            raise ValueError("invalid cold scale")
        z = ((x-center) / scale).square().mean().sqrt().item()
        path = "cold"
    g = (1-(z/config.z_cut)**2)**2 if z < config.z_cut else 0.
    return path, z, g


@dataclass(frozen=True)
class ReferenceCandidate:
    task_id: int
    identity: int
    source_version: int
    source: ReferenceState
    feature: tuple


@dataclass(frozen=True)
class Proposal:
    task_id: int
    identity: int
    source_version: int
    feature: tuple
    path: str
    z: float | None
    g: float | None
    h: float
    a0: float
    b0: float
    scale_target: tuple
    direction: tuple


@dataclass(frozen=True)
class ReferenceEvent:
    before: ReferenceState
    config: ReferenceConfig
    cold: ColdStatistics | None
    proposals: tuple


def prepare_event(candidates, before, config, capacity, eta_model, current_version):
    """Read-only event preparation from eligible arrivals and immutable sources."""
    validate_state(before, config)
    if type(capacity) is not int or not 1 <= config.n_boot <= capacity:
        raise ValueError("require 1 <= n_boot <= K")
    if not math.isfinite(eta_model) or eta_model <= 0:
        raise ValueError("invalid model step")
    if type(current_version) is not int or current_version < 0:
        raise ValueError("invalid current version")
    candidates = tuple(sorted(candidates, key=lambda c: c.task_id))
    if (len(candidates) > capacity or len({c.identity for c in candidates}) != len(candidates)
        or len({c.task_id for c in candidates}) != len(candidates)):
        raise ValueError("event must contain <= K unique tasks and identities")
    for c in candidates:
        if type(c.source_version) is not int or not 0 <= c.source_version <= current_version:
            raise ValueError("future or invalid source version")
        validate_state(c.source, config)
        x = vector(c.feature, config.dimension)
        if (x.abs() > 1+DOMAIN_ATOL).any() or x[-1] < -DOMAIN_ATOL:
            raise ValueError("feature outside declared domain")
    cold = cold_statistics([c.feature for c in candidates], config)
    proposals = []
    for c in candidates:
        path, z, g = score_feature(c.feature, c.source, cold, config)
        h = 1 / (1 + current_version - c.source_version)
        a0, b0, scale, direction = 0., 0., (), ()
        if g is not None and g > 0:
            x = vector(c.feature, config.dimension)
            scale_tensor = (x-torch.tensor(before.mu, dtype=torch.float64)).abs().clamp(config.sigma_min, 1.)
            target = ReferenceState(tuple(x.tolist()), tuple(scale_tensor.tolist()), 1.)
            direction = tuple(clip_l2(target.normalized()-before.normalized(), config.clip_reference).tolist())
            scale = tuple(scale_tensor.tolist())
            a0, b0 = eta_model*h*g/capacity, config.eta_reference*h*g/capacity
        proposals.append(Proposal(c.task_id, c.identity, c.source_version, tuple(c.feature),
                                  path, z, g, h, a0, b0, scale, direction))
    return ReferenceEvent(before, config, cold, tuple(proposals))


@dataclass(frozen=True)
class ReferenceWrite:
    after: ReferenceState
    contributions: tuple  # (task_id, b_i * v_i), in deterministic task order.
    displacement: tuple


def write_reference(event, coefficients: Mapping[int, float]):
    """Pure §2.1 writer; coefficients are external final b_i, NOT a budget."""
    accepted = [p for p in event.proposals if p.g is not None and p.g > 0]
    if set(coefficients) != {p.task_id for p in accepted}:
        raise ValueError("supply one final reference coefficient per positive-score proposal")
    contributions = []
    displacement = torch.zeros(2*event.config.dimension+1, dtype=torch.float64)
    for p in accepted:
        b = coefficients[p.task_id]
        if not math.isfinite(b) or not 0 <= b <= p.b0:
            raise ValueError("reference coefficient outside nominal bound")
        term = b * vector(p.direction, len(displacement))
        displacement += term
        contributions.append((p.task_id, tuple(term.tolist())))
    normalized = event.before.normalized() + displacement
    d, root = event.config.dimension, math.sqrt(event.config.dimension)
    after = ReferenceState(tuple((normalized[:d]*root).tolist()),
                           tuple((normalized[d:2*d]*root).tolist()), normalized[-1].item())
    validate_state(after, event.config)
    return ReferenceWrite(after, tuple(contributions), tuple(displacement.tolist()))
