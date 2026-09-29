# D1 阶段 3B 实验协议

## 固定科学条件

- CIFAR-10-LT / FLGo 现有小型 CNN，CIFAR-100-LT / FLGo 现有 ResNet18；客户端长尾不平衡比 50。
- 100 客户端，每轮随机 20 客户端，Dirichlet α=0.1，200 轮，本地 1 epoch，种子 1–4。CIFAR-10 的 batch size 为 64，CIFAR-100 为 32；分别使用学习率 0.1、0.01。训练进程一次运行一个实验单元。
- 根集从原始训练集预先隔离 2,000 条，训练/审计各 1,000 条。完整覆盖或缺失末尾 20% 类别，客户端训练池与根集不交叉。根集在受覆盖类别内保持有限长尾偏斜，每类至少 20 条（CIFAR-10）或 10 条（CIFAR-100）；缺类条件保持总预算 2,000 条。类别均衡 BR-DRAG 仅更改根训练的重采样方式，不增加独特根样本。
- 主场景的攻击为无攻击、循环标签翻转、根训练集约束的自适应模型投毒、固定 3×3 白色右下角触发器后门；攻击场景恶意客户端比例为 30%。自适应攻击仅使用攻击者拥有的尾类样本和根训练半集，绝不读取根审计半集。
- 主 D1 使用 `majority` 模式；60% 恶意压力单元预先使用 `conservative` 模式，不按真实身份或每轮恶意比例切换。

## 精简后的 100 个单元

| 家族 | 单元构成 | 数量 |
|---|---|---:|
| 主场景 | 2 数据集 × 6 场景 × 4 种子，仅 D1 | 48 |
| 论文对照 | 2 数据集 × 5 对照（FedAvg、FLTrust、BR-DRAG、FLEST、类别均衡 BR-DRAG）× 4 种子，代表场景为缺 20% 根类加自适应攻击 | 40 |
| 消融 | CIFAR-10 代表场景 × 2 种子 × 4 项：单根方向、去残差、整体审计约束、类别均衡 BR-DRAG 加普通残差拼接 | 8 |
| 恶意比例 | CIFAR-10 完整根自适应攻击 10% 时 D1/FedAvg；60% 时 D1 保守模式的完整根和缺类根 | 4 |

六个主场景：完整根/无攻击、缺类根/无攻击、完整根/翻标、完整根/自适应、缺类根/自适应、缺类根/后门。未把六场景、五对照、消融、两个数据集及各项扫描做笛卡尔积。

BR-DRAG 的根参考方向、方向差异校准与范数归一来自《Xiao 等 - 2026 - Divergence-Based Adaptive Aggregation for Byzantine Robust Federated Learning.pdf》第 IV.B–C 节。FLEST 的信任分数、K-means 最大簇置信分数、动态混合比例与加权聚合来自《Better Safe Than Sorry Constructing Byzantine-Robust Federated Learning with Synthesized Trust.pdf》第 4.2–4.3 节；此实现固定两个 K-means 簇，并使用 10 次迭代上限。FLTrust 的正余弦根信任按本项目 `aggregators/fl_trust.py` 的本地实现规则重建，以适配 FLGo 的模型差值方向。

省略 α=0.5、根预算 500/3000、缺类率 50% 的单因素扫描，因为它们主要衡量参数敏感性，不是验证“类别证据→限额残差→独立审计”增量作用所必需。恶意比例 30% 由主场景覆盖，10%/60% 只在 CIFAR-10 的代表性攻击中补充。60% 的保守模式不能用来声称缺类尾类可被恢复；报告其代价。

## 指标与判读

每单元保存总体、宏平均、预先按 LT 训练频次定义的后 20% 类别准确率、固定触发器 ASR、训练曲线、每轮根计算时间、D1 回退比例、参与轮实际恶意比例与恶意多数轮数。尾类良性客户端定义为本地尾类占比高于全局长尾训练池尾类占比；记录该组与其他良性客户端的平均聚合系数以及相对等权基线的有效权重损失。D1 聚合含几何中位数、裁剪和审计，标量权重记录为系数影响代理量，不等同严格雅可比影响；对照方法记录显式系数。不把软权重解释为二元误拒率。自适应攻击零向量回退比例用于识别攻击过弱的单元。

## 执行和恢复

所有命令均使用 `E:\anaconda3\python.exe`。首次运行时，torchvision 会自动下载原始 CIFAR-10 和 CIFAR-100 到 `easyFL/flgo/benchmark/RAW_DATA/CIFAR10/`、`easyFL/flgo/benchmark/RAW_DATA/CIFAR100/`；后续运行复用本地数据。下载需要网络连接，原始数据不纳入 Git。CIFAR-LT 的长尾划分由任务生成代码完成。

AutoDL 上的部署、数据校验和后台运行步骤见 [AUTODL_RUNBOOK.md](AUTODL_RUNBOOK.md)。

```powershell
& "E:\anaconda3\python.exe" run_d1_full.py --profile full --list
& "E:\anaconda3\python.exe" run_d1_full.py --profile full --unit 0 --gpu 0
& "E:\anaconda3\python.exe" run_d1_full.py --profile full --all --gpu 0
& "E:\anaconda3\python.exe" run_d1_full.py --profile full --summarize
```

`--all` 按固定索引顺序串行执行 100 单元；已有 `reports/unit_NNN.json` 时跳过，`--rerun` 显式重跑。每个单元先严格核对任务元数据再训练。输出位于 `outputs/d1_3b/`，不纳入 Git。

## 硬件与时间

本地 8GB 笔记本仅用于单轮逻辑检查。2026-09-28 的 CIFAR-100 缺类 D1 单轮检查测得根计算约 60.7 秒、PyTorch 峰值分配约 12.15 GiB；Windows 可能使用了共享显存，因此不能把它视为原生 8GB 可运行证明。CIFAR-100 完整根的类别数更多，16GB 配置仍应在正式首单元监测峰值。

按 20,000 个总轮次及单轮样本测算，4060 Ti 16GB 的总耗时粗估 **55–110 小时**，4090D 24GB 粗估 **25–60 小时**。这不是实测的两机吞吐；首个 CIFAR-100 D1 完整单元完成后，应以报告中的 `seconds_per_round` 重算剩余时间。代码的 batch size 与每轮参与数固定，不按设备暗改科学条件。
