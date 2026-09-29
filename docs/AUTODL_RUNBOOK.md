# AutoDL 运行 D1 完整实验

推荐单张 RTX 4090D 24GB、至少 8 个 CPU 逻辑核心、32GB 内存和 50GB 数据盘；当前 `--all` 串行使用一张 GPU。租用时选 PyTorch 2.5.1 / Python 3.12 / CUDA 12.4 镜像。已有估算为 25–60 小时，实际以首个完整单元的 `seconds_per_round` 重估。实例报价以 AutoDL 页面为准。

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

创建数据盘上的 Conda 环境并安装已核对的 D1 依赖。脚本会验证 CUDA 和 100 单元计划；依赖失败即停止。

```bash
cd /root/autodl-tmp/FL-Byzantine-Library
bash scripts/autodl_experiment.sh setup
source /root/miniconda3/etc/profile.d/conda.sh
conda activate /root/autodl-tmp/conda/envs/flbyz312
"$CONDA_PREFIX/bin/python" -c 'import torch; print(torch.__version__, torch.cuda.is_available())'
bash scripts/autodl_experiment.sh check
```

FLGo 的实际数据目录由 `easyFL/flgo/benchmark/__init__.py` 中的 `data_root` 决定，默认是仓库内的 `easyFL/flgo/benchmark/RAW_DATA`。本仓库放在 `/root/autodl-tmp`，因此原始数据也在数据盘。先下载并校验 CIFAR-10、CIFAR-100；任何失败都必须修复后重试，不会跳过该数据集。

```bash
readlink -f easyFL/flgo/benchmark/RAW_DATA
df -h /root/autodl-tmp
bash scripts/autodl_experiment.sh data-d1
```

预期出现 `CIFAR10_READY train=50000 test=10000` 与 `CIFAR100_READY train=50000 test=10000`。CIFAR-LT 由实验代码从原始训练集生成，无需另外下载。数据目录被 `.gitignore` 排除。

### 推荐：tmux

```bash
command -v tmux || { apt-get update && apt-get install -y tmux; }
cd /root/autodl-tmp/FL-Byzantine-Library
tmux new-session -d -s d1full \
  'bash /root/autodl-tmp/FL-Byzantine-Library/scripts/autodl_experiment.sh run-d1'
tmux ls
tail -n 80 -F outputs/d1_3b/run.log
```

`run-d1` 在启动训练前再次校验环境和两套数据，将 stdout 与 stderr 一并追加到 `outputs/d1_3b/run.log`，并以绝对 Conda Python 路径加 `-u` 运行。断开 SSH 后 tmux 中的进程继续运行。也可用 `screen -dmS d1full bash /root/autodl-tmp/FL-Byzantine-Library/scripts/autodl_experiment.sh run-d1`。

### 备选：nohup

与 tmux 二选一，不要同时启动两个完整实验。

```bash
cd /root/autodl-tmp/FL-Byzantine-Library
mkdir -p outputs/d1_3b
nohup bash scripts/autodl_experiment.sh run-d1 \
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
bash scripts/autodl_experiment.sh summary-d1
```

`D1_3B_UNIT_OK index=...` 表示一个完整单元完成，`last_exit_code` 为 0 表示脚本正常退出；完整结果应为 `D1_3B_SUMMARY_OK completed=100/100`。程序中断后再次运行同一 `run-d1` 命令，已有且匹配计划的报告会跳过；正在执行但尚未写出报告的单元会从头重跑。租用实例关机或释放前，请将重要报告备份到本地或可靠存储。

## 常见问题

| 现象 | 检查与处理 |
|---|---|
| CIFAR 下载超时、校验失败 | 查看 `run.log` 或重新执行 `data-d1`；检查 `df -h /root/autodl-tmp` 和实例联网。修复下载后重试，不跳过数据集。 |
| CUDA 不可用、GPU 号错误 | 运行 `nvidia-smi`、`bash scripts/autodl_experiment.sh check`；确认租用的是 GPU 实例及 PyTorch 2.5.1 CUDA 12.4 镜像。脚本不会退到 CPU。 |
| `ModuleNotFoundError` 或依赖冲突 | 重跑 `setup`、查看 `"/root/autodl-tmp/conda/envs/flbyz312/bin/python" -m pip check`；确认使用该环境的绝对 Python 路径。 |
| SSH 断线 | 重连后查看 `tmux ls` 或 `status` 和日志；不要因本地连接断开而重复启动。 |
| 日志暂时无新内容 | 查看 `ps -ef`、`nvidia-smi`、`stat outputs/d1_3b/run.log`、`launcher.log`；首轮下载、任务生成或长轮计算可能间隔较久，程序用 `-u` 输出。 |
| 磁盘不足 | 运行 `df -h /root/autodl-tmp`；环境、下载数据、实验输出都在数据盘，按需要扩容数据盘。 |

复用到其他创新点时，可设置不同的 `OUTPUT_DIR` 并使用 `bash scripts/autodl_experiment.sh run <entrypoint.py> [arguments...]`；该通用入口不会修改 D1 的科学参数，也不会替其他实验准备数据。
