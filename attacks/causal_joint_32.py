"""causal_joint_32_v1: finite-budget causal white-box joint time-vector attacker.

Registered contract (D2_PRIME_PHASE3_0_3_1_RULING Q2/Q3): per qualifying malicious
task, exactly 8 upload vectors (d in {1,2}, gamma in {0,0.5,1,4}) crossed with 4
timing actions (immediate / +4 / +8 / expire) = 32 joint candidates, each scored by
one 32-tick causal proxy trajectory and the class-balanced CE on the attacker's own
optimization data. At most one gradient of the published model per decision.

The attacker only reads what Q1 permits: the published model vector, the visible
arrived-update mean it is handed, its own optimization data, and the public bound
B_M. It never receives slow/fast lists, dispatch/delay seeds, or future state.
"""
import math

import torch
import torch.nn.functional as F

REGISTERED_NAME = "causal_joint_32_v1"
DIRECTION_EPS = 1e-12
GAMMAS = (0.0, 0.5, 1.0, 4.0)
DIRECTIONS = (1, 2)
TIMINGS = ("immediate", "delay4", "delay8", "expire")
TIMING_RANK = {"immediate": 0, "delay4": 1, "delay8": 2, "expire": 3}


def _unit(vector):
    norm = vector.detach().double().norm().item()
    if not math.isfinite(norm) or norm <= DIRECTION_EPS:
        return None, norm
    return vector/vector.norm(), norm


def clip_to_cap(vector, cap):
    norm = vector.detach().double().norm().item()
    if norm <= cap:
        return vector
    return vector*(cap/vector.norm())


class CausalJoint32Attacker:
    def __init__(self, opt_images, opt_labels, present_classes, B_M, scratch_model, device):
        if opt_images.shape[0] != opt_labels.shape[0] or opt_images.shape[0] == 0:
            raise ValueError("attacker needs a non-empty aligned optimization set")
        if opt_images.shape[0] > 60:
            raise ValueError("optimization set must not exceed 60 samples")
        # float64 scratch model so a destroyed (huge-logit) proxy model still yields a
        # finite ranked loss instead of a float32 overflow; the attacker then ranks any
        # residual non-finite candidate last and avoids pushing the model into overflow.
        self.device = device
        self.images = opt_images.to(device).double()
        self.labels = opt_labels.to(device)
        self.present_classes = sorted(int(c) for c in present_classes)
        self.B_M = float(B_M)
        self.cap = 10.0*float(B_M)
        self.model = scratch_model.to(device).double()
        self.gradient_count = 0
        self.candidate_count = 0

    def _load(self, vector):
        offset = 0
        with torch.no_grad():
            for p in self.model.parameters():
                size = p.numel()
                p.copy_(vector[offset:offset+size].reshape(p.shape))
                offset += size
        if offset != vector.numel():
            raise ValueError("parameter dimension mismatch loading attacker scratch model")

    def _class_balanced_ce(self, logits):
        per_class = []
        ce = F.cross_entropy(logits, self.labels, reduction="none")
        for cls in self.present_classes:
            mask = self.labels == cls
            per_class.append(ce[mask].mean())
        return torch.stack(per_class).mean()

    def grad_direction(self, published_vector):
        """One class-balanced CE gradient of the published model; unit direction."""
        self._load(published_vector)
        self.model.train(False)
        for p in self.model.parameters():
            p.grad = None
        logits = self.model(self.images)
        loss = self._class_balanced_ce(logits)
        loss.backward()
        grad = torch.cat([p.grad.detach().reshape(-1) for p in self.model.parameters()]).float()
        for p in self.model.parameters():
            p.grad = None
        self.gradient_count += 1
        unit, norm = _unit(grad)  # Unit is float32 so candidate vectors stay float32.
        return unit, norm, float(loss.detach().item())

    def resolve_directions(self, mu_vis, grad_unit, normal_diff):
        v1, n1 = _unit(mu_vis)
        v2 = grad_unit
        vn, nn_ = _unit(normal_diff)
        resolved = {}
        for d, chain in ((1, (("mu_vis", v1), ("grad", v2), ("normal_diff", vn))),
                         (2, (("grad", v2), ("mu_vis", v1), ("normal_diff", vn)))):
            chosen = None
            for source, vec in chain:
                if vec is not None:
                    chosen = (source, vec)
                    break
            resolved[d] = chosen  # None means every fallback direction was degenerate.
        return resolved, {"mu_vis_norm": n1, "normal_diff_norm": nn_}

    def build_candidates(self, mu_vis, resolved):
        """Eight registered upload vectors u = clip_{10 B_M}(mu_vis - gamma*B_M*v_d)."""
        candidates = []
        for d in DIRECTIONS:
            chosen = resolved[d]
            for gamma in GAMMAS:
                if gamma == 0.0 or chosen is None:
                    vector = clip_to_cap(mu_vis.clone(), self.cap)
                    source = "mu_vis_only" if gamma == 0.0 else "degenerate_zero_direction"
                else:
                    source, unit = chosen
                    vector = clip_to_cap(mu_vis - gamma*self.B_M*unit, self.cap)
                candidates.append({"d": d, "gamma": gamma, "vector": vector,
                                   "direction_source": source,
                                   "vector_norm": float(vector.detach().double().norm().item())})
                self.candidate_count += 1
        return candidates

    def adv_loss(self, model_vector):
        self._load(model_vector)
        self.model.train(False)
        with torch.no_grad():
            logits = self.model(self.images)
            loss = self._class_balanced_ce(logits)
        return float(loss.item())

    @staticmethod
    def select(scored):
        """Maximize L_adv; ties -> earlier release, smaller gamma, smaller direction.

        Candidates whose L_adv is non-finite are ranked last so a legal finite score
        always wins; the caller reports search deactivation if none are finite.
        """
        def key(item):
            finite = math.isfinite(item["L_adv"])
            return (0 if finite else 1, -item["L_adv"] if finite else 0.0,
                    TIMING_RANK[item["effective_action"]], item["gamma"], item["d"])
        return min(range(len(scored)), key=lambda i: key(scored[i]))
