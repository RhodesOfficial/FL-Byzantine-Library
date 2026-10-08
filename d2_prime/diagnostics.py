"""Read-only independent NumPy formula checks for phase-zero evidence.

No output from these routines is consumed by scoring, training or dispatch.
The reference oracle does not call features/prepare_event/write_reference.
"""
import math
import numpy as np


def check_batch(batch, model_before, model_after, carrier_after, reference_after, sources, protocol):
    event, rc, pc = batch["event"], protocol.reference_config, protocol.config
    fm, d = protocol.feature_map, rc.projection_buckets + 1
    proposals = {p.task_id: p for p in event.proposals}
    candidates = {c["task_id"]: c for c in batch["candidates"]}
    mu, sigma, e = np.array(event.before.mu), np.array(event.before.sigma), event.before.evidence
    xs, deltas = {}, {}
    for tid, c in candidates.items():
        delta = np.array(c["delta"], dtype=np.float64)
        norm = np.linalg.norm(delta)
        delta *= min(1., pc.clip_norm/norm) if norm else 1.
        buckets = np.zeros(rc.projection_buckets)
        np.add.at(buckets, np.array(fm.buckets), np.array(fm.signs)*delta)
        xs[tid] = np.r_[np.clip(math.sqrt(rc.projection_buckets)/pc.clip_norm*buckets, -1., 1.),
                         np.linalg.norm(delta)/pc.clip_norm]
        deltas[tid] = delta
    cold_ids = [tid for tid, p in proposals.items() if p.path == "cold"]
    if cold_ids:
        cold_rows = np.array([xs[tid] for tid in proposals])
        cold_mu = np.median(cold_rows, axis=0)
        cold_sigma = np.clip(np.median(np.abs(cold_rows-cold_mu), axis=0),
                             rc.sigma_min, 1.)
    model_delta = np.zeros_like(model_before, dtype=np.float64)
    ref_delta = np.zeros(2*d+1)
    coeff_error = 0.
    for receipt in batch["receipts"]:
        tid, p = receipt["task_id"], proposals[receipt["task_id"]]
        x = xs[tid]
        if p.path == "cold":
            z = math.sqrt(float(np.mean(((x-cold_mu)/cold_sigma)**2)))
        else:
            source = sources[candidates[tid]["source_version"]]
            z = math.sqrt(float(np.mean((x-np.array(source.mu))**2 /
                (np.array(source.sigma)**2+(rc.kappa_u*(1-source.evidence))**2))))
        g = (1-(z/rc.z_cut)**2)**2 if z < rc.z_cut else 0.
        h = 1/(1+batch["version_before"]-candidates[tid]["source_version"])
        a0, b0 = pc.eta_model*h*g/pc.capacity, rc.eta_reference*h*g/pc.capacity
        # Eligible event identities are unique. Compute balance from strictly
        # earlier batches, including same-timestamp commits, not task-id order.
        previous = []
        for earlier in protocol.batches:
            if earlier is batch:
                break
            previous.extend(earlier["receipts"])
        prior = math.fsum(r["q"] for r in previous if r["identity"] == receipt["identity"]
                         and batch["at"]-protocol.budget.config.window < r["at"] <= batch["at"])
        remaining = max(0., protocol.budget.config.limit-prior)
        lam = min(1., remaining/(a0+b0)) if a0+b0 else 0.
        coeff_error = max(coeff_error, abs(receipt["a"]-lam*a0), abs(receipt["b"]-lam*b0), abs(p.g-g))
        target_scale = np.clip(np.abs(x-mu), rc.sigma_min, 1.)
        v = np.r_[(x-mu)/math.sqrt(d), (target_scale-sigma)/math.sqrt(d), 1-e]
        norm_v = np.linalg.norm(v)
        v *= min(1., rc.clip_reference/norm_v) if norm_v else 1.
        model_delta -= receipt["a"]*deltas[tid]
        ref_delta += receipt["b"]*v
        assert np.linalg.norm(receipt["a"]*deltas[tid])/pc.clip_norm + np.linalg.norm(receipt["b"]*v)/rc.clip_reference <= receipt["q"] + 1e-10
    ref_expected = np.r_[mu/math.sqrt(d), sigma/math.sqrt(d), e] + ref_delta
    errors = dict(model=float(np.max(np.abs(np.array(model_after)-(model_before+model_delta)))),
                  carrier=float(np.max(np.abs(np.array(carrier_after)-(model_before+model_delta)))),
                  reference=float(np.max(np.abs(np.array(reference_after)-ref_expected))),
                  coefficients=coeff_error)
    assert max(errors.values()) <= 1e-10, errors
    return errors
