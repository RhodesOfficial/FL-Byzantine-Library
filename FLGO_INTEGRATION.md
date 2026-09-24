# FLGo integration

`easyFL/` is the FLGo source checkout (currently
`14a977c2ee7c7ead392cf8fba5502099d220ee4a` from
`https://github.com/RhodesOfficial/easyFL`). The adapter in `flgo_byzantine/`
uses FLGo for tasks, client training, virtual availability and latency,
evaluation, and JSON records. It uses the FL-Byzantine-Library's tensor
aggregation implementations and ALIE/IPM attack formulas. The adapter
does not modify the FLGo checkout. The checkout is ignored by this
repository so it remains independently versioned; clone it into
`easyFL/` if it is absent.

## Install

Use one Python environment with the dependencies from both projects:

```powershell
python -m pip install -r requirements.txt
python -m pip install -r easyFL/requirements.txt
```

Run from the repository root. The launch script adds the local `easyFL/`
checkout to Python's import path, so a separate `flgo` installation is
unnecessary. Dataset generation may download MNIST.

## First experiment

```powershell
python run_flgo_byzantine.py --task ./toy_10 --create-toy --clients 10 --aggregator avg --attack none --rounds 2
python run_flgo_byzantine.py --task ./mnist_20 --create-mnist --clients 20 --aggregator avg --attack none --rounds 2
python run_flgo_byzantine.py --task ./mnist_20 --aggregator krum --attack alie --malicious-fraction 0.2 --assumed-count 4 --rounds 2
python run_flgo_byzantine.py --task ./mnist_dir20 --create-mnist --partition dirichlet --alpha 0.5 --clients 20 --aggregator tm --attack ipm --malicious-fraction 0.2 --assumed-count 2
```

The toy task runs offline and checks integration only; use a real dataset
and multiple seeds for research conclusions.

Use an existing FLGo task by providing its directory with `--task` and
omitting `--create-mnist`. FLGo writes its usual records under
`<task>/record/`; the custom logger also records the received and
malicious-client counts and distance from the aggregated update to the
mean of received benign updates. This latter quantity is an oracle
diagnostic for experiments, not information supplied to the defense.
Record names include the attack, defense, assumed malicious count,
malicious fraction, and a short hash of all bridge options to keep
different scenarios separate.

## Supported options and assumptions

| Option | Values | Notes |
| --- | --- | --- |
| `--aggregator` | `avg`, `cm`, `tm`, `krum`, `cc`, `rfa`, `sign` | Uses the corresponding library class. |
| `--attack` | `none`, `alie`, `ipm` | ALIE and IPM use library formulas and full knowledge of benign updates in the received round. |
| `--malicious-fraction` | `[0, 1)` | Malicious client identities are sampled once from all task clients using `--seed`. |
| `--assumed-count` | nonnegative integer | Defense's assumed Byzantine bound **among received updates**; required for `tm` and `krum`. It is independent of the actual count. |
| `--proportion` | `(0, 1]` | FLGo samples this fraction of clients per round. |

When `--attack none`, no clients are marked malicious, regardless of
`--malicious-fraction`. For `sign`, the server applies the FLGo learning
rate to the aggregated sign vector, matching the library's update scale.

The adapter defines an update as `server parameters - locally trained
parameters`; the library aggregate is subtracted from server parameters.
This makes `avg` equivalent to uniform FedAvg on trainable parameters.
Non-parameter buffers retain their server values. For models relying on
BatchNorm running statistics, use an architecture with local/group
normalization or extend the buffer policy before drawing conclusions.

`tm` needs more than `2*f` received updates. Multi-Krum needs at least
`2*f+3`. The adapter raises an error if a round violates these constraints
instead of silently changing the defense. ALIE requires at least two
benign response and a finite attack scale. The defense never receives
malicious identity labels; these are used only to inject simulated
attacks and record participation. Some original library diagnostic
statistics assume malicious updates occupy the last vector positions,
so they are deliberately not reported by this adapter.

## Adding methods

`flgo_byzantine/algorithm.py` has two extension points:

1. `_build_aggregator` maps a tensor-based library aggregator to FLGo
   update vectors. State-dependent aggregators should retain their
   instance across rounds.
2. `_attack_update` crafts a vector from received benign vectors. Record
   the attacker's actual information before adding limited-knowledge or
   adaptive attacks.

The present bridge is synchronous. FLGo's `asyncbase.py` and simulator
provide the event and delay foundation for BRAFed-like work, but a
separate asynchronous server adapter must define stale-update handling
and evaluation before claiming a BRAFed reproduction.

## Offline integration check

With the project dependencies installed, run:

```powershell
python -m unittest discover -s tests -p test_flgo_bridge.py
```

The test creates a temporary synthetic FLGo task, checks that the bridge's
ordinary averaging matches native FedAvg, and runs an ALIE/Krum scenario
through FLGo's trainer, simulator, and JSON logger.
