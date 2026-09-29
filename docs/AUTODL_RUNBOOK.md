# AutoDL 运行 D1 完整实验

资源环境只区分本地 8GB 与 AutoDL 云端；云端可选单张 RTX 4090/4090D 24GB、至少 8 个 CPU 逻辑核心、32GB 内存和 50GB 数据盘。当前 `--all` 串行使用一张 GPU。租用时优先选 PyTorch 2.5.1 / Python 3.12 / CUDA 12.4 平台镜像。原 4090D 25–60 小时估算未经 CIFAR-100 实测，可能超出；实例报价以 AutoDL 页面为准。实际性能记录及本地启动方式见 [D1_FULL_EXPERIMENT.md](D1_FULL_EXPERIMENT.md)。

## 本地 Windows PowerShell

在本仓库确认脚本已提交，然后由仓库所有者手动推送：

```powershell
git status --short --branch
git push origin feature/d1-category-coverage
```

从 AutoDL 控制台复制实例的 SSH 主机和端口，替换以下两个值。端口不是固定的 22：

```powershell
$SshHost = 'YOUR_AUTODL_SSH_HOST'
$SshPort = 12345
ssh -p $SshPort "root@$SshHost"
```

实例开始运行后，可新开一个本地 PowerShell 窗口持续看日志；按 Ctrl+C 只停止本地查看：

```powershell
& .\scripts\watch_autodl.ps1 -SshHost $SshHost -Port $SshPort -Action follow
& .\scripts\watch_autodl.ps1 -SshHost $SshHost -Port $SshPort -Action status
& .\scripts\watch_autodl.ps1 -SshHost $SshHost -Port $SshPort -Action gpu
```

不用脚本也可直接运行：

```powershell
ssh -p $SshPort "root@$SshHost" "tail -n 80 -F /root/autodl-tmp/FL-Byzantine-Library/outputs/d1_3b/run.log"
```

若 PowerShell 禁止运行本地脚本，可只用上述原生 `ssh` 命令，或仅对本次进程使用 `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\watch_autodl.ps1 -SshHost $SshHost -Port $SshPort -Action follow`。

## 云端 AutoDL Bash

以下命令在 SSH 登录后的云端终端运行。仓库 URL 和目录名可按实际修改；脚本会从自身位置推导项目目录。

```bash
cd /root/autodl-tmp
git clone --branch feature/d1-category-coverage --single-branch \
  https://github.com/RhodesOfficial/FL-Byzantine-Library.git FL-Byzantine-Library
cd /root/autodl-tmp/FL-Byzantine-Library
git branch --show-current
git log -1 --oneline
git status --short
```

若已有克隆，只在实验未运行时更新：

```bash
cd /root/autodl-tmp/FL-Byzantine-Library
git fetch origin feature/d1-category-coverage
git switch feature/d1-category-coverage
git pull --ff-only origin feature/d1-category-coverage
```

### 首选：复用镜像自带的 PyTorch

**以下步骤统一使用 `AUTODL_ENV_MODE=image`。**脚本先核验镜像自带的 PyTorch 2.5.1、torchvision 0.20.1、CUDA 12.4 和 GPU，再在数据盘建立继承镜像包的轻量 venv；其余 D1 依赖仍需安装，但不会重复下载 PyTorch/CUDA 大包。`nvidia-smi` 显示的 CUDA 版本是驱动能力，可以高于 PyTorch 的 12.4 运行时。

```bash
cd /root/autodl-tmp/FL-Byzantine-Library
AUTODL_ENV_MODE=image bash scripts/autodl_experiment.sh setup
test -x /root/autodl-tmp/venvs/flbyz-image/bin/python
AUTODL_ENV_MODE=image bash scripts/autodl_experiment.sh check
```

`check` 预期出现 `ENV_MODE=image`、`CUDA available=True` 和 GPU 名称。以后每次调用 `data-d1`、`verify-d1-offline`、`run-d1`、`summary-d1` 也必须带该前缀，尤其是放入 tmux/nohup 的命令；漏掉会回到默认独立环境，可能出现 `ModuleNotFoundError: prettytable`。

### 备选：独立 Conda 环境

若基础镜像版本与上述要求不符，独立模式会在数据盘另建 Conda 环境，并下载指定的 PyTorch 2.5.1/cu124 包。这是预期行为，PyTorch wheel 与 cuDNN 合计下载量可超过 1.5GB；不会自动复用镜像的基础包。镜像模式已经跑通时无需执行这一套。

```bash
cd /root/autodl-tmp/FL-Byzantine-Library
bash scripts/autodl_experiment.sh setup
bash scripts/autodl_experiment.sh check
```

两种环境使用不同 Python 目录，不能交叉运行。若选用独立模式，后续示例命令统一去掉 `AUTODL_ENV_MODE=image` 前缀；若选用镜像模式，则始终保留该前缀。镜像模式依赖系统盘上的基础镜像；更换镜像后重新运行 `setup` 与 `check`。

FLGo 的实际数据目录由 `easyFL/flgo/benchmark/__init__.py` 中的 `data_root` 决定，默认是仓库内的 `easyFL/flgo/benchmark/RAW_DATA`。本仓库放在 `/root/autodl-tmp`，因此原始数据也在数据盘。优先使用下面的 AutoDL 公开数据并离线校验；若不使用公开数据，执行 `data-d1` 下载/校验原始 CIFAR-10、CIFAR-100。任何下载或校验失败都必须修复，不跳过数据集。

```bash
readlink -f easyFL/flgo/benchmark/RAW_DATA
df -h /root/autodl-tmp
AUTODL_ENV_MODE=image bash scripts/autodl_experiment.sh data-d1
```

预期出现 `CIFAR10_READY train=50000 test=10000` 与 `CIFAR100_READY train=50000 test=10000`。CIFAR-LT 由实验代码从原始训练集生成，无需另外下载。数据目录被 `.gitignore` 排除。

### 使用 AutoDL 公开数据（若目录中确有原始 CIFAR-10/100）

在 AutoDL 控制台的「公开数据」中分别搜索 CIFAR-10 和 CIFAR-100，记录各自的**实例内实际路径和文件格式**。本次实例实测路径见下方；新实例如路径不同，以 `test -f` 的实际结果为准。公开数据挂载通常只读，应将原始压缩包解压到 `/root/autodl-tmp` 的 FLGo 数据目录。切勿把已做长尾划分、重排标签或改为图片文件夹格式的数据当作原始 CIFAR 输入。

若公开数据是原版 `cifar-10-python.tar.gz` 和 `cifar-100-python.tar.gz`，先核对路径与压缩包内容，再分别解压。压缩包内应有 `cifar-10-batches-py/`、`cifar-100-python/` 顶层目录：

```bash
PUBLIC_C10_ARCHIVE='/root/autodl-pub/cifar-10/cifar-10-python.tar.gz'
PUBLIC_C100_ARCHIVE='/root/autodl-pub/cifar-100/cifar-100-python.tar.gz'
test -f "$PUBLIC_C10_ARCHIVE" && test -f "$PUBLIC_C100_ARCHIVE"
tar -tzf "$PUBLIC_C10_ARCHIVE" | head
tar -tzf "$PUBLIC_C100_ARCHIVE" | head
DATA_ROOT='/root/autodl-tmp/FL-Byzantine-Library/easyFL/flgo/benchmark/RAW_DATA'
mkdir -p "$DATA_ROOT/CIFAR10" "$DATA_ROOT/CIFAR100"
tar -xzf "$PUBLIC_C10_ARCHIVE" -C "$DATA_ROOT/CIFAR10"
tar -xzf "$PUBLIC_C100_ARCHIVE" -C "$DATA_ROOT/CIFAR100"
cd /root/autodl-tmp/FL-Byzantine-Library
AUTODL_ENV_MODE=image bash scripts/autodl_experiment.sh verify-d1-offline
```

若公开数据已经是上述两个解压后的目录，则将它们复制到对应的 `CIFAR10/`、`CIFAR100/` 下，再运行 `verify-d1-offline`。校验成功应输出 `CIFAR10_OFFLINE_READY train=50000 test=10000` 和 `CIFAR100_OFFLINE_READY train=50000 test=10000`。该检查使用 `download=False`，缺文件或校验错误就停止，不会联网补救。校验通过后运行 `run-d1`；其 `download=True` 加载器会识别完整有效的本地文件并复用，日志中的 `Files already downloaded and verified` 表示**没有重新下载**。若格式或校验值不匹配，先确认公开数据版本和目录，不能静默替换科学设计中的原始 CIFAR。

### 推荐：tmux

```bash
command -v tmux || { apt-get update && apt-get install -y tmux; }
cd /root/autodl-tmp/FL-Byzantine-Library
tmux new-session -d -s d1full \
  'cd /root/autodl-tmp/FL-Byzantine-Library && AUTODL_ENV_MODE=image bash scripts/autodl_experiment.sh run-d1'
tmux ls
tail -n 80 -F outputs/d1_3b/run.log
```

`run-d1` 在启动训练前再次校验环境和两套数据，将 stdout 与 stderr 一并追加到 `outputs/d1_3b/run.log`，以选定环境的绝对 Python 路径加 `-u` 运行。断开 SSH 后 tmux 中的进程继续运行。不要在外层 shell 设置模式后就省略 tmux 命令**内部**的 `AUTODL_ENV_MODE=image`。

### 备选：nohup

与 tmux 二选一，不要同时启动两个完整实验。

```bash
cd /root/autodl-tmp/FL-Byzantine-Library
mkdir -p outputs/d1_3b
nohup env AUTODL_ENV_MODE=image bash scripts/autodl_experiment.sh run-d1 \
  > outputs/d1_3b/launcher.log 2>&1 < /dev/null &
echo $! > outputs/d1_3b/launcher.pid
tail -n 80 -F outputs/d1_3b/run.log
```

`launcher.log` 收集日志初始化前的错误；实验主体的双流日志在 `run.log`。脚本用 `flock` 防止同一输出目录的重复运行。

## 运行检查和恢复

```bash
cd /root/autodl-tmp/FL-Byzantine-Library
bash scripts/autodl_experiment.sh status
nvidia-smi
ps -ef | grep '[r]un_d1_full.py'
tail -n 80 outputs/d1_3b/run.log
cat outputs/d1_3b/last_exit_code
AUTODL_ENV_MODE=image bash scripts/autodl_experiment.sh summary-d1
```

`D1_3B_UNIT_OK index=...` 表示一个完整单元完成，`last_exit_code` 为 0 表示脚本正常退出；完整结果应为 `D1_3B_SUMMARY_OK completed=100/100`。程序中断后再次运行同一 `run-d1` 命令，已有且匹配计划的报告会跳过；正在执行但尚未写出报告的单元会从头重跑。租用实例关机或释放前，请将重要报告备份到本地或可靠存储。

有意停止时，在云端另一个终端执行 `tmux send-keys -t d1full C-c`，然后运行 `bash scripts/autodl_experiment.sh status`，确认 `run_d1_full.py` 进程已退出。只对 `tail -F` 按 Ctrl+C **不会停止训练**。已完成的报告保留，但没有轮内检查点。按量计费实例关机结束 GPU 计费，关机不等于释放；普通容器实例连续关机 15 天会被释放并清空数据。GPU 型号不能用只调 GPU 数量的“升降配置”按钮直接替换。参考 [AutoDL 计费](https://www.autodl.com/docs/price/)、[数据保留](https://www.autodl.com/docs/instance_data/)和[升降配置](https://www.autodl.com/docs/update_config/)。

## 本次实际问题记录（2026-09-29）

| 现象 | 检查与处理 |
|---|---|
| 选了 PyTorch 镜像，`setup` 却下载约 908MB torch、665MB cuDNN | 执行了默认独立 Conda 模式；新环境不会共享镜像包。用 `AUTODL_ENV_MODE=image bash scripts/autodl_experiment.sh setup` 复用已核验镜像。其余依赖仍可能下载；不要在两种模式间混用。 |
| `IMAGE_TORCH_OK` 后报 `.../venvs/flbyz-image/bin/python: No such file or directory` | 旧版脚本把 `venv` 建在错误的 `bin/` 下，已在提交 `8a070e49` 修复。停止实验后 `git pull --ff-only`，再运行镜像模式 `setup`；确认 `test -x /root/autodl-tmp/venvs/flbyz-image/bin/python`。 |
| `data-d1` 报 `ModuleNotFoundError: prettytable` | 镜像环境装好了，但命令漏了 `AUTODL_ENV_MODE=image`，回到未装完的默认独立环境。先运行 `AUTODL_ENV_MODE=image bash scripts/autodl_experiment.sh check`，再对 `data-d1` 或 `verify-d1-offline` 加同样前缀。 |
| `torch.cuda.reset_peak_memory_stats` 报 `RuntimeError: Invalid device argument` | 旧版 D1 在首次 CUDA 分配前重置统计，已在提交 `1ddf2977` 修复。停机后更新到该提交或更高版本再恢复；已生成任务和完整单元报告可复用。 |
| 任务生成后警告 `has no attribute 'visualize'` | FLGo 可视化钩子未提供；若紧接着出现 `Task ... has been successfully generated` 且轮次推进，此警告不影响训练。不要把它当作后续 Traceback 的原因。 |
| `Files already downloaded and verified` 重复出现 | torchvision 完整性校验提示，不是再次下载。公开数据先用 `verify-d1-offline` 的 `download=False` 确认两套 `*_OFFLINE_READY`，再启动实验。 |
| CIFAR 缺失、下载超时或校验失败 | 查看 `run.log`，核对 `/root/autodl-pub` 实际文件、解压顶层目录和 `RAW_DATA`；运行带模式前缀的 `verify-d1-offline`。若选择网络下载，运行带模式前缀的 `data-d1` 并在失败后修复重试；不跳过数据集。 |
| `nvidia-smi` 显示 CUDA 13.2，但镜像 PyTorch 是 cu124 | 前者为驱动支持的 CUDA 版本，后者为 PyTorch 运行时；以 `check` 的 CUDA 可用性和运行结果判断，不要求数字完全相同。 |
| GPU 利用率低、显存约 1.16GB | 首个 CIFAR-10 D1 单元 60 秒采样平均利用率 3.4%；完整报告每轮 3.164 秒，其中根聚合 2.512 秒（约 79%），PyTorch 峰值预留 0.703 GiB。主要时间在 D1 根计算，不能据此断言 CIFAR-100 或全部 100 单元都适合 8GB；须测代表单元。 |
| CUDA 不可用、GPU 号错误 | 运行 `nvidia-smi` 与带模式前缀的 `check`；确认镜像版本和 GPU 号。脚本不会退到 CPU。 |
| 其他 `ModuleNotFoundError` 或依赖冲突 | 确认 `ENV_MODE=image` 与 `PYTHON_BIN=/root/autodl-tmp/venvs/flbyz-image/bin/python`，在同一模式重跑 `setup`，再用该绝对 Python 路径执行 `-m pip check`。 |
| SSH 断线 | 重连后查看 `tmux ls` 或 `status` 和日志；不要因本地连接断开而重复启动。 |
| 日志暂时无新内容 | 查看 `ps -ef`、`nvidia-smi`、`stat outputs/d1_3b/run.log`、`launcher.log`；首轮下载、任务生成或长轮计算可能间隔较久，程序用 `-u` 输出。 |
| 磁盘不足 | 运行 `df -h /root/autodl-tmp`；环境、下载数据、实验输出都在数据盘，按需要扩容数据盘。 |

复用到其他创新点时，可设置不同的 `OUTPUT_DIR` 并使用 `bash scripts/autodl_experiment.sh run <entrypoint.py> [arguments...]`；该通用入口不会修改 D1 的科学参数，也不会替其他实验准备数据。
