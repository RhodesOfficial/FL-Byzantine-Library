"""Passive contribution records in model-displacement direction, no RNG/forwards."""
import math
import torch

CHANNEL_DEFINITIONS = {
    "baseline": "C_i=a_i*u_i; parallel means original client channel; residual coefficient is zero",
    "d1": "C_i=a_i*p_i+b_i*e_i; p_i/e_i are projection/residual of input-clipped model displacement",
    "comparison": "Compare actual C_i across methods, not coefficient magnitudes; channel definitions differ",
    "input_clipping": "Represented in p_i/e_i; coefficients apply to these clipped vectors, not raw u_i",
    "root": "Root direction injections belong only to C_root",
    "along_final": "Signed dot(C_i,actual_model_displacement)/norm(actual_model_displacement)^2; not a probability",
    "grouping": "True pre-flip local classes 8/9 fraction > global training-pool fraction; diagnostic only",
    "vector_format": "Raw little-endian float32, flat parameter order; every 20 rounds",
    "decomposition_epsilon": 1e-12,
}

ERROR_DEFINITIONS = {
    "diagnostic_dtype": "float64 before all subtraction, summation and norms; training remains float32",
    "d": "Actual float32 displacement supplied to parameter writeback, new-minus-old direction",
    "delta": "actual_new_parameters.float64 - old_parameters.float64",
    "layer1": "E_alg=norm(d64-hat_d64) <= 1e-12 + 1e-5*norm(d64); no rounding allowance",
    "reference": "theta_ref=float32(theta64+d64); actual new parameters must equal theta_ref elementwise",
    "rounding": "q=theta_ref64-theta64-d64, computed independently of hat_d",
    "layer2": "E_model=norm(delta-hat_d64) <= 2e-12+1e-5*norm(d64)+norm(q)",
    "relative_threshold": "layer2_absolute_bound/norm(delta), null when norm(delta)=0",
    "decomposition_error": "Report only: norm(delta-hat_d64)/(norm(delta)+1e-12); null at zero delta; never a sole failure gate",
    "direction_at_zero": "null",
}


def trace(parallel, residual, parallel_coef, residual_coef, root, final_residual):
    return {"parallel": parallel, "residual": residual,
            "parallel_coef": parallel_coef, "residual_coef": residual_coef,
            "root": root, "final_residual": final_residual}


def zero_trace(inputs):
    zero = torch.zeros_like(inputs[0])
    return trace([zero] * len(inputs), [zero] * len(inputs),
                 [0.0] * len(inputs), [0.0] * len(inputs), zero, zero)


def reconstruct64(value):
    """Contributions only; never add numerical writeback residuals to them."""
    n = len(value["parallel"])
    assert all(len(value[k]) == n for k in ("residual", "parallel_coef", "residual_coef"))
    root = value["root"].detach().double()
    assert torch.isfinite(root).all().item()
    contributions = []
    reconstructed = root.clone()
    for p, e, a, b in zip(value["parallel"], value["residual"],
                           value["parallel_coef"], value["residual_coef"]):
        a, b = float(a), float(b)
        assert math.isfinite(a) and math.isfinite(b)
        contribution = a * p.detach().double() + b * e.detach().double()
        assert torch.isfinite(contribution).all().item()
        contributions.append(contribution)
        reconstructed += contribution
    return reconstructed, contributions


def summarize(value, actual_displacement):
    """Reconstruct for reporting only; failure decisions use the two layers."""
    final = actual_displacement.detach().double()
    assert torch.isfinite(final).all().item()
    norm = final.norm().item()
    reconstructed, contributions = reconstruct64(value)
    norms = [c.norm().item() for c in contributions]
    along = [torch.dot(c, final).item() / (norm * norm) if norm > 0 else None for c in contributions]
    error = (final - reconstructed).norm().item() / (norm + 1e-12) if norm > 0 else None
    assert error is None or math.isfinite(error)
    assert all(math.isfinite(x) for x in norms)
    assert all(x is None or math.isfinite(x) for x in along)
    return {"client_parallel_coef": [float(x) for x in value["parallel_coef"]],
            "client_residual_coef": [float(x) for x in value["residual_coef"]],
            "client_contrib_norm": norms, "client_contrib_along_final": along,
            "decomposition_error": error}


def two_layer_errors(value, theta, displacement, theta_new):
    """Independent writeback reference; q never uses reconstructed contributions."""
    assert theta.dtype == displacement.dtype == theta_new.dtype == torch.float32
    assert theta.shape == displacement.shape == theta_new.shape
    theta64, d64, new64 = (x.detach().double() for x in (theta, displacement, theta_new))
    assert all(torch.isfinite(x).all().item() for x in (theta64, d64, new64))
    hat, _ = reconstruct64(value)
    reference = (theta64 + d64).float()
    q = reference.double() - theta64 - d64
    delta = new64 - theta64
    d_norm, q_norm, delta_norm = (x.norm().item() for x in (d64, q, delta))
    e_alg, e_model = (d64 - hat).norm().item(), (delta - hat).norm().item()
    bound1, bound2 = 1e-12 + 1e-5 * d_norm, 2e-12 + 1e-5 * d_norm + q_norm
    return {"E_alg": e_alg, "d_norm": d_norm, "q_norm": q_norm,
            "E_model": e_model, "delta_norm": delta_norm,
            "layer1_absolute_bound": bound1, "layer2_absolute_bound": bound2,
            "tau_rel": bound2 / delta_norm if delta_norm > 0 else None,
            "model_relative_error": e_model / delta_norm if delta_norm > 0 else None,
            "layer1_pass": e_alg <= bound1, "writeback_exact": torch.equal(theta_new, reference),
            "layer2_pass": e_model <= bound2}


def require_two_layers(checks):
    if not checks["layer1_pass"]:
        raise ValueError(f"pre-write contribution decomposition failed: {checks}")
    if not checks["writeback_exact"]:
        raise ValueError(f"actual parameter writeback differs from independent float32 reference: {checks}")
    if not checks["layer2_pass"]:
        raise ValueError(f"model contribution error exceeds independently predicted rounding bound: {checks}")


def group_cosines(value, groups):
    final = value["final_residual"].detach().double()
    length = final.norm().item()
    output = {}
    for name, positions in groups.items():
        cosine = None
        if positions and length > 0:
            mean = torch.stack([value["residual"][i].detach().double() for i in positions]).mean(0)
            norm = mean.norm().item()
            if norm > 0:
                cosine = max(-1.0, min(1.0, torch.dot(final, mean).item() / (length * norm)))
                assert math.isfinite(cosine)
        output[name] = cosine
    return output
