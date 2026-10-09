# D2′ 2.2＋2.3首次失败后的修订裁决

日期：2026-10-09。审查HEAD：`a3cda3f6c33a4ebf1d49fac4731673bf2177e2d8`；审查对象包括本次未提交的报告、代码与原始证据。本轮只读分析既有轨迹，只新增本裁决文档；没有修改实现、运行训练或提交代码。

**裁决：现有报告单独不足以定根因；补充只读分析后，已经足以形成一个可证伪的明确假设。允许使用唯一一次机制修订，仅将正式运行的 `z_cut: 3.0 → 6.0`，其他参数与判据全部不变。现在不直接切D3，不启动攻击比较。若这一次完整复验仍失败，停止D2′攻击路线，提前进入换向评估。**

`[事实]` 为文件核验结果；`[只读重算]` 为本轮直接从既有日志计算的量，附输入行号；`[推断]` 不等于已证实因果；`[裁决]` 为执行约束。下文的参数修订是一个待实施的研究决定，不代表修订预算已经执行消耗。

## Q1．是否已经足以形成明确假设

**[裁决] 是，但依据不是单独的平均g=0.6759，而是本轮已完成的时间、速度、陈旧度及参考状态诊断。根因尚未被因果隔离，不妨碍提出一次有根据、可失败的修订假设。执行 Agent 不必再为这些相同统计重新采集训练数据。**

### 已核对的边界

[事实] 迁移测试与数值核验通过，完整M=45.280%，未达到48.876%；评分降低实际系数、预算lambda全1、无持续停滞，修订次数仍为0。报告明确没有消融归因证据。[报告L13](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_2_3_REPORT.md:13>)；[性能L46–56](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_2_3_REPORT.md:46>)；[预算与证据边界L66–68](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_2_3_REPORT.md:66>)。

因此可以确认“当前算法配置未保持干净可学性”和“存在系数抑制”，不能直接确认“全部5.596pp损失由g造成”。

### 应看什么、如何辨别，以及本轮实际结果

| 诊断项与数据 | 本轮只读结果 | 能辨别什么／仍不能证明什么 |
|---|---|---|
| **g与z按任务进度分布**：每个proposal的g/z及终结顺序；分S1–S5，并单列ready前后。 | 平均g依次为 **0.636840、0.684701、0.688482、0.684247、0.685537**。前400任务为0.577514，401–800为0.588756；后9600仍为0.685742。 | [推断] 早期确实更差，但不能把全部问题归为短暂冷启动；晚期仍存在稳定的整体降权。数据来自各段首尾对应的事件范围。[S1起点L8](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:8>)、[S2起点L455](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:455>)、[S3起点L897](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:897>)、[S4起点L1345](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:1345>)、[S5起点L1790至末行2238](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:1790>)。 |
| **快/慢分组g**：proposal身份连接冻结慢端名单，分别看均值与分位数。 | 快端均值 **0.684977**，慢端 **0.663635**；两组都有明显降权。 | [推断] 有组间差异，但不是只有慢端被压制；R_slow通过也不代表整体训练增益保留。[全程proposal L8–2238](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:8>)；[慢端名单L44](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_1_REPORT.md:44>)。 |
| **源版本／提交陈旧度分组**：从同次k与source_version求差，连接该源版本参考。 | ℓ=0/1/2/3的平均g分别 **0.686281/0.678755/0.663862/0.653210**；没有更高陈旧度样本。对11,580条source路径，仅把评分参考替换为同事件当前参考做静态诊断，g的平均变化为 **+0.000365**，平均绝对变化 **0.001457**。 | [推断] 当前轨迹的源／当前参考错位不足以解释约0.32的平均降权；零陈旧度也被压制，不支持“异步源快照语义本身已被证伪”。该替换只是对固定观测的诊断，不是当前参考方法训练成绩。[全程事件L8–2238](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:8>)。 |
| **sigma是否塌到下界**：检查全部参考版本及source评分使用的33维sigma。 | 最小sigma为 **0.114445**，出现在k415的范数坐标；没有source使用的sigma≤0.075。sigma中位数从k20的 **0.358974** 上升到k120的 **0.460480**，k480为 **0.465465**。 | [推断] 不支持“sigma收缩到0.05导致普遍异常分数膨胀”。因此本次不抬高sigma_min。[k415/L1551](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:1551>)；[k20/L78](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:78>)；[k120/L455](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:455>)；[k480/L1790](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:1790>)。 |
| **mu/sigma与实际特征残差对照**：在每段，对source路径的feature计算到自身源mu的绝对偏差，与源sigma比较。 | S2–S5的“全部残差绝对值均值／全部sigma均值”分别 **1.0392、1.0349、1.0394、1.0372**；均方标准化残差的平方根约 **1.246–1.256**，而g仍约0.685。 | [推断] 尺度已大体跟踪它所定义的绝对残差量级；“普通更新与中心有非零偏差”本身就会受到当前平滑评分衰减。不能把sigma误当已校准的标准差，也不能把z_cut=3解释成“正常数据几乎不受影响”。[S2至S5的source事件L455–2238](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:455>)；[尺度目标为绝对残差L249–254](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/reference.py:249>)。 |
| **首次ready的质量与演化**：取k20快照，对接下来401–800任务的特征作事后检查，再看后续参考。 | k20的平均sigma **0.369472**；随后400条观测对该mu的平均绝对残差 **0.486062**，有早期尺度滞后。参考随后继续变化，未停在k20；晚期g仍低。 | [推断] ready不等于统计质量已充分稳定，早期问题可能有贡献；但“早期参考永久固化”与日志不符。旧任务快照被冻结，后续任务仍绑定新快照。这里使用后续观测仅作离线质量评估，不允许把它们喂回当时决策。[k20快照及随后事件L78–150](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:78>)；[后续k120/L455](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:455>)。 |
| **裁剪与评分的直接量级**：将h、原始范数n、裁剪系数c与g对齐，而不是只数超阈值个数。 | 固定旧轨迹上，`Σh·n·c / Σh·n = 0.976751`；在已裁剪向量大小之和上，再乘g后的比例为 `Σh·n·c·g / Σh·n·c = 0.659065`。 | [推断] 在这种“逐端贡献范数之和”的诊断口径下，评分的直接缩减明显更大，值得优先处理。**这不是实际聚合净位移比，也不是精度损失分摊**，因为向量方向与抵消未知。[任务原始范数及裁剪记录L1起](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/tasks.json:1>)；[全程h/g L8–2238](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:8>)。 |

**以上表格中的数值均为本轮只读重算。** 输入为600个commit事件、12,000条proposal、任务记录与终结顺序；分位数采用linear，按task_id连接，不重放训练，不调用被测评分函数。源参考由各事件的提交前参考按版本索引；最后参考可由提交前状态与已记录位移复核。source路径z的独立公式重构最大误差为4.44e-16。[事件L8–2238](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:8>)。

本轮核对events、tasks、terminal_order及已有分组统计的SHA256均与清单一致；原文件未覆盖。[events索引L11595–11598](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_2_3_MANIFEST.json:11595>)；[tasks与顺序索引L11620–11628](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_2_3_MANIFEST.json:11620>)；[分组索引L11635–11638](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_2_3_MANIFEST.json:11635>)。

### 只读分析的止步处

不能从这些日志恢复“取消g后重新训练”的模型轨迹、M或准确的净方向差。正式记录保留了低维特征、范数与数值checks，但没有持久保留每批完整模型位移和逐端高维更新。[存储选择L106–110](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/float32_protocol.py:106>)。**不要求为补这类事后归因而再跑一组诊断训练；也不将固定日志的改分数计算冒充消融实验。**

## Q2．唯一一次修订：假设、参数、预期与证伪

### 假设的精确表述

**[推断／待检验假设] 当前绝对残差尺度下，正常异质更新的标准化残差长期集中在z约1.2；`z_cut=3`的平滑评分即使不拒绝更新，也会使大多数正常更新持续获得约0.68的系数。固定K、无评分后再归一化的聚合把这种评分衰减直接传到训练步长和参考更新。在固定12,000任务预算内，这种持续增益损失是可学性差距的主要可修复来源；只放宽评分曲线应能恢复干净性能门。**

这是假设“此修订足以修复当前可学性”，不是宣布“所有精度损失都由g造成”。参考更新也使用同一g，修订会改变未来参考，不能称为只改变模型学习率的严格消融。

[事实] 评分为 `g=(1−(z/z_cut)^2)^2`，超过截断则0；模型与参考候选系数都乘g。[评分公式L166–185](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/reference.py:166>)；[双通道系数L244–256](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/reference.py:244>)。

[只读重算] 仅代入公式，z=1时原g=0.790123，z=1.25时原g=0.682919。即使这些更新都在截断以内，它们也不会获得接近1的权重。全程实际z中位数为1.224469，后9600任务中位数为1.211756。[全程事件L8–2238](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:8>)。

### 具体修订与单值选择理由

**[裁决] 仅将正式实验配置 `z_cut` 从3.0改为6.0，cold与source路径共用这个值。** B_M、H/beta、e_ready、sigma_min/sigma_0、kappa_U、eta_M/eta_R、B_R、n_boot、特征映射、任务/模型/种子、K/槽位/期限/延迟及所有通过门槛不变。无需改评分函数形式，不增加再归一化、权重下限、热身豁免或额外服务器步长补偿。保留旧配置及其失败轨迹，修订清单使用新配置哈希。

[推断] 选择6是对“正常更新保留约90%评分系数”这一诊断目标的一次明确调整：以晚期z中位数1.211756代入 `g≥0.90`，需 `z_cut≥5.3492`，取向上整数6，避免伪精确取值。**0.90是本次参数选择目标，不是原性能门，也不是来自独立确认集的统计标准。** 本轮只计算了这一新取值，没有扫描多个cutoff后择优。

[只读重算] 保持旧轨迹所有z、源参考、h和时序不变，代入6：

| 固定旧轨迹上的代数量 | 原3.0 | 新6.0，仅静态重算 |
|---|---:|---:|
| 全程平均g | 0.675961 | **0.911834** |
| `Σh·g/Σh` | 0.680487 | **0.913089** |
| 后9600任务的`Σh·g/Σh` | 0.690574 | **0.916426** |
| z=1.25的g | 0.682919 | **0.915078** |

输入与公式见[全程事件L8–2238](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:8>)及[评分L185](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/reference.py:185>)。**这些值不是新训练的预测轨迹，不能用于计算或声称修订后的M。**

[只读重算] 新g下、尚未执行预算缩放的旧时序候选费用 `q*=0.055h·g_6`，最大同身份33-tick窗口费用为 **0.454061**；3个身份有超过0.4125的窗口。各身份最大费用的95%分位为0.377965。[全程事件L8–2238](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase2_2_3_20261009/full/events.jsonl:8>)。**[推断] 新训练可能开始触发预算，故不能把0.913089当实际最终系数保留率，更不能顺手调大beta以保证它不触发。**

### M预期、有效判据与时间点

**[推断] 若假设成立，预期回到较好基线的2pp容忍范围。可登记的恢复目标是M约48.876%–50.876%；这是验收目标区间，不是由现有日志得到的可靠预测或置信区间。现有证据不能支持更精确的M预测；高于50.876%也可以通过。**

| 时间点 | 固定检查 | 判定含义 |
|---|---|---|
| 修订登记后、完整训练前 | 有效配置只有z_cut变化；复核6对应的评分边界、双通道系数/预算与参考不变量；按原入口规则做短程smoke。 | 接线/数值资格。不得按smoke准确率再选参数；真实训练使用原始初态，不能接着旧失败模型训练。 |
| 终结2400任务 | 原ready出现门、进度和无错误要求不变；记录该段g/z、实际a、名义h/20、lambda及参考尺度。 | 只作既定机制诊断，不新增早期M门，不据此换成另一个cutoff。 |
| 终结4800任务及以后每段 | 报告`G=Σh·g/Σh`和`A=Σa/Σ(h/20)`，分别识别评分恢复和预算再抑制。后四段合并G、A均≥0.85作为“持续系数损失已明显缓解”的预登记诊断支持线。 | 0.85是本假设的解释性检查，不替代原性能门；中途未达线不授权调参或按成绩提前截断单元。 |
| 完整12,000任务结束 | 原末五点M **≥48.876%**；R_slow≥0.80；原后四段P≥0.10且无整段停更；ready/source覆盖、全部预算/数值/协议判据通过。 | 全部满足才判修订后的2.2＋2.3通过。仍只跑一个修订完整单元，不追加seed找好结果。 |

原性能、慢端、停滞与机制门见[裁剪版L65](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS_TRIMMED.md:65>)、[完整机制要求L187](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:187>)；48.876%的来源见[本次报告L46](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_2_3_REPORT.md:46>)。

**如果假设错，如何判：**

- G、A已恢复至上述诊断线，但M仍<48.876%：**“缓解评分缩减足以修复可学性”未成立**；可能还有方向选择、参考动态或其他损失。不能据此说评分完全没有作用，也不能因M有所上涨就放行。
- G恢复而A未恢复：预算/时序等耦合抵消了系数恢复；若最终硬门失败，单参数修订仍判失败，不允许接着改beta/H。
- G本身没有持续恢复：新轨迹上的参考/更新分布反馈使固定日志推断不成立；按实际记录判，不用静态0.912覆盖实测结果。
- M和全部原硬门通过，但G/A诊断不支持：可以判可学性门通过，**不能写成已经证实预想的增益中介解释**。
- 任一工程不变量失败：停止、修工程，并区分无效运行；工程修复不得改变这唯一的算法修订取值。有效完整修订运行失败后，不再追加第二个机制配置。

**代价与结论限制：**[只读公式] z=3时原g=0，改为6后g=0.5625；接受区明显变宽。[公式L185](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/reference.py:185>)。[推断] 干净性能恢复可能伴随更弱的异常抑制。通过本关只允许恢复到后续攻击验证路线，不能声称鲁棒性提高；阶段3必须让攻击知道新阈值并按新配置执行，BRAFed及其预算对照仍不可跳过。

## Q3．现在是否换向，失败后走哪里

**[裁决] 现在先用已完成的只读诊断支持上述唯一修订，不直接换向，也不再要求额外采集训练型诊断。执行 Agent 停下保留预算是正确的；本裁决才给出具体修订选择。**

[事实] 既有规则允许一次诊断驱动修订；再次失败应停止攻击比较并进入换向评估。3.4是较晚的继续/换向门，2.2反复不能正常学习时应提前止损。[失败规则L63–64](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:63>)；[2.2处置L180](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:180>)；[提前止损L311–315](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:311>)。

**本次执行顺序固定为：**保存原失败证据 → 登记唯一z_cut修订与受影响检查 → 短程入口验收 → 一个完整修订单元 → 按原硬门裁定。两条2.1基线的算法和外部协议没有被修改，不因这项D2′参数修改而自动重跑；发生公共驱动/协议改动则另按原复用规则核对，不得混用不匹配结果。

如果有效修订完整单元仍失败：

1. 在2.2＋2.3处记“修订后FAIL、一次机制修订已用完”，保存两次配置、全部诊断和未通过项；停止后续D2′攻击与大矩阵。
2. **不为拿到“3.4 FAIL”而继续跑3.x，也不能把当前失败冒称已执行了3.4。** 3.4需要前序通过以及强基线证据。[依赖图L128–135](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS_TRIMMED.md:128>)。
3. 向用户交付提前止损结论，并进入**D3换向评估**：核对D3对公共探针/模型结构/数据条件的要求、现有可复用资产及最低正面证据路径。该评估不等于D3已可行，更不自动启动D3实现/训练。
4. 用户再决定是否启动D3或改变项目预算。本次无需用户补充参数选择；若要在这一次失败以后继续扩大D2′校准，则属于新范围，需要用户明确改变此前的一次修订约束。

## Q4．B_M、H/beta及首版默认值应如何对待

### B_M

**[裁决] 它确实改变了一部分本轮更新，但其对M损失的因果贡献未确定；本次不同时调整B_M，也不另开一个并行B_M修订。**

[事实] 808/12,000上传被裁剪，平均裁剪系数0.988101；慢端8.8183%、快端5.2085%。[裁剪结果L72–80](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_2_3_REPORT.md:72>)。这些比例与Q1的加权范数诊断支持“裁剪存在、评分的直接系数损失更广泛”，不支持“裁剪必然无害”。

[推断] 同时改B_M会连同特征归一化、饱和坐标和评分输入一起变化，无法再把该单次修订解释为针对评分曲线的调整。B_M也进入特征映射的尺度。[特征定义L93–103](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/reference.py:93>)。因此本次保持0.9701598816245317；若后来还想改B_M，必须承认那是第二次机制修订，不能靠“单独立案”绕过次数限制。

### H=33 / beta=0.4125

**[裁决] 这次不调整。lambda全1足以排除“本轨迹实际被预算截断”作为直接损失来源，但不能证明预算过大、无用，或攻击下也不会生效。**

[事实] 实际最大身份窗口费0.381976低于0.4125；迁移用例已触发预算耗尽/缩放；正常干净轨迹允许预算不触发。[报告L66](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_2_3_REPORT.md:66>)；[原机制判据L187](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:187>)。

[推断] 当前预算不触发也可能部分源于g先压低了收费。修订后预算可能开始发挥作用，Q2已给出固定轨迹上的超额候选诊断；这正是应保留并报告的耦合，不能以“干净不能触发”为新目标去重新校准beta。

### e_ready、z_cut、sigma_min等默认值

**[裁决] 应当接受质疑，但不是同时调整全部参数。首版默认值经过公式与实现验收，不等于经过真实训练有效性校准。** 设计原文已经将它们标为实现默认值、效果待验证。[首版参数说明L325–332](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_DESIGN.md:325>)。

- 本次证据优先指向 **z_cut控制的正常残差到系数映射**，故只调整它。
- **sigma_min**：Q1未发现接近下界的塌缩，不抬高。
- **e_ready**：早期参考确有尺度滞后，但晚期仍降权，单纯推迟ready缺乏针对主要持续问题的依据。ready是e达到阈值，不是参考质量认证。[ready定义L120–129](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/reference.py:120>)。
- **eta_R、B_R、kappa_U、sigma_0及eta_M**：现有诊断未将它们单独识别为需要修改的项；本次保留。尤其不能在放宽z_cut的同时增加服务器步长或参考步长来保证成绩回升。

## Q5．失败的全局定位与修订预算

**[裁决] 定位为“当前评分参数化与固定K、无再归一化写回之间存在持续增益损失的候选机制失败”；尚不能定性为D2′核心思想已被否定，也不能宣布只是一个已知可修好的超参数问题。现有证据不支持异步语义与D2′根本冲突。**

- **已证实的工程/实验层结论：**此配置的完整干净可学性不达标；参考路径确实启用；账本和写回通过已覆盖的验证。[报告L46、L58、L64–68](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_2_3_REPORT.md:46>)。测试通过不等于证明不存在任何未覆盖工程问题，但当前没有新增工程错误证据。
- **[推断] 首版参数问题是当前最有依据的可检验解释：**成熟期尺度没有塌缩，零陈旧度和快端也存在降权，且评分公式本身能解释正常z约1.2为何只保留约0.68的系数。其是否主导M损失仍须由唯一修订检验。
- **[推断] 不能据此判根本异步冲突：**当前源/当前参考的静态评分差很小，持续学习与慢端门均通过。也不能据这一轻度陈旧度轨迹反向宣称所有异步场景都适用。

**一次修订仍合理；不启动更大范围的重新校准。** 理由是现在有了单一、可解释的修改对象，而不是为了用完额度。若诊断呈现参考不受控、根本不可辨识或协议无法满足约束，本可不使用这次额度直接止损；本轮日志没有给出这样的结论。

修订若通过，仅支持“在这个开发任务、种子和正常延迟条件下，调整评分曲线恢复了干净可学性”。它不证明源版本评分带来正面增量、不证明预算抗攻击，也不能替代后续消融、强基线及确认矩阵。修订若仍失败，按Q3提前停止D2′攻击路线；不降低48.876%门槛，不把45%附近的持续学习改称本关成功。
