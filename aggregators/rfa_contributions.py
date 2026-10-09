"""Mandatory RFA consumer checks; legacy optional statistics are unrelated."""
import math
from numbers import Integral

import torch

from .contribution_diagnostics import trace, reconstruct64, two_layer_errors, require_two_layers
from .rfa import FinalMix, MIX_SEMANTICS, tensor_fingerprint


def bind_final_mix(instance, inputs, client_ids, aggregate, expected_call_id, bridge_call_id):
    """Bind trusted receipt order to the actual successful RFA call, without fallback."""
    m = len(inputs)
    ids = tuple(client_ids)
    if not m or len(ids) != m:
        raise ValueError("RFA input/identity lengths differ or are empty")
    if any(isinstance(cid, bool) or not isinstance(cid, Integral) or cid < 0 for cid in ids):
        raise ValueError("RFA requires nonnegative integer client IDs")
    ids = tuple(int(cid) for cid in ids)
    if len(set(ids)) != m:
        raise ValueError("duplicate identity in synchronous RFA batch")
    weights = instance.last_client_weights
    record = instance.last_contribution_trace
    if (not isinstance(weights, tuple) or len(weights) != m
            or not isinstance(record, FinalMix) or record.weights != weights):
        raise ValueError("missing or inconsistent mandatory RFA final weights")
    if (record.call_id != expected_call_id or record.call_id != instance._call_sequence
            or record.semantics != MIX_SEMANTICS or record.T != instance.T
            or record.nu != instance.nu):
        raise ValueError("stale RFA call or parameter/semantics mismatch")
    if (record.input_fingerprints != tuple(tensor_fingerprint(x) for x in inputs)
            or record.output_fingerprint != tensor_fingerprint(aggregate)
            or record.shape != tuple(aggregate.shape)
            or record.dtype != str(aggregate.dtype) or record.device != str(aggregate.device)):
        raise ValueError("RFA trace does not describe the actual ordered inputs/output")
    if (len(record.final_betas) != m or not math.isfinite(record.denominator)
            or record.denominator <= 0 or any(not math.isfinite(b) or b < 0 for b in record.final_betas)
            or any(not math.isfinite(w) or w < 0 for w in weights)):
        raise ValueError("invalid RFA final coefficients/denominator")
    eps = torch.finfo(aggregate.dtype).eps
    # Captured Tensor division may round in the computation dtype; do not replace it.
    tol = max(1e-10, 8*m*eps)
    if (abs(math.fsum(weights)-1) > tol
            or any(abs(w-b/record.denominator) > max(1e-10, 4*eps)*max(1, abs(w))
                   for w, b in zip(weights, record.final_betas))):
        raise ValueError("weights do not match the captured final beta normalization")
    zero = torch.zeros_like(aggregate)
    decomposition = trace(inputs, [zero]*m, [-w for w in weights], [0.]*m, zero, zero)
    hat, contributions = reconstruct64(decomposition)
    if aggregate.dtype == torch.float64:
        if not torch.allclose(-aggregate.detach().double(), hat, atol=1e-10, rtol=1e-8):
            raise ValueError("RFA aggregate reconstruction failed (float64)")
    elif aggregate.dtype == torch.float32:
        error = (-aggregate.detach().double()-hat).norm().item()
        if error > 1e-12 + 1e-5*aggregate.detach().double().norm().item():
            raise ValueError("RFA aggregate reconstruction failed (float32)")
    else:
        raise ValueError("RFA bridge has registered numerical checks only for float32/float64")
    return {
        "bridge_call_id": bridge_call_id, "rfa_call_id": record.call_id,
        "semantics": MIX_SEMANTICS, "T": record.T, "nu": record.nu,
        "input_direction": "server_parameters-minus-client_parameters",
        "model_displacement": "minus-aggregate; C_i=-w_i*u_i",
        "aggregate_reconstruction_error": (-aggregate.detach().double()-hat).norm().item(),
        "final_betas": list(record.final_betas), "denominator": record.denominator,
        "clients": [{"position": i, "client_id": cid, "weight": w,
                     "model_coefficient": -w, "input_fingerprint": record.input_fingerprints[i],
                     "contribution_norm": contributions[i].norm().item()}
                    for i, (cid, w) in enumerate(zip(ids, weights))],
    }, decomposition


def verify_model_writeback(decomposition, theta, aggregate, theta_new):
    """Use independent rounding q, never a fitted residual assigned to clients."""
    displacement = -aggregate
    if theta.dtype == aggregate.dtype == theta_new.dtype == torch.float32:
        checks = two_layer_errors(decomposition, theta, displacement, theta_new)
        require_two_layers(checks)
        return checks
    if theta.dtype == aggregate.dtype == theta_new.dtype == torch.float64 and theta.device.type == "cpu":
        hat, _ = reconstruct64(decomposition)
        reference = theta.detach() + displacement.detach()
        delta = theta_new.detach() - theta.detach()
        if (not torch.allclose(displacement, hat, atol=1e-10, rtol=1e-8)
                or not torch.equal(theta_new, reference)
                or not torch.allclose(delta, hat, atol=1e-10, rtol=1e-8)):
            raise ValueError("RFA float64 model writeback/reconstruction failed")
        return {"E_alg": (displacement-hat).norm().item(), "E_model": (delta-hat).norm().item(),
                "writeback_exact": True, "atol": 1e-10, "rtol": 1e-8}
    raise ValueError("unregistered RFA model writeback dtype/device")
