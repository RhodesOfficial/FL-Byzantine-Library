"""Synchronous FLGo bridge to FL-Byzantine-Library tensor aggregators.

An update is ``server_parameter - trained_client_parameter``.  This matches
the gradient direction used by the original library.  After aggregating the
updates, we subtract the result from the server model.  All options beginning
with ``byz_`` are supplied through FLGo's regular option dictionary.
"""

from __future__ import annotations

import copy
from typing import Sequence

import numpy as np
import torch

from flgo.algorithm.fedbase import BasicClient, BasicServer

from aggregators.clipping import Clipping
from aggregators.cm import CM
from aggregators.fedavg import fedAVG
from aggregators.krum import Krum
from aggregators.rfa import RFA
from aggregators.sign_sgd import SignSGD
from aggregators.trimmed_mean import TM
from attacks.alie import craft_alie_update
from attacks.ipm import craft_ipm_update


AGGREGATORS = frozenset({"avg", "cm", "tm", "krum", "cc", "rfa", "sign"})
ATTACKS = frozenset({"none", "alie", "ipm"})


def _parameter_vector(model: torch.nn.Module) -> torch.Tensor:
    parameters = list(model.parameters())
    if not parameters:
        raise ValueError("FLGo model has no parameters to aggregate")
    return torch.nn.utils.parameters_to_vector(parameters).detach()


def _model_from_update(model: torch.nn.Module, update: torch.Tensor) -> torch.nn.Module:
    result = copy.deepcopy(model)
    parameters = list(result.parameters())
    with torch.no_grad():
        current = torch.nn.utils.parameters_to_vector(parameters)
        if update.numel() != current.numel():
            raise ValueError("aggregator output length does not match model parameters")
        torch.nn.utils.vector_to_parameters(current - update.to(current), parameters)
    return result


def _build_aggregator(name: str, n: int, f: int, option: dict):
    if name not in AGGREGATORS:
        raise ValueError(f"unsupported byz_aggregator {name!r}; choose {sorted(AGGREGATORS)}")
    if name == "avg":
        return fedAVG()
    if name == "cm":
        return CM()
    if name == "sign":
        return SignSGD()
    if name in {"tm", "krum"} and f <= 0:
        raise ValueError(f"{name} requires byz_assumed_count > 0")
    if name == "tm":
        if 2 * f >= n:
            raise ValueError("trimmed mean requires more than 2*f received updates")
        return TM(b=f)
    if name == "krum":
        if n < 2 * f + 3:
            raise ValueError("multi-Krum requires at least 2*f+3 received updates")
        return Krum(n=n, f=f, m=n - f - 2)
    if name == "cc":
        return Clipping(tau=float(option.get("byz_clip_tau", 1.0)), b=f)
    return RFA(T=int(option.get("byz_rfa_steps", 5)),
               nu=float(option.get("byz_rfa_nu", 1e-6)))


def _attack_update(name: str, benign: Sequence[torch.Tensor], n: int,
                   m: int, option: dict) -> torch.Tensor:
    if name == "alie":
        z = option.get("byz_alie_z")
        return craft_alie_update(benign, n, m, None if z is None else float(z))
    if name == "ipm":
        return craft_ipm_update(benign, float(option.get("byz_ipm_epsilon", 1.0)))
    raise ValueError(f"unsupported byz_attack {name!r}; choose {sorted(ATTACKS)}")


class Server(BasicServer):
    """FLGo server that evaluates library defenses against library attacks."""

    def initialize(self):
        self.byz_aggregator = str(self.option.get("byz_aggregator", "avg")).lower()
        self.byz_attack = str(self.option.get("byz_attack", "none")).lower()
        if self.byz_aggregator not in AGGREGATORS or self.byz_attack not in ATTACKS:
            raise ValueError(f"supported aggregators: {sorted(AGGREGATORS)}; attacks: {sorted(ATTACKS)}")
        self.byz_assumed_count = int(self.option.get("byz_assumed_count", 0))
        if self.byz_assumed_count < 0:
            raise ValueError("byz_assumed_count must be nonnegative")
        ratio = float(self.option.get("byz_malicious_fraction", 0.0))
        if not 0 <= ratio < 1:
            raise ValueError("byz_malicious_fraction must be in [0, 1)")
        rng = np.random.default_rng(int(self.option.get("byz_seed", self.option["seed"])))
        count = int(ratio * self.num_clients) if self.byz_attack != "none" else 0
        self.byz_malicious_ids = frozenset(int(x) for x in rng.choice(
            self.num_clients, count, replace=False))
        self.byz_last_round = {}
        self._byz_aggregator_instance = None
        self._byz_aggregator_shape = None

    def iterate(self):
        self.selected_clients = self.sample()
        received = self.communicate(self.selected_clients)
        models = received.get("model", [])
        if not models:
            self.byz_last_round = {"received": 0, "malicious": 0}
            return False
        self.model = self.aggregate(models)
        return True

    def aggregate(self, models: list, *args, **kwargs):
        if not models:
            return self.model
        if len(models) != len(self.received_clients):
            raise ValueError("FLGo received-client IDs do not match returned models")
        base = _parameter_vector(self.model)
        updates = [base - _parameter_vector(m).to(base) for m in models]
        if any(not torch.isfinite(v).all().item() for v in updates):
            raise ValueError("received non-finite client update")
        malicious_positions = [i for i, cid in enumerate(self.received_clients)
                               if cid in self.byz_malicious_ids]
        malicious_set = set(malicious_positions)
        benign = [v for i, v in enumerate(updates) if i not in malicious_set]
        if malicious_positions and self.byz_attack != "none":
            crafted = _attack_update(self.byz_attack, benign, len(updates),
                                     len(malicious_positions), self.option)
            for i in malicious_positions:
                updates[i] = crafted.clone()
        n = len(updates)
        f = self.byz_assumed_count
        shape_key = (self.byz_aggregator,
                     n if self.byz_aggregator == "krum" else None, f)
        if self._byz_aggregator_shape != shape_key:
            self._byz_aggregator_instance = _build_aggregator(
                self.byz_aggregator, n, f, self.option)
            self._byz_aggregator_shape = shape_key
        aggregate = self._byz_aggregator_instance(updates)
        if aggregate.shape != base.shape or not torch.isfinite(aggregate).all().item():
            raise ValueError("aggregator returned an invalid update")
        if self.byz_aggregator == "sign":
            aggregate = aggregate * float(self.option.get(
                "byz_server_step", self.option["learning_rate"]))
        benign_error = (aggregate - torch.stack(benign).mean(dim=0)).norm().item() if benign else None
        self.byz_last_round = {"received": n, "malicious": len(malicious_positions),
                               "assumed_malicious": f, "attack": self.byz_attack,
                               "aggregator": self.byz_aggregator,
                               "benign_mean_error_norm": benign_error}
        return _model_from_update(self.model, aggregate)


Client = BasicClient
