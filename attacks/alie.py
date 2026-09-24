from .base import _BaseByzantine
from scipy.stats import norm
import torch
import numpy as np


def craft_alie_update(benign_gradients, n, m, z=None):
    """Craft one ALIE update from the visible benign update vectors."""
    if len(benign_gradients) < 2 or not 0 < m < n:
        raise ValueError("ALIE requires at least two benign updates and 0 < m < n")
    if z is None:
        s = np.floor(n / 2 + 1) - m
        cdf_value = (n - m - s) / (n - m)
        if not 0 < cdf_value < 1:
            raise ValueError("ALIE has no finite z for this client count")
        z = norm.ppf(cdf_value)
    stacked = torch.stack(benign_gradients, dim=0)
    return stacked.mean(dim=0) - stacked.std(dim=0) * z


class alie(_BaseByzantine):
    def __init__(self,n,m,z=None,*args,**kwargs):
        super().__init__(*args, **kwargs)
        s = np.floor(n / 2 + 1) - m
        cdf_value = (n - m - s) / (n - m)
        self.z_max = norm.ppf(cdf_value)
        self.n_total = n
        self.n_malicious = m
        self.n_good = n - m
        self.alie_z_max = self.args.alie_z_max if self.args.alie_z_max is not None else self.z_max

    def omniscient_callback(self,benign_gradients):
        self.adv_momentum = craft_alie_update(
            benign_gradients, self.n_total, self.n_malicious, self.alie_z_max
        ).to(self.device)


    def local_step(self,batch):
        return None

    def train_(self, embd_momentum=None):
        return None
