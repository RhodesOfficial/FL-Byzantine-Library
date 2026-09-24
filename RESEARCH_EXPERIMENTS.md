# 四个稳健联邦学习研究想法：实验实现与运行

代码位于新分支 `codex/robust-fl-research-ideas`。这是探索性实现，**不是**
BRAFed、BR-DRAG、BOBA 或 AsyncFilter 的论文复现。它使用现有 FLGo 任务的
客户端训练、虚拟时钟与记录系统；所有模式采用同一套攻击身份抽样和模型更新
约定。现有同步入口 `run_flgo_byzantine.py` 保持可用。

## 方法与对照

| 阶段 | 本仓库中的条件 | 待检验的问题 |
| --- | --- | --- |
| 1 | `triage` 对 `baseline` | 综合模型版本、客户端历史与同轮邻居方向，把更新分成接受、有限校正、暂缓；是否降低良性少数群体的误判？ |
| 2 | `joint_timing` 对 `joint_random`，另有 `ipm` 与 `timed_ipm` | 攻击者同时选择向量与到达时机，比同向量规则的随机时机更有害吗？ |
| 3 | `root_fusion` 对 `root_only` 及保留相同可信客户端的 `baseline` | 根数据量、标签错误或类别缺失时，按方向一致性降低根参考权重，是否平滑退化？ |
| 4 | `anytime` 的 2/10/50 ms 预算对 `baseline`、`triage` | 在软时间预算下，分级筛选的准确率、误判和服务器尾部耗时如何变化？ |

三路判定目前是可证伪的启发式规则。两个及以上相似邻居可为少数方向提供支持，
因此**三个串通客户端也可能伪造一个群体**。根融合的历史方向同样可能被长期
投毒。每个风险都应作为后续消融或攻击条件，而不是把代码输出视为保证。

这里的 `root_only` 是参考方向对齐基线，并非 BR-DRAG 复现；`baseline` 可选
现有 FedAvg、坐标中位数、截尾平均、Krum 等已接入的聚合器。论文级比较还需要
另行接入 BRAFed、BOBA、AsyncFilter、GAS、FLTrust 等准确复现或作者代码。

## 准备任务

使用已配置 FLGo 与 PyTorch 的 Python 环境，从仓库根目录运行。已有 FLGo
任务直接传给 `--task`。如需创建非 IID MNIST 任务，可使用现有入口：

```powershell
python run_flgo_byzantine.py --task ./mnist_dir20 --create-mnist --partition dirichlet --alpha 0.1 --clients 20 --aggregator avg --attack none --rounds 2
```

这个命令会顺便运行两轮普通桥接训练。检查任务的客户端标签分布后，选出两个
明确视为可信、且能覆盖拟研究类别的客户端作为 `--root-ids`。这些客户端在
阶段 3 的**所有**条件中都从普通训练和攻击者抽样中排除；根样本只取自它们的
本地训练集，不使用服务器测试集。阶段 3 的 `class0_only` 是根数据缺失其他
类别的压力测试；可用 `--root-class` 更改保留类别。
当前任务的 2、11 号客户端合计只有 0、1、2、3、6、7 类，随机抽取的 100 张
根样本在检查中还未抽到 6 类。因此这组根客户端适合复核数值稳定性，不能作为
“完整类别覆盖”的对照；若要检验类别缺失效应，需另设覆盖全部目标类别的
可信根集合，并在所有相应对照中同样预留这些客户端。

## 一次运行与完整矩阵

先用一个条件检查任务与环境：

```powershell
python run_research.py --task ./mnist_dir20 --mode triage --attack ipm --rounds 5 --proportion 0.3 --seed 0
```

生成四阶段、三个随机种子的执行计划；下列命令默认**只生成计划**：

```powershell
python research_suite.py --task ./mnist_dir20 --root-ids 2,11 --output ./research_runs_v2
```

确认新目录的 `manifest.json` 后执行完整矩阵。再次运行相同命令会跳过
已经完成且记录完整的条件，继续剩余条件：

```powershell
python research_suite.py --task ./mnist_dir20 --root-ids 2,11 --output ./research_runs_v2 --run
```

可先缩小规模，例如 `--phases 1,2 --seeds 0 --rounds 10`。阶段 1 的后门条件
需要图像分类任务；离线 toy 任务仅用于连接测试。运行完毕后，重新整理记录：

```powershell
python research_suite.py --output ./research_runs_v2 --summarize
```

请把新目录的 `manifest.json`、`summary.csv`、`summary.md` 和失败条件的
`.log` 文件交给我；完整 FLGo JSON 记录仍在 `<task>/record/`，脚本在
`summary.csv` 中保留每条记录的路径。

新计划的运行 ID 带实现版本摘要，避免从任务目录误拾取修复前的记录。已有
`research_runs` 仍可用 `--summarize` 复核，但不能用来续跑修复后的实现。
汇总中的 `run_health=loss_explosion` 表示测试损失超过 1e6 或出现非有限值；
`halted_rounds` 和 `updates_used` 有助于识别旧版保护逻辑造成的空转。

## 指标解释与实验边界

- `final_accuracy`、`last_10_accuracy`、`worst_client_accuracy` 分别是最后测试
  准确率、最后十次记录的均值、最后一次客户端验证准确率的最低值。
- `status=complete` 只表示进程和记录完成。还应检查 `run_health`、
  `max_test_loss` 与 `halted_rounds`；数值失控的记录不能用于比较防御效果。
- `backdoor_asr` 仅在后门条件下计算：右下角贴块后，原标签不是目标类的测试
  样本被预测为目标类的比例。IPM 与时序攻击是非定向攻击，ASR 留空。
- `benign_false_reject_rate`、`minority_false_reject_rate` 使用模拟器已知的攻击
  身份和训练标签计算，**只用于离线诊断**，不提供给聚合器。少数客户端在当前
  实现中定义为“主导标签所在的客户端群组人数处于最低四分位”的客户端；该代理指标需
  与更细的分客户端结果一起阅读。暂缓另以 `benign_defer_rate` 和
  `minority_defer_rate` 报告，不算作误杀。
  若所有主导标签群组人数相同，当前代理定义没有少数群体，少数群体比率留空；
  分母仅有一两次决策时，0 也不能解释为方法已保护该群体。
- `virtual_time` 是 FLGo 虚拟时钟时间；`server_p95_ms` 是收到更新后的服务器
  处理时间第 95 百分位，包含参考方向与聚合工作。`anytime` 的预算只约束其
  分级聚合段，而且是软上限；应同时查看 `deadline_miss_rate` 和完整进程的
  `wall_seconds`。
- 阶段 2 的 `joint_random` 与 `joint_timing` 用同一向量构造规则及最大延迟，
  但运行过程中模型轨迹会分岔。应先核对实际 `mean_staleness` 和训练时间，再
  讨论时序选择的额外作用。
- 目前攻击者只能调整**自己的**回复内容与到达时刻。`joint_timing` 使用服务器
  历史更新的线性外推选择最不利的到达时刻，属于白盒启发式攻击，并非最优攻击。
  ALIE/IPM 在同一发送批次可见良性向量，属于强知识设定。
- 本实现主要覆盖水平图像分类任务。隐私加密、网络能耗、认证鲁棒性和论文中
  所有基线尚未实现。请不要将这些初步运行当作全面查新或可投稿的最终结果。

## 验证

在含 PyTorch 与 FLGo 依赖的环境中：

```powershell
python -m unittest discover -s tests -p test_research.py -v
python -m unittest discover -s tests -p test_flgo_bridge.py -v
python -m unittest discover -s tests -p test_research_suite.py -v
```

默认系统 Python 若没有 PyTorch，前两个测试会跳过；第三个测试无需训练依赖。
