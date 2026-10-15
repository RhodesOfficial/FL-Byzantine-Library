"""Observable-only invitation policy and authenticated metadata return consumer.

The simulator supplies observed online/return notifications; latent draws and
diagnostic probabilities are deliberately absent from this module's interface.
"""
import hashlib
import json


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def invite(plan, registered):
    chosen = tuple(plan)
    if len(chosen) != 8 or len(set(chosen)) != 8 or not set(chosen) <= set(registered):
        raise ValueError('invalid invitation')
    return chosen


class Consumer:
    def __init__(self, identity, registered, dispatched):
        self.identity = dict(identity)
        self.registered = set(registered)
        self.dispatched = dict(dispatched)
        self.seen = set()

    def accept(self, message, on_time):
        # Exact allowlist also rejects latent/diagnostic fields.
        if set(message) != set(self.identity) | {'client', 'token', 'payload'}:
            return 'schema'
        if any(message[k] != v for k, v in self.identity.items()):
            return 'identity'
        c = message['client']
        if c not in self.registered:
            return 'unregistered'
        if c not in self.dispatched:
            return 'undispatched'
        token, payload = self.dispatched[c]
        if message['token'] != token or message['payload'] != payload:
            return 'tampered'
        if token in self.seen:
            return 'duplicate_token'
        if not on_time:
            return 'late'
        self.seen.add(token)
        return 'accepted'
