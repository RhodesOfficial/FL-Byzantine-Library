# E01 复现身份与恢复入口

本文件只说明 `APRIME-EXP-v1` 的 C100 r80 固定梯度诊断；不开放新训练、其他参考、调参或重复效果实验。正常已完成阶段不再运行，文档更新不触发实验。

## 固定输入

- 执行交接输入：`b9e83363e5d74589454a26f812b13ece839f8d36`，工作分支 `codex/direction-a-prime`。
- 只取 `ba9b542:artifacts/direction_a/phaseG1_2_full_v1/` 中的三份元数据及 `messages/A-backbone-CIFAR100-s2026101322-r0080-v1/client_000.pt` 至 `client_019.pt`；另只读两份实际序列化/聚合边界代码。不提取模型、图像、特征诊断大包或旧 P 头。
- 任务计数/信息：[固定任务目录中的计数](../../../artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR100-N20-v1/counts.json)、[信息](../../../artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR100-N20-v1/info.json)。对应哈希、参考状态及固定五条件见 [结果身份](../../../artifacts/a_prime/e01/results.json)。
- 本轮实际环境：Windows、Python 3.10.11、NumPy 1.26.4、PyTorch 2.6.0+cpu；现有 Python 位于 `%LOCALAPPDATA%/Programs/Python/Python310/python.exe`。没有安装依赖、GPU 或外部付费。

## 实际完成的恢复

1. 代表周期在来源文件已保存、完成标记未写入的 `partial` 边界恢复客户端 0；原始和解码文件哈希不变。
2. 首次全点完成其余 19 端、全部五条件向量；JSON 序列化错误使汇总尚未发布。来源 20/20 完整、条件封存 0/5 完整、5/5 部分。部分 JSON 原样保留为 [首次部分证据](../../../artifacts/a_prime/e01/results_attempt_01.partial.txt)，不能当完整结果。
3. 修复只规范 JSON 标量类型。恢复读取全部已完成来源缓存和已有向量，独立标量核对后续作汇总；没有重新提取/解码完成来源、重新计算科学向量、重抽、训练或改变头状态。恢复前后向量哈希记录在 [结果](../../../artifacts/a_prime/e01/results.json) 的 `recovery`。
4. 最后独立进程核验输入、20 端原始/解码哈希、结果和向量哈希、三态及向量范数读回：[恢复验证](../../../artifacts/a_prime/e01/recovery_verification.json)。

## 入口及保护

- [诊断入口](../../../scripts/check_a_prime_e01.py)、[外层运行入口](../../../scripts/run_a_prime_e01.ps1)。正式启动必须通过外层入口计入冷启动、保存、读回和各失败尝试；`representative` ≤120 秒、全点必须保留 360 秒恢复/修复余量，总包 ≤1200 秒。
- 失败尝试留原回执并以新 attempt 续作；成功阶段拒绝静默重复。JSON 使用同目录临时文件、读回及原子替换；完整来源只查身份，部分文件只修复未完成项；已有结果只能封存或读取，不因低分重算。
- 新增本地产物 ≤256 MiB；主要数组写前检查已知大小，工作集监测限 8 GiB。实际、暂估和未知成本见唯一 [资源账](RESOURCE_LEDGER.json)，不将内部和外层时间相加。

已完成运行不应再次调用 `full`。可用下面的**只读身份恢复检查**确认当前本地产物仍可读取（不计算新偏差、不训练、不覆盖回执）：

```powershell
$py = Join-Path $env:LOCALAPPDATA 'Programs/Python/Python310/python.exe'
& $py -c "import sys; sys.path.insert(0,'scripts'); import check_a_prime_e01 as e; identity=e.inputs()[-1]; s=e.read_json(e.OUT/'state.json'); assert e.verify_state(s,identity)==list(range(20)); r=e.read_json(e.OUT/'results.json'); assert r['identity']==identity and e.sha(e.OUT/'results.json')==s['result_sha256']; assert e.sha(e.ROOT/r['vectors']['path'])==s['vectors_sha256']==r['vectors']['sha256']; assert all(c['status']=='complete' for c in s['conditions']); print('identities and complete local artifacts verified; no scientific recomputation')"
```

本地大文件保留在 `artifacts_local/a_prime/e01/`，不纳入 Git；精确路径、字节和哈希在 [状态](../../../artifacts/a_prime/e01/state.json) 与 [结果](../../../artifacts/a_prime/e01/results.json)。这不是仅靠 Git 就能离线恢复全部大文件的声明。若本地文件丢失/哈希改变，检查会明确失败；不得改写 complete 或自动重跑。按固定 Git 来源恢复缺失的原始字节，并经 Reviewer 说明必要的缓存/向量重建范围后再继续；不会恢复为图像训练或旧 P 实验。

未测试所有断电位置/系统级故障；已实际验证的边界仅上述两条部分恢复及完整读回。普通 ACL/路径/保存修复见提交记录，不另建科学裁决。
