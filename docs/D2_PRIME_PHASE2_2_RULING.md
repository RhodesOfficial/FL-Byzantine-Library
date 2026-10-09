# D2′ 裁剪版 2.2＋2.3 开工裁决

日期：2026-10-09。审查基线：`a3cda3f6c33a4ebf1d49fac4731673bf2177e2d8`。本文件只裁定接口语义、验收与失败处置，不包含实现或新训练结果。

`[事实]` 均附文件行号；`[推断]` 表示由证据推出的判断；`[裁决]` 是本次确定的约束。**无需用户再拍板。先完成正式 D2′ 路径的迁移复核，再运行 seed101 的一个完整干净单元；不重新校准 H、beta、B_M 或参考参数。**

## Q1．正式接入、提交触发、等待与结果消费

### 明确裁决

**[裁决] 选 (b)：新建 D2′ 专用的正式异步入口。复用2.1的外部调度、运输及真实客户端训练契约；D2′ 的模型、参考、预算和任务终态由一个联合提交后端负责。不要在已冻结的基线入口中加入算法开关，也不要先调用基线聚合再补做 D2′ 评分/扣账。**

- [事实] 正式基线状态只接受 avg/rfa，维护自己的模型、任务、源模型和 FIFO；它的提交是模型单通道写回。[基线状态 L35–51](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/async_baseline_state.py:35>)；[基线写回 L162–200](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/async_baseline_state.py:162>)。
- [事实] 原 TaskProtocol 把模型固定为 CPU/float64，接收也按 double 构造差值；其 `commit_event` 才包含参考、账本和模型的共同提交。[核心初始化 L89–113](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/protocol.py:89>)；[接收 L262–274](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/protocol.py:262>)；[联合提交 L347–365](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/protocol.py:347>)。
- [推断] 因此“直接挂上旧对象”和“给基线聚合加后置过滤”都不能自动继承正式 GPU 运行与双通道提交的正确性；需要正式数值路径的迁移验收。

**允许边界：**允许执行 Agent 扩展机制核心的设备/精度适配，或抽取可复用的公共驱动，但必须保持既有 CPU/float64 默认调用与0.7契约兼容，不改评分、预算、快照和任务规则。`reference.py` 的评分/参考纯函数与 `budget.py` 的账本规则应直接复用；确需调整数值承载时须通过 Q4。基线运行的默认行为和记录含义不能改变。文件组织与复用方式属于实施选择，不改变上述架构裁决。

正式模型训练、源模型载体和模型写回继续 GPU/float32、无AMP；参考统计和账本保留现有 CPU/float64 数值口径。不能维护一条持续演化的 double 隐藏模型、仅把它舍入给客户端：**每个源快照必须对应实际已写回的 float32 模型**。模型贡献与参考特征必须对应同一个规范的裁剪候选；数值转换不能变成第二套裁剪/特征定义。既有真实模型两层核验继续适用。[既有精度裁决 L21–25](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_1_RULING.md:21>)；[当前特征输入域 L93–103](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/reference.py:93>)。

### 何时调用 `commit_event`

**[裁决] 沿用2.1开批门：满 K=20，或最老合法候选从首次到达起等待满8 tick，或满足既定尾部排空条件。调用一次联合提交是一次“尝试”，不保证产生模型版本。** 不按同步轮触发，不因每个 tick 到来就无条件提交小批。

1. 每 tick 先处理到期，再接收本 tick 到达，按 FIFO 取最多20个候选；每批前重新检查期限和提交版本差。
2. **开批人数按合法、未终结、已到达的候选计，包含预算等待者。** 开批后，余额为零者从本次评分输入与冷启动统计中排除，但继续留在原 FIFO/缓冲位置并占槽。不为了凑足20个“有余额者”跳过等待者、从后面补取额外样本，也不按剩余人数改分母。
3. **下一 tick 必须重新检查等待任务与开批资格；满足上述门才再次调用 `commit_event`。** 等待不足8且不满20、也非尾部时，不立即重试小批。等待年龄不重置；满8后即使没有新包，也有每 tick 的重试机会。余额随模拟时间释放，不依赖版本推进。
4. 同 tick 若一次尝试确实终结了任务，可以继续按同一门处理后续候选；若没有新增终态/候选移出，就停止本 tick 的重试循环。不能只检查“返回了 CommitResult”就继续循环；也不能只按版本是否变化判断进度，因为全拒绝也可能释放槽位。
5. 重试必须重新检查有效性、余额、当前版本差、当前参考写入方向和本事件冷启动统计。源参考快照、源模型、task_id、首次到达时间和到期时间保持原值。不得复用旧 scales、旧候选增量或延长期限。
6. 提交/拒绝/过期才释放身份和全局槽位；waiting 不释放、不补训、不新签同身份任务。每 tick 最后的补槽规则仍是2.1的规则。

[事实] 2.1 已冻结满批/8 tick/尾部、40槽以及先终结再补槽。[2.1报告 L29–40](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_1_REPORT.md:29>)。核心先从缓冲候选中排除零余额者，再准备参考；等待不调用任务终结，而消费/拒绝调用终结。[资格筛选 L370–391](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/protocol.py:370>)；[任务终结与填充 L205–218](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/protocol.py:205>)；[消费与拒绝 L427–445](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/protocol.py:427>)。等待后重算是原设计要求。[设计 L273–280](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_DESIGN.md:273>)。

### Server 消费 `CommitResult` 的契约

| 字段/状态 | 必须做什么 | 不得做什么 |
|---|---|---|
| `event` | 记录同次候选、源版本、评分路径、g/h及提交前参考，供逐端重构和机制覆盖检查。 | 用该诊断对象再次调用参考写入，或用当前参考替换其中绑定的源参考。 |
| `receipts` | 作为实际成功消费、a/b/q及提交时刻的依据；每 task_id 只计一次。 | 把一个 proposal 或一次重试当作一次新训练/新消费。 |
| `waiting` | 保存原因，结合**提交完成后的权威任务状态**决定是否继续等待；按上述开批门重试。 | 因出现在 waiting 就释放槽位、重签、扣费、刷新期限或复活终态任务。 |
| `rejected` | 记录拒绝原因，核对对应终态；其实际 a/b/q 为0。 | 将“拒绝”改成均匀聚合或放回队列试到通过。 |
| `scales` | 记录本次候选 a0/b0、余额和缩放，关联同次 event。 | 把它当最终账目，或在重试时复用。 |
| `model_displacement` | 核对 −Σa_i·裁剪更新与真实 float32 写回；同步载体与已提交状态，逐元素核对。 | 后端已提交后，再把这个位移重复加到后端模型上。 |
| `reference_displacement` | 核对 Σb_i·v_i、实际参考前后状态及其快照。 | Server 再独立更新一次参考，或只写模型不写参考。 |
| 版本/终态/快照 | 读取后端完成整个事件后的状态，再评价、记录与签发新任务。 | 按 CommitResult 非空自行加版本，或在半提交状态调用评价/派发。 |

[事实] `waiting` 是事件诊断列表；核心在生成它以后，还可能因其他任务成功提交而推进版本，再调用 `_expire_stale()`。[返回结构 L78–86](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/protocol.py:78>)；[提交尾部 L439–447](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/protocol.py:439>)。**[推断] 因此某 task_id 可同时出现在本次 waiting 诊断中、最终状态却已经过期；不能根据 waiting 列表重建活任务集合。**

**[裁决] 每次 `commit_event` 完成后均须通过 `audit_budget()`，包括只等待/只拒绝的尝试；保留核心原有的提交前和草稿发布前审计。** 每 tick 还要核对任务、槽位、队列、模型载体和版本；单元结束独立用持久账目重算所有历史窗口。审计失败立即停止，不用 epsilon 免除实质超额。[已有审计覆盖 L314–334](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/protocol.py:314>)；[核心调用位置 L358–365](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/protocol.py:358>)；[预算容差 L36–39](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/budget.py:36>)。

## Q2．H/beta、系数及额度的对应

**[裁决] 直接对应 `BudgetConfig.window=33.0`、`BudgetConfig.limit=0.4125`。不换算为模型版本、批次数或任务数，不再除以K或1.1。eta_M=1、eta_R=0.1、K=20、rho=0.1全部沿用。**

[事实] 2.1用提交的模拟时间间隔校准 H，用提交前 h 下的名义 q=0.055h、窗口 `(t−H,t]`、每身份最大窗口费用校准 beta。[2.1校准 L105–109](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_1_REPORT.md:105>)。`RollingBudget` 也按模拟时间窗口累计同身份 q，receipt要求 q=a+b。[预算定义 L8–33](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/budget.py:8>)；[窗口实现 L77–98](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/budget.py:77>)。

[裁决] 正式 D2′ 每次候选/重试均使用：

\[
h_i=\frac{1}{1+k-s_i},\quad
a_i^{(0)}=\frac{h_i g_i}{20},\quad
b_i^{(0)}=\frac{0.1h_i g_i}{20},\quad
a_i=\lambda_i a_i^{(0)},\quad b_i=\lambda_i b_i^{(0)}=0.1a_i,
\quad q_i=a_i+b_i.
\]

小批、去除零余额者及拒绝后，分母始终20；**不再乘 RFA 的 w_i 或小批 m/K**。D2′ 本身不是“RFA权重×D2′评分”的组合。无评分抑制且无预算缩放时，a_i=h_i/20，与2.1平均的系数兼容；启用 B_M 后向量已被裁剪，因此不宣称模型轨迹必然等于未裁剪基线。

[事实] 核心 `prepare_event` 按固定 capacity 生成 a0/b0；共同缩放和 rho 比例已写入联合提交。[候选系数 L244–256](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/reference.py:244>)；[最终系数 L394–414](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/protocol.py:394>)。2.1平均实际系数为 h/20。[2.1报告 L52–56](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_1_REPORT.md:52>)。

[推断] H=33大于任务期限32，并不表示两个时间量冲突；H约束已发生的贡献，期限约束当前任务存活时间。但刚耗尽额度后立即签发的新任务，可能在旧费用释放前先到期。这是当前冻结设计可能产生的机制损失，必须报告，不能擅自缩短H、延长期限或提前退费。

## Q3．参考与评分参数

**[裁决] 原值直接沿用；在2.2 smoke前把有效值、初始化状态、特征映射及其哈希明确列入本单元冻结清单。新增的是显式登记，不是新增调参实验。**

| 量 | 2.2固定值/含义 |
|---|---|
| `sigma_min` / `sigma_0` | 0.05 / 0.25 |
| `e_ready` / `kappa_U` / `z_cut` | 0.5 / 0.1 / 3.0 |
| `B_R` / `eta_R` | 1.0 / 0.1 |
| `n_boot` / `eta_M` / `K` | 3 / 1.0 / 20 |
| 特征 | CountSketch 32桶＋范数，共33维；映射种子0，保存实际桶号/符号及参数展开顺序。 |
| 初始参考 | mu全0、sigma全0.25、e=0；U=1；未ready。不得从2.1轨迹拟合中心/尺度或预充证据量。 |

[事实] 这些默认值来自设计§2.1.7；当前 `ReferenceConfig` 与之对应。**sigma_0不是当前配置对象里的独立字段**，而是 `ReferenceState.initial()` 中固定的0.25，不能只保存 `ReferenceConfig` 后声称初始化已完整登记。[设计 L321–328](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_DESIGN.md:321>)；[配置 L16–26](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/reference.py:16>)；[初始化 L120–134](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/reference.py:120>)。

[推断] 异步适配已经通过源快照与提交版本差 h 进入公式；2.1没有运行参考评分，不能从其干净基线成绩推出应改变 z_cut、e_ready 或尺度下界。[2.1范围 L19](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_1_REPORT.md:19>)。2.2若机制失败，按已有一次诊断修订规则处理，不能先搜索这些参数再把最佳运行报成唯一首测。

## Q4．迁移复核的范围、位置与失败回退

**[裁决] 它是2.2＋2.3合并关内部、完整训练之前的必过工程子项。可先单独完成一次执行会话，但不新增阶段编号或完整实验单元；2.2报告必须单列“迁移复核：PASS/FAIL及证据”。旧CPU测试通过不能替代新Server、实际GPU载体的直接验收。**

[事实] 2.1裁决已要求迁移复核；2.1报告也明确未替代该验收。[前置裁决 L25](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_1_RULING.md:25>)；[2.1边界 L159](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_1_REPORT.md:159>)。

以下是**验收族，不是新增关卡**。同一个固定张量用例可覆盖多行。

| 验收族 | 必须通过的具体性质 | 失败回退 |
|---|---|---|
| 协议与触发迁移 | K20同刻40到达分两批且第二批重新算h；混合源版本差值正确；7/8 tick开批边界、尾批、32到期、64/65陈旧边界正确；等待占槽，身份≤1、全局≤40；重复/错身份/未来版本不能消费；纯等待不会同tick死循环。 | 0.1＋0.2及正式驱动适配。 |
| 源快照与因果性 | 修改当前参考不能改变ready源的g；修改尚未到达包不能改变当前评分/写回；签发时cold的任务不能改绑后来ready参考；旧快照无别名污染，并保留至所有合法引用结束。真实源/当前参考不同的固定用例必须产生手算可区分的评分。 | 0.3；来源/队列绑定错误同时回0.2。 |
| 冷启动和参考写入 | eligible<3时cold等待且不预留；零余额身份在冷统计前排除；真实收费的固定轨迹覆盖cold→ready，不能靠手动预充证据替代；中心、尺度、证据的联合创新范数≤B_R，逐端Σb_i v_i重构实际参考位移；拒绝/等待不写参考。 | 0.3/0.4。 |
| 预算与重试 | 用H33/beta0.4125覆盖部分缩放、恰耗尽、33左端点释放、等待后重算h/方向/余额；过期不提前退已付费用；全历史窗口不超额；q=a+b、b=0.1a；即使向量相消或参考创新为零，也不退系数费用。相同配置下共享额度与模型额度beta/1.1的已定义等价性仍成立。 | 0.4。 |
| float32模型及两条贡献 | 原始差值绑定实际float32源；全范数裁剪和特征输入为同一候选；每次实际a/b与账目一致；模型通过既有两层误差及独立写回舍入核验；参考在double下逐元素`atol=1e-10, rtol=1e-8`重构；新快照模型与实际CNN逐元素一致；无NaN/Inf、无事后投影掩盖越界。 | 数值承载/0.2/0.3/0.4，按失败来源定位。 |
| 原子发布与结果消费 | 发布前注入参考或记账错误时，模型、参考、账本、任务状态、版本和快照不变；不暴露“模型已写但参考未写”的状态；正系数相消仍推进一次版本；无receipt不推进；waiting诊断里的任务若最终过期，不被复活。故意漏参考费/漏receipt/重复消费必须被审计发现。 | 0.4及正式Server消费边界。 |
| 进度、统计与真实入口 | Q5的终态排序/分段/跨评价点处理有独立固定例；尝试数、训练数、实际消费数分别对账；用冻结配置完成一次约200任务的真实GPU短程入口验证，载体/队列/参考/账本一致，无根读取、无死锁，训练预算计数正确。 | 0.2/正式驱动或诊断实现。 |

固定张量复核必须至少有一组用正式 K=20、H=33、beta=0.4125和32/64/8参数贯通新Server、原生运输和实际载体。可继承旧小参数用例作为独立数学锚点，但不能只验旧纯后端。200任务smoke只验接线，不承担可学性或ready覆盖门槛。

已有可复用的验收依据包括：零余额者排除及重试重算测试，[原0.4测试 L261–309](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/tests/test_d2_prime_commit.py:261>)；发布失败不改状态和错误账目负例，[原0.4测试 L406–448](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/tests/test_d2_prime_commit.py:406>)；真实模型的统一数值判据，[检查点 L57](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:57>)。这些引用规定应保留的性质，不声称新路径已通过。

**回归范围：**重跑现有协议、参考和联合提交自动测试；若修改了它们的公共默认行为或0.7依赖，还须重跑受影响的恢复测试。若抽取/修改了基线公共驱动，重跑2.1直接入口锚点与回归，并证明基线行为未变；不能只凭“重构”二字继续抵扣旧基线。正式GPU恢复仍不在本次范围，发生不可恢复错误时终止单元，不半程继续。

**训练放行：**迁移复核与smoke均通过后，才运行一个12,000任务完整单元。失败修工程，不调整性能参数。完整训练因评分/预算长期抑制而失败，才按机制FAIL处理：最多一次有明确假设的修订、重跑受影响单元；仍失败则停止攻击比较并进入换向评估。[失败规则 L63–64](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:63>)；[2.2处置 L180](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:180>)。

报告还须分别列出完整可学性与机制启用，不能把迁移PASS当成合并关PASS。沿用：干净M相对较好基线下降≤2pp、R_slow≥0.80、无Q5停滞；前20%任务内出现ready源快照，后半程正常源路径覆盖≥80%。[裁剪版 L65](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS_TRIMMED.md:65>)；[机制门槛 L187](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:187>)。

[事实] 已冻结较好基线M为50.876%。[2.1结果 L84–85](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_1_REPORT.md:84>)。**[推断] 本单元的干净M通过下限因此是48.876%，不能改用RFA 49.024%作为较好基线，也不能用旧版单seed的3pp条款放宽裁剪版2pp要求。** 正常干净轨迹可以不触发预算耗尽，但上述迁移用例必须真实触发；本关不为凑触发而新增攻击训练。[机制范围 L187](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:187>)。

## Q5．单单元的持续停滞与任务进度

**[裁决] 完整版定义直接用于这一条12,000任务轨迹；不需要多个seed才能分段。按“已训练且已终结任务”的累计顺序分成5段，每段2400个任务；不用tick、提交批次或模型版本分段。0.10门槛不变。**

[事实] 原检查点明确以已训练且已终结任务为异步进度轴，并要求在一条完整轨迹中分5段、检查后4段。[进度口径 L48](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:48>)；[持续停滞 L56](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:56>)。

### 分段与系数比

终态事件按实际事件顺序排列；同一原子事件同时终结的任务用 task_id 升序确定统计序号。得到终结序号1至12,000：

| 段 | 终结序号 | 用途 |
|---|---|---|
| S1 | 1–2400 | 冷启动诊断；仍检查数值/预算/协议，且检查ready出现门槛。 |
| S2 | 2401–4800 | 停滞硬判据。 |
| S3 | 4801–7200 | 停滞硬判据。 |
| S4 | 7201–9600 | 停滞硬判据。 |
| S5 | 9601–12000 | 停滞硬判据。 |

每个已训练任务恰好进入一段，不因同身份重复训练或候选重试而重复计数。跨界原子提交只在离线统计中按任务分段，不拆开实际提交。

\[
A_j=\sum_{i\in S_j}a_i^{\rm actual},\qquad
N_j=\sum_{i\in S_j}\frac{1}{20(1+\ell_i^{\rm arrival})},\qquad
P_j=A_j/N_j.
\]

这里 consumed 任务取最终receipt的a；拒绝/过期等未消费任务取0。**名义分母沿用慢端保留的无筛选口径：首次合法到达版本差，未合法到达者取到期版本差。** 包含已训练但未消费的任务，不包含g、lambda或裁剪缩放；不把重试产生的多个a0加进分母。算法实际系数以及H/beta校准依然使用提交前版本差，不能混淆这两个字段。[慢端分母的既定定义 L55](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:55>)。

S2–S5任一段 P_j<0.10即推进失败；等于0.10不因该条失败。分母为0、缺任务或缺到达/到期版本证据属于不可判/诊断错误，不能记PASS。**这个门不能通过删除过期任务或只统计有评分/有receipt的任务来满足。**

### “整段模型无有效位移”的可检查定义

以该段起止终结序号对应的完整原子事件边界为观察范围；边界跨段的事件同时列入相邻段的位移诊断，明确标记，不复制其任务费用。逐事件计算实际float32模型前后差：

\[
V_j=\sum_{e\in\text{该段覆盖的事件}}\|\theta_e^+-\theta_e^-\|_2.
\]

- **V_j=0表示所有实际写回均无参数变化；不能仅凭段首与段尾相同判停滞。** 这里不另设可调的“极小位移”阈值；非零但过小的情况由P_j、两层核验和完整性能共同诊断。
- 以已通过完整可学性的平均基线为固定参照，离线核对其同任务进度段是否存在已核验的非零实际写回。若基线仍推进而D2′整段 V_j=0，判推进失败；不得用“没有NaN/任务仍能终结”解释为正常学习。
- **本停滞门中的“基线仍在学习”按“已通过完整可学性且该段仍有非零训练写回”操作化，不新增逐段准确率上升要求。** [事实] 2.1模型每批记录了写回 checks，其中诊断包含实际参数差的 `delta_norm`，可离线复算对应段，不需要重训基线。[每批checks L176–187](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/async_baseline_state.py:176>)；[delta_norm定义 L84–99](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/contribution_diagnostics.py:84>)。
- 若基线该段也无位移，或原始上传本身趋零，必须报告上传范数与直接贡献重构，不能仅从零位移归因为门控；证据不足时不得勾选该子项PASS。P_j及完整性能门仍独立有效。[原零更新解释要求 L56](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:56>)。

### 评价点跨越的必要约定

[事实] 当前基线Server若任务进度跳过登记评价点就报错；2.1完整基线全为20条满批且没有拒绝/过期，实际精确命中了评价点。[精确命中检查 L73–80](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/async_baseline_algorithm.py:73>)；[2.1轨迹 L94–101](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_1_REPORT.md:94>)。**[推断] D2′引入非整批消费和过期后，直接照搬该检查会把正常跨点误判为工程失败。**

**[裁决] 目标点仍为10,400/10,800/11,200/11,600/12,000。若无法精确命中，在首次达到或超过该目标的完整原子事件边界评价一次，记录目标值、实际终结数及偏移，不插值、不择优，不拆提交来凑点。** 过期事件完成后和每次提交事件完成后都要检查，不能把整个tick内多次事件全部处理完才取点。40槽下单事件越点至多39个任务；超出此界应检查驱动。2.1在该规则下偏移为0，原结果仍适用。这是任务进度轴的落点约定，不增加训练单元。

前20% ready门按累计终结进度≤2400时产生的源快照判定，并保存后续实际签发绑定；后半程正常路径比例按终结序号6001–12000中的实际已评分任务去重统计，ready源走source路径者/已产生实际g者≥80%。另报事件级比例、未评分/预算等待数量；重复重试不能把正常路径覆盖率刷高。

## Q6．B_M 的使用及适用边界

**[裁决] 2.2正式启用模型全范数裁剪，仍取 `B_M=0.9701598816245317`。不在开跑前改成1.003729，也不使用RFA轨迹的另一分位数。记录2.2自己的实际裁剪比例与分组差异。**

- [事实] 同步B_M来自干净FedAvg 12,000个未裁剪上传范数的95%分位，严格超阈值比例5%。[同步尺度 L119](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE1_REPORT.md:119>)。2.1裁决已明确2.2沿用该值。[既有决定 L157–164](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_1_RULING.md:157>)。
- [事实] 2.1异步平均 p95=1.003729、超阈值6.15%；快端4.5881%、慢端8.2857%。异步RFA总体超阈值7.7333%。这些是未启用裁剪基线的诊断，不是D2′实际裁剪结果。[分组证据 L115–124](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_1_REPORT.md:115>)。
- [推断] 平均总体比同步多1.15个百分点，不能独立证明应重调B_M，也不能证明慢端影响可以忽略。D2′将改变模型轨迹，自己的范数分布还需本单元观测。

**报告必须注明：**“B_M在同步干净FedAvg校准后固定迁移到异步场景；它是预先确定的尺度，不保证异步更新恰有5%被裁剪，不是异步最优阈值，也不证明快慢端截断概率相同。”

至少保存原始范数、裁剪系数、裁剪后范数，按全体/快慢端/到达与提交陈旧度/终态分组；同时报告全部合法可观测上传的超阈值比例及实际消费任务的裁剪比例。等待重试不重复计上传样本，不把g、预算lambda或h导致的缩放记成B_M裁剪。无样本组保持不可估计，不填0。

若完整单元失败且证据指向尺度失配，才依既有一次诊断修订规则处理；不得预先拿异步p95替换、也不得依据D2′成绩在多个尺度中选择后只保留获胜轨迹。[既有修订限制 L180](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:180>)。**本次裁决允许执行 Agent 开始接入与迁移复核；完整训练的放行条件是Q4通过，不是本裁决文档本身。**
