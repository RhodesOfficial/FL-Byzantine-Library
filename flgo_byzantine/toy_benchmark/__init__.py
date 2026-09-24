"""Small deterministic classification benchmark for integration smoke tests.

This synthetic task is only for checking the wiring. It is not evidence of
defense quality on real federated data.
"""

from . import model as default_model


def visualize(*args, **kwargs):
    """The tiny offline task intentionally has no generated figure."""
