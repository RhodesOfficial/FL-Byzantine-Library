from .base import _BaseByzantine


def craft_ipm_update(benign_gradients, epsilon):
    """Craft one inner-product manipulation update."""
    if not benign_gradients:
        raise ValueError("IPM requires at least one benign update")
    return -epsilon * sum(benign_gradients) / len(benign_gradients)


class IPMAttack(_BaseByzantine):
    def __init__(self, eps, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.epsilon = eps

    def omniscient_callback(self,benign_gradients):
        self.adv_momentum = craft_ipm_update(benign_gradients, self.epsilon)

    def local_step(self,batch):
        return None

    def train_(self, embd_momentum=None):
        return None
