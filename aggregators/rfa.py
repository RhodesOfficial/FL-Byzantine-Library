"""RFA with a passive, final-iteration mixing contract (not causal influence)."""
from dataclasses import dataclass
import hashlib
import math

import torch
from .base import _BaseAggregator


def _compute_euclidean_distance(v1, v2):
    return (v1 - v2).norm()


def _scalar(value):
    # max(distance, nu) can select the Python nu, making beta a Python float.
    return float(value.detach().item()) if isinstance(value, torch.Tensor) else float(value)


MIX_SEMANTICS = "rfa_final_mix_v1"


def tensor_fingerprint(value):
    value = value.detach().contiguous()
    header = f"{tuple(value.shape)}|{value.dtype}|{value.device}|".encode()
    data = value.reshape(-1).view(torch.uint8).cpu().numpy().tobytes()
    return hashlib.sha256(header + data).hexdigest()


@dataclass(frozen=True)
class FinalMix:
    call_id: int
    semantics: str
    input_fingerprints: tuple
    output_fingerprint: str
    shape: tuple
    dtype: str
    device: str
    T: int
    nu: float
    final_betas: tuple
    denominator: float
    weights: tuple


def _validate_problem(weights, alphas, z, nu, T, b):
    m = len(weights)
    if not m or len(alphas) != m:
        raise ValueError("require nonempty inputs and one alpha per input")
    if type(T) is not int or T < 1:
        raise ValueError("T must be a positive integer")
    if isinstance(nu, bool) or not isinstance(nu, (int, float)) or not math.isfinite(nu) or nu <= 0:
        raise ValueError("nu must be finite and positive")
    if type(b) is not int:
        raise ValueError("legacy grouping b must be an integer")
    if any(not math.isfinite(float(a)) or float(a) < 0 for a in alphas):
        raise ValueError("alphas must be finite and nonnegative")
    first = weights[0]
    if not isinstance(first, torch.Tensor) or not first.is_floating_point() or not first.numel():
        raise ValueError("inputs must be nonempty floating tensors")
    for value in (*weights, z):
        if (not isinstance(value, torch.Tensor) or value.shape != first.shape
                or value.dtype != first.dtype or value.device != first.device
                or not torch.isfinite(value).all().item()):
            raise ValueError("inputs and initial z must share finite shape/dtype/device")


def _weiszfeld(weights, alphas, z, nu, T, b):
    _validate_problem(weights, alphas, z, nu, T, b)
    m = len(weights)
    malicious_betas = []
    benign_betas = []
    for t in range(T):
        betas = []
        for k in range(m):
            distance = _compute_euclidean_distance(z, weights[k])
            betas.append(alphas[k] / max(distance, nu))
        denominator = sum(betas)
        if (not math.isfinite(_scalar(denominator)) or _scalar(denominator) <= 0
                or any(not math.isfinite(_scalar(beta)) or _scalar(beta) < 0 for beta in betas)):
            raise ValueError("invalid beta/normalization denominator")
        z = 0
        # Legacy position groups, including the original b=0 slicing behavior.
        # They have no role in the mixing formula or the new ID contract.
        beta_m = betas[-b:]
        beta_m = [b.item() if isinstance(b, torch.Tensor) else b for b in beta_m]

        beta_b = betas[:-b]
        beta_b = [b.item() if isinstance(b, torch.Tensor) else b for b in beta_b]
        benign_betas.extend(beta_b)
        malicious_betas.extend(beta_m)
        for w, beta in zip(weights, betas):
            z += w * beta
        z /= denominator
        if not torch.isfinite(z).all().item():
            raise ValueError("nonfinite aggregate")
    # Capture the betas that just produced z. NEVER recompute distances at z.
    mix = tuple(_scalar(beta / denominator) for beta in betas)
    if any(not math.isfinite(w) or w < 0 for w in mix):
        raise ValueError("invalid final mixing coefficient")
    tolerance = max(1e-10, 8*m*torch.finfo(z.dtype).eps)
    if abs(math.fsum(mix)-1.) > tolerance:
        raise ValueError("final weights do not normalize")
    return (z, malicious_betas, benign_betas, mix,
            tuple(_scalar(beta) for beta in betas), _scalar(denominator))


def smoothed_weiszfeld(weights, alphas, z, nu, T, b, *, return_weights=False):
    """Default six-argument call retains its three-item return contract."""
    result = _weiszfeld(weights, alphas, z, nu, T, b)
    return result[:4] if return_weights else result[:3]


class RFA(_BaseAggregator):
    """Default return is Tensor; side records describe this successful call only."""

    def __init__(self, T, nu=1e-6):
        self.T = T
        self.nu = nu
        self.b = 5
        self.malicious_betas = []
        self.benign_betas = []
        self._call_sequence = 0
        self.last_client_weights = None
        self.last_contribution_trace = None
        super(RFA, self).__init__()

    def __call__(self, inputs):
        self.invalidate_contributions()
        self.malicious_betas, self.benign_betas = [], []
        self._call_sequence += 1
        if not inputs:
            raise ValueError("require nonempty inputs")
        if not isinstance(inputs[0], torch.Tensor):
            raise ValueError("inputs must be tensors")
        alphas = [1 / len(inputs) for _ in inputs]
        z = torch.zeros_like(inputs[0])
        z, mal_betas, ben_betas, mix, betas, denominator = _weiszfeld(
            inputs, alphas, z=z, nu=self.nu, T=self.T, b=self.b)
        record = FinalMix(self._call_sequence, MIX_SEMANTICS,
            tuple(tensor_fingerprint(value) for value in inputs), tensor_fingerprint(z),
            tuple(z.shape), str(z.dtype), str(z.device), self.T, float(self.nu), betas, denominator, mix)
        self.malicious_betas = mal_betas
        self.benign_betas = ben_betas
        self.last_client_weights = mix
        self.last_contribution_trace = record
        return z

    def invalidate_contributions(self):
        """Used at failed/empty mandatory consumer boundaries; never fake weights."""
        self.last_client_weights = None
        self.last_contribution_trace = None

    def get_attack_stats(self):
        """Legacy/deprecated position-history means, not true identity weights."""
        average_malicious = sum(self.malicious_betas) / len(self.malicious_betas) if self.malicious_betas else 0
        average_benign = sum(self.benign_betas) / len(self.benign_betas) if self.benign_betas else 0
        return {"average_malicious_beta": average_malicious, "average_benign_beta": average_benign}
