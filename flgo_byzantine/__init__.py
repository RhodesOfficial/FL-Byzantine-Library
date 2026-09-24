"""FLGo adapter for selected FL-Byzantine-Library attacks and aggregators.

Import this package as the ``algorithm`` argument to ``flgo.init``.  FLGo owns
the task, client training, simulator, and logging; this module owns attack
injection and robust aggregation of client parameter updates.
"""

from .algorithm import Client, Server

__all__ = ["Client", "Server"]
