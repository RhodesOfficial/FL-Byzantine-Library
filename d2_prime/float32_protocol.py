"""Explicit formal carrier adaptation. Decision rules remain TaskProtocol's.

Only the committed model evolves in float32. CPU double candidates are clipped
once from the exact values of source/local float32 parameters, then used in both
channels. The double displacement is temporary, never a hidden evolving model.
"""
from dataclasses import asdict, replace
import torch

from .protocol import TaskProtocol, SourceSnapshot
from .reference import ReferenceState, ReferenceCandidate, features, prepare_event
from aggregators.contribution_diagnostics import trace, two_layer_errors, require_two_layers


class Float32TaskProtocol(TaskProtocol):
    def __init__(self, initial_model, *args, **kwargs):
        if initial_model.dtype != torch.float32 or initial_model.device.type != 'cuda':
            raise ValueError('formal model must be GPU/float32')
        super().__init__(initial_model.detach().cpu(), *args, **kwargs)
        self._model = initial_model.detach().clone()
        self._freeze()
        self.observations, self._feature_cache = {}, {}
        self.last_checks = None

    def _freeze(self):
        self._sources[self.version] = SourceSnapshot(self.version, self._model.float().clone(),
            self._reference.mu, self._reference.sigma, self._reference.evidence, self.config_id)
        self._refs.setdefault(self.version, 0)
        self._collect_sources()

    def snapshot(self, version):
        # Public snapshots cannot mutate the internal source via a tensor alias.
        source = self._sources[version]
        return replace(source, model=source.model.clone())

    def _local_vector(self, value):
        local = torch.as_tensor(value)
        if local.dtype != torch.float32:
            raise ValueError('formal local parameters must be float32')
        return local.detach().cpu().double()

    def _source_vector(self, version):
        return self._sources[version].model.detach().cpu().double()

    def issue(self, identity):
        task = super().issue(identity)
        self.observations[task.task_id] = dict(asdict(task), first_arrival_at=None,
            staleness_arrival=None, staleness_terminal=None, terminal_at=None,
            raw_norm=None, clipped_norm=None, clip_scale=None, attempts=0,
            last_path=None, g=None, a=0., b=0., q=0., ever_scored=False,
            source_scored=False, source_ready=ReferenceState(self._sources[task.source_version].mu,
                self._sources[task.source_version].sigma,self._sources[task.source_version].evidence).ready(self.reference_config))
        return task

    def receive(self, reply, transport_identity):
        accepted = super().receive(reply, transport_identity)
        if accepted:
            raw, clipped = self._updates[reply.task_id]
            norm = raw.norm().item()
            self.observations[reply.task_id] = dict(self.observations[reply.task_id],
                first_arrival_at=self.now, staleness_arrival=self.version-reply.source_version,
                raw_norm=norm, clipped_norm=clipped.norm().item(),
                clip_scale=min(1., self.config.clip_norm/norm) if norm else 1.)
            self._feature_cache[reply.task_id] = features(clipped, self.feature_map, self.config.clip_norm)
        return accepted

    def _finish(self, task_id, state):
        self.observations[task_id] = dict(self.observations[task_id], state=state,
            terminal_at=self.now, staleness_terminal=self.version-self.tasks[task_id].source_version)
        self._feature_cache.pop(task_id, None)
        super()._finish(task_id, state)

    def candidates(self):
        return tuple(dict(task_id=i, identity=self.tasks[i].identity,
            source_version=self.tasks[i].source_version,
            staleness=self.version-self.tasks[i].source_version,
            delta=self._updates[i][0], clipped_delta=self._updates[i][1]) for i in self._buffer)

    def _prepare_reference_candidates(self, candidates):
        rows = []
        for c in candidates:
            s = self._sources[c['source_version']]
            if s.config_id != self.config_id:
                raise ValueError('source configuration mismatch')
            rows.append(ReferenceCandidate(c['task_id'], c['identity'], c['source_version'],
                ReferenceState(s.mu, s.sigma, s.evidence), self._feature_cache[c['task_id']]))
        return prepare_event(rows, self.reference, self.reference_config, self.config.capacity,
                             self.config.eta_model, self.version)

    def _commit_draft(self):
        draft = super()._commit_draft()
        draft.observations = self.observations.copy()
        draft._feature_cache = self._feature_cache.copy()
        return draft

    def _empty_displacement(self):
        return torch.zeros(self._model.numel(), dtype=torch.float64)

    def _write_model(self, displacement):
        # One conversion at the model channel boundary, no second candidate clip.
        return self._model + displacement.to(device=self._model.device, dtype=torch.float32)

    def _export_displacement(self, displacement):
        return displacement.float().clone()

    def _store_displacement(self, displacement):
        return None  # Full vector is checked live and not retained for every batch.

    def _store_candidates(self, candidates):
        return [{k:v for k,v in c.items() if k not in ('delta','clipped_delta')} for c in candidates]

    def _apply_commit_event(self):
        before_model, before_reference = self._model.clone(), self.reference.normalized()
        updates = self._updates.copy()
        result = super()._apply_commit_event()
        # Validation happens on the draft before TaskProtocol publishes anything.
        accepted = [r.task_id for r in result.receipts]
        zero = torch.zeros_like(before_model.cpu())
        value = trace([-updates[i][1] for i in accepted], [zero]*len(accepted),
            [r.a for r in result.receipts], [0.]*len(accepted), zero, zero)
        checks = two_layer_errors(value, before_model.cpu(), result.model_displacement, self._model.cpu())
        require_two_layers(checks)
        oracle_ref = torch.zeros_like(before_reference)
        receipts = {r.task_id:r for r in result.receipts}
        for p in result.event.proposals:
            self.observations[p.task_id] = dict(self.observations[p.task_id],
                attempts=self.observations[p.task_id]['attempts']+1, last_path=p.path, g=p.g,
                staleness_commit=int(round(1/p.h-1)))
            if p.g is not None:
                self.observations[p.task_id].update(ever_scored=True, source_scored=p.path=='source')
            if p.task_id in receipts:
                r = receipts[p.task_id]
                self.observations[p.task_id].update(a=r.a, b=r.b, q=r.q)
                oracle_ref += r.b*torch.tensor(p.direction, dtype=torch.float64)
        actual_ref = self.reference.normalized()-before_reference
        if not torch.allclose(actual_ref, oracle_ref, atol=1e-10, rtol=1e-8):
            raise ValueError('reference contribution reconstruction failed')
        checks['reference_max_abs_error'] = (actual_ref-oracle_ref).abs().max().item()
        self.last_checks = checks
        if result.receipts:
            self.batches[-1]['checks'] = checks
        return result
