# 方向 A（FedPCC）G1.1 训练计数、邀请完成事件与正支持裁决记录 v1

日期：2026-10-13（Asia/Shanghai）。本轮裁决基准提交：`e3c3528722cd4c4f55f96b37182255a4ade961b8`。执行证据所在提交：`6ea9bd191e1f2489670d37bb60cb42a737d401e7`。

**[推断] 正式 G1.1 状态裁为“证据不足/预算耗尽”，具体原因是证据不足，未发生预算耗尽；本次有界事件 smoke 验收成立，另行登记。** K §G1.1 第 4 项的结构与机制条目在本次声明的代理工作量实例内均得到证据支持，但不能把这个明确限定为 smoke 的实例直接升格为正式通过。正式工作量协议及其事件、资源绑定仍待补齐；不否定已经成立的注册、日志对应与条件正支持证据。依据：[K §一 L54、84–85、§G1.1 L126–131][K]、[合同 §四 W01–W03、E01–E04及 §六][C]、[Pre L3、10、26][Pre]、[Mechanism L1：binding、mechanism.workload_status][Mech]。完整判定见 §二。

**这是本裁决记录的建议组织方式：**按现场与证据身份、逐项判据、参数登记、后续接口、未认证事项、协调者观察、合同更新及后续事项排列。文件名采用 `DIRECTION_A_G1_1_ADJUDICATION_v1.md`，与既有 0.2 裁决的方向、节点、ADJUDICATION 和版本命名一致，并区别执行验收报告与运行记录。本文件记录设计层裁决，不改写历史封存 JSON 的自报状态。

## 一、现场预检与证据身份

### 1.1 环境预检

以下为本轮编辑前的实际结果。Git 命令均在 `E:\Federated Machine Learning\FL-Byzantine-Library-astra` 执行，目录存在；Python 只读核对显式使用 `E:\anaconda3\python.exe`。

|预检项|实际结果|
|---|---|
|`git branch --show-current`| `feature/direction-a`，符合期望|
|`git status`|工作区干净；本地领先 `origin/feature/direction-a` 2 个提交|
|`git log --oneline -5` 第 1 条|`e3c3528 docs: record direction A adjudications and sync backbone preparation`|
|第 2 条|`6ea9bd1 phaseG1.1: invitation and completion event support`|
|第 3 条|`e3ca623 phase0.2: baseline protocol and model acceptance`|
|第 4 条|`902af7e docs: add non-attack research base and direction selection`|
|第 5 条|`9d0cfa8 Merge remote-tracking branch 'origin/master'`|

|必需文件的实际绝对路径|存在性|
|---|---|
|`E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_G1_1_ACCEPTANCE_v1.md`|存在，可读|
|`E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_G1_1_RUN_RECORD_v1.md`|存在，可读|
|`E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_CHECKPOINTS_v1.md`|存在，可读|
|`E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_PROTOCOL_FREEZE_v1.md`|存在，可读|
|`E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_0_2_ADJUDICATION_v1.md`|存在，可读|
|`E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_BACKBONE_PREPARATION_ADJUDICATION_v1.md`|存在，可读|

F、I 的指定部分亦存在并已读取。本轮只定向读取上述材料、证据目录、两份已封存 0.2 任务及必要的实现/审计源文件；未遍历论文目录。

### 1.2 读取范围、版本与完整性核对

本记录简称：K 为检查点文档，C 为研究合同，AC 为 G1.1 执行验收报告，RR 为运行记录，Pre 为封存预登记；AD02 为 0.2 裁决，B 为骨干准备归属裁决。引用定位列在文末。**本关所有 JSON 都只有第 1 行，因此 JSON 引用同时给出键或记录身份，以免仅靠行号无法定位。**

本轮编辑前实际 SHA-256 如下；该表记录的是当前裁决输入，而非声称所有文件都在执行时的基准提交内。

|输入|原始字节 SHA-256|
|---|---|
|AC|`1de225adfa3cc00c85bae57dca6b6b6aafa15c31762f3d71f0fe2066c6c8ee1f`|
|RR|`09d13c2be3bff83d00b7d633994c2bc49f019c28c70e4b05ff1888f0a5ff8463`|
|K|`8fe09ca87e9cdb5dd053a22e8ee3ba02a37d64f72dcc96e8987c338b8c09e98a`|
|C（本轮修改前）|`078a006d35a34ba196337461ee53d9bc73f48ffaf851f50f77ca20782ca2e1f9`|
|AD02|`a61ad0275f92375f3f667761dcc9cec9891bb5abce3dee2fbca3a31dc1dc9f7d`|
|B|`c863529137063c5cd9e39485b0445844cd3a837aa07512bf1c76f877d86ffd28`|
|F|`3a516ba17bc84c72b3da7fd69822a89e5b377a8730f5e6890eb4a3998a2392f4`|
|I|`818b2423c16a96e15c0f1e4fe9d6cc6993f3ece0fe9b085446ca71e29febaf5f`|

已读取 `artifacts/direction_a/phaseG1_1_v1/` 下实际存在的全部 **20 个文件**：

|类别|实际文件|
|---|---|
|预登记、机制与预定计划|`preregistration.md`、`mechanism.json`、`exogenous_plan.json`、`speed_assignments.json`|
|注册与支持|`registration_CIFAR10.json`、`registration_CIFAR100.json`、`support_CIFAR10.json`、`support_CIFAR100.json`|
|覆盖与诊断隔离|`coverage_plan.json`、`coverage_trace.json`、`diagnostic_channel_audit.json`|
|六份随机工程轨迹|`trace_CIFAR10_random.json`、`trace_CIFAR10_tail_slow.json`、`trace_CIFAR10_tail_fast.json`、`trace_CIFAR100_random.json`、`trace_CIFAR100_tail_slow.json`、`trace_CIFAR100_tail_fast.json`|
|验收、账本与清单|`acceptance.json`、`run.json`、`artifact_hashes.json`|

核对结果：

1. [Hashes L1][Hashes] 列出的 18 项原始字节 SHA-256 全部相符；其自身和运行账本不在该清单内。另将全部 20 文件分别与 `6ea9bd1:<对应路径>` 的 Git blob 比较，全部逐字节相同。清单自身 SHA-256 为 `23f421da8e074effbc668315d8330a5efb8ecb85facdec4ea905e880d48e8305`；[Run L1][Run] 的 SHA-256 为 `f6e5073814b6ecb05a5f18e896c1e223e9b19f3cbb41c16d597d63bf5007b63e`。
2. [Acceptance L1：preregistration_sha256][A] 与 Pre 的 `5b2dc116fafaa6828bb90f0fa0c933193989e3f5de3f0b83444c2c548ea8d050` 一致；Pre 33 行是当前 RR 的精确字节前缀，RR 随后附加最终摘要。入口源文件 [L58–64][Runner] 显示先保存预登记和输入指纹，再开始注册；[Run L1：actions][Run] 的首项是该预登记写入。这些证据支持执行先登记后运行的顺序，不将 Git 提交时间冒充预登记时间。
3. [Acceptance L1：implementation_sha256][A] 的六份实现/测试文件指纹均与当前字节一致。七项 `input_file_sha256` 中六项与当前字节一致；唯一不同是合同，差异已定位至后续 R07 和 G1 预算行同步，详见 §六.2。
4. 两份 [Registration L1：source_file_sha256][Reg10]、[Reg100] 指向的 0.2 `info/data/counts/acceptance.json` 共八个文件，均与原 0.2 清单及当前字节一致；注册消息中的计数数组逐项等于已有 `counts.json`，ACK 绑定实际上传字节哈希。仅比较封存数组、文件及索引编码哈希，没有读取原始 CIFAR 标签、重新划分或重算训练计数。

本轮只读核对还遍历了全部注册消息、支持记录、已有轨迹及账本条目，检查集合对应、身份/载荷哈希、事件链接、账本累计和精确分数等式；没有导入执行模块，没有调用生成器、回放器或测试入口。原报告的“可精确回放”由 [Acceptance L1：tests.replay][A] 及已封存实现证明其既有验收记录，本轮没有将它写成“再次回放通过”。原报告所述约 2.23 秒外部工具耗时未在这些账本中独立封存，本裁决不以它作为成本判据，采用 Run 的阶段/总耗时。[AC L46][AC]

## 二、G1.1 状态与逐条判据裁决

### 2.1 K 的节点判据核验

K §G1.1 第 4 项原文，见 [K L128][K]：

> 所有目标端注册成功，所有 `n_ic>0` 来源有 `q_i>0` 和 `r_i>0` 的机制依据；计划邀请与有效完成逐条可对应；空返回尝试仍被计入日志和预算；三种速度分配保持同一速度集合；固定工作量包含协议声明的新增计算；真实概率通道可单独审计。短轨迹必须覆盖按时、未派发、掉线、超时、全失败及重复 round 下不同 attempt。

下表裁决列均为 **[推断]**，限于 `FedPCC-G1.1-event-smoke-v1`，并须连同 §2.2 的正式状态读取。

|K 判据片段|直接核对的证据|本次裁决|
|---|---|---|
|所有目标端注册成功|Reg10/Reg100 L1 的 `registered_ids/messages` 各含 20 个端，任务身份分别绑定两份 0.2 完整任务；全 C 类含零计数逐项复制。上传/ACK 编码长度、SHA-256、端/任务身份及 train_split_hash 一致；两个任务的注册上/下行分别为 17100/3900、45837/3920 byte。不可变注册接口见 [Registration 源文件 L63–118][RegCode]。|本地回环协议范围成立；未把两个任务的同名端混作一次注册。未认证物理设备/网络接入不构成本关新增失败条件。|
|所有 `n_ic>0` 来源有 `q_i>0` 和 `r_i>0` 的机制依据|[Support10][Sup10]/[Support100][Sup100] L1 的 `nonzero_sources` 与原封存正计数位置逐项对应，无遗漏/重复；每场景 85/593 个来源，三场景合计 255/1779 条。120 条 `probabilities` 的 q、r、p 精确分数均正，每条来源引用匹配。机制与公式说明见 Mech L1、[诊断源文件 L30–59][DiagCode]。|条件正支持成立；不是从“这次每端都返回过”推得支持，也没有缩小总体。见 §2.3。|
|计划邀请与有效完成逐条可对应|六份 Trace 及 Coverage L1 的每条事件均绑定 task/attempt/round/version/client；每个返回能找到同端本次计划邀请、派发及相同 token，载荷哈希与解码身份一致；[事件源文件 L95–134][EventCode] 对应这条接收路径。|成立；q 的分母是过滤前计划邀请，r 的失败包含未派发和掉线。|
|空返回尝试仍被计入日志和预算|C100 tail_slow 的 `attempt_id=9` 无返回，仍在 32 次轨迹与 Run 的逐轨迹账本内；Coverage 的 attempt 1、2 连续全失败，round 序列为 0、1、1、1。Run L1 的 attempts=394，与逐轨迹累计及 actions 相符。|成立；没有增加次数凑返回，没有把模拟 round 当真实模型更新。|
|三种速度分配保持同一速度集合|[Speeds L1：各任务 assignments、speed_multiset_seconds_per_work_unit][Speeds]：每场景恰有 10 个 1 和 10 个 4；尾占比排序及并列端 ID 对应的偏慢/偏快集合相符；六份 Trace 的速度映射与各自任务/场景一致。|成立；配对改变对应关系，保持边际集合。|
|固定工作量包含协议声明的新增计算|Mech L1 的 `work_units/total_work_units/workload_status` 明列普通训练 1、参考类梯度扫描 1、特征范数统计 1/4、消息准备 1/4，合计 5/2；Pre L26 明说这是代理且未执行实际计算。|在代理模型内成立；不能据此认证 W01/W02 的实际批量、扫描口径、计算耗时或正式预算。这是正式资格尚未补齐的关键边界。|
|真实概率通道可单独审计|[Channel L1][Channel] 与 Acceptance 的隔离记录相同；逐个读取事件模块依赖，未导入离线诊断；逐条读取轨迹及解码 payload，未将真实概率作为实际事件/派发/返回输入。支持文件另存精确分数、连续对照与误差；[测试源文件 L238–267][Tests] 给出封存审计定义。|当前事件与注册接口范围成立。E05 预测器尚未实现，不把当前隔离检查当成未来完整方法的隔离认证。|
|短轨迹必须覆盖按时、未派发、掉线、超时、全失败及重复 round 下不同 attempt|[CoveragePlan][CovPlan]/[Coverage][Cov] L1 保存 4 attempts 的预定 fixture；六类事件计数为计划 32、派发 23、未派发 9、掉线 10、超时 2、返回 11，两次空完成。包含恰在 deadline 返回；非格点边界身份明确。标量边界与未注册端拒绝的既有核验见 [Acceptance L1：tests.scalar_oracles][A]、[Tests L73–97][Tests]。|成立；fixture 从随机经验率和支持证明中排除，不把强制覆盖当成随机研究重复。|

六份随机工程轨迹的全部条目已与 Acceptance 的 `random_trace_audits` 对照。下表是对保存日志的只读汇总，不是重新生成事件；每份均 32 attempts、256 次计划邀请、227 次派发、29 次未派发、14 次掉线。[六份 Trace L1：attempts/events][Traces]、[Acceptance L1：random_trace_audits][A]

|任务/场景|超时|有效返回|空完成 attempt 数|
|---|---:|---:|---:|
|[C10 random](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/trace_CIFAR10_random.json:1>)|74|139|0|
|[C10 tail_slow](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/trace_CIFAR10_tail_slow.json:1>)|67|146|0|
|[C10 tail_fast](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/trace_CIFAR10_tail_fast.json:1>)|69|144|0|
|[C100 random](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/trace_CIFAR100_random.json:1>)|74|139|0|
|[C100 tail_slow](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/trace_CIFAR100_tail_slow.json:1>)|61|152|1|
|[C100 tail_fast](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/trace_CIFAR100_tail_fast.json:1>)|75|138|0|

### 2.2 正式状态：证据不足，smoke 另记

K 共用规则原文包含：“smoke 通过另记，不能替代正式通过。”[K L84][K]；合同 W01 要求正式事件支持审计和训练前冻结训练工作量，W02 要求相应正式测量前冻结扫描口径与费用，E02/E03 要求正式支持审计/诊断前冻结机制，§六、§7.2 保留正式阶段额度的关闭条件。[C §四、§六、§7.2][C]

本次证据自身的限定为：

- Pre L3、10、26 将运行登记为事件 smoke，明确时长代理与正式工作量/预算的区别；Mech L1 的 `binding` 为 `event smoke only; no actual training/resource-budget freeze`。
- Acceptance L1 的 `actual_training_updates/forwards/gradient_requests` 均为 0，`paired_research_repeats=0`；事件 round 是逻辑完成槽，不是训练结果。正式 W01/W02 的具体协议及其资源测量并未由这些文件交付。
- Run L1 的 `hit=null`，各项实耗在此次有界额度内。故不能以“预算耗尽”解释未正式封版。

**[推断] 因此选择五个状态词中的“证据不足/预算耗尽”，并明确原因只为正式证据不足。** 不选择“修正后重跑”，因为本轮没有发现必须修复的事件实现错误；不选择“收窄后重验”，因为没有新增收窄总体或变更研究定义；不选择“停止当前范围”，因为条件支持成立且不存在该方向被否定的证据。AC L5 和 Acceptance 的 `G1.1_pass_within_declared_event_mechanism` 保留为执行层的实例结论，本记录不将它转换为 K 的正式“通过”。

**[推断] 这不是要求 G1.1 先做 G1.2、G1.3 或真实设备实验。** G1.1 尚需的正式交接是：对应实际协议的 W01/W02 工作量说明及所需成本测量、与该工作量绑定的正式 E01–E04 机制身份和有界额度，以及这些范围按 K §G1.1 的验收记录。可在 G1.2 输入准备/工作量测量的并行工作中取得相关信息，再回到 G1.1 核对；不新增“G1.2 通过后才能 G1.1”的依赖。[B §2.2–2.3、§3.2][B]、[K L61–64、88、130][K]

**[推断] 也不以“本关只有一组随机流”单独否定数学正支持证明。** 本次没有做误差/收益优势裁决；K L86 的研究配对重复要求仍留给适用的正式比较，六个任务/场景组合不能冒充三份独立重复。现有同身份的注册和结构证据可作为后续验收输入；是否足以复用须连同正式绑定记录审查，不要求为凑次数机械重做，也不能只换文件名就升级为主实验。[K L84–88、111][K]

### 2.3 正支持与误差的采纳边界

[推断] 采纳的是**给定声明随机机制的条件支持证明**。不是对某一固定种子序列宣称另有随机性，也不是物理设备完成率。依据：[Mech L1][Mech]、[Plan L1：draw_law、seeds][Plan]、Support10/Support100 L1 的 `sampling_law/channel`。

封存定义为固定数均匀无放回邀请，q=2/5；在线和未掉线的连续理想因子为 9/10、19/20，J=1/4+(3/2)U，D=speed×(5/2)×J，deadline=8。连续理想快/慢 r 为 171/200、627/2000，p 为 171/500、627/5000。实际登记的 U 格点 M=2^53；online、connected 的格点计数分别为 8106479329266893、8556839292003942，慢端 jitter 可完成格点数为 3302639726738364，快端全部可完成。[Mech L1][Mech]、[Sup10 L1：probabilities][Sup10]、[Sup100 L1：probabilities][Sup100]

本轮以这些已封存分数核对全部概率行及来源引用：q、r、p 均正；网格与连续差满足记录的 |Δr|≤3/M、|Δp|≤q×3/M，r 的 float64 展示误差另列。[诊断源文件 L16–59][DiagCode]、[Tests L40–63][Tests]。**[推断] 无需借用 0.2 的 logits `ε_num` 或新增概率数值阈值；精确分数是本实例的权威对象，展示浮点数不替代它。** 有限零返回依旧只表示观测不足。[K L129][K]、[F §一.2 L61、67][F]、[C §六 0.2 数值容差补录][C]

## 三、事项 3：参数身份、采纳范围与登记位置

**[推断] 纳入本轮裁决。** 这些选择决定 G1.1 支持成立的条件和成本范围，属于本次交付身份；本轮采纳为已执行 smoke 实例的登记，不替执行者另选数值、不追认正式主参数。C §四原表给出研究要求及待补子项，§7.3 允许通过可定位的记录补录。[C §四、§7.3][C]

|合同字段|当前证据及本次裁决（裁决均为 [推断]）|
|---|---|
|W01|普通训练代理工作量为 1；具体步数、批量、学习率、计算量尚未由本次测量或选定。接受代理登记，正式待办保留。Pre L26、Mech L1。|
|W02|参考扫描代理 1、特征范数统计代理 1/4；实际扫描样本量、频率、完整数据或小批量口径及相应成本未认证。接受代理登记，正式待办保留。Pre L26、Mech L1。|
|W03|接受两任务全部端的本地 UTF-8 回环注册及实际编码成本；bootstrap 早于全部 attempts，不受单次 8 模拟秒过滤。注册单次回环耗时分别约 0.0014552/0.0019969 秒；阶段账本含其他核验，不与这两个子计时混用。真实网络耗时不适用，不能填成已测 0。Reg10/Reg100 L1、Run L1。|
|W04、W05、W06|本次未运行合成匹配、重训、约束优化或直接分类器对照，均不解除原待实测状态。Acceptance L1：gradient_requests、payload_accounting；原字段仍留对应 G3 节点。|
|W07|事件 `event-slot-*` 是逻辑完成槽，不能当成 reference_id、checkpoint 或终点校准身份。参考点和校准频率仍未由本次选定。Pre L28–29、Trace L1：version_id、actual_model_updates。|
|E01|登记固定 20 端抽 8 端、均匀无放回、q=2/5；计划先于场景事件保存。invite seed=2026101301。接受本实例的定义与证据，不将当前 seed/32 次计划列为正式研究重复。Pre L24、Plan L1、Runner L103–120。|
|E02|登记每任务 10×1、10×4 秒/逻辑工作单位；最高尾占比 10 端在 tail_slow 取 4，tail_fast 取 1，并列按端 ID；random 使用 seed=2026101305 的预定排列。接受既有分配，不重排、不重算训练计数。Pre L25、Speeds L1。|
|E03|登记 D=speed×W×J、W=5/2、J=1/4+(3/2)U、deadline=8 模拟秒；在线 U<9/10，派发后掉线 U<1/20；U 为已声明独立格点流，online/dropout/jitter seeds 分别为 2026101302/03/04。接受条件机制及分数诊断；不认证实际端运行时长，不提升为正式机制冻结。Pre L24、26–31，Mech/Plan/Support L1。|
|E04|登记预定每主轨迹 32 attempts、触顶点 40、累计触顶点 512，覆盖/回放/测试均计；真实更新为 0，逻辑非空完成才推进 round。初始 200 更新轮与正式 attempt 上限仍按原合同处理。Pre L12–13、19、29，Run L1。|
|E05|接受“未实现实际预测器”的范围声明；事后比例不充当预测。先验、窗口、p_min、截断和搜索仍由 G2.1 登记/验收，不提前裁定。Acceptance L1：actual_predictor；Channel L1；C §四 E05。|

W 的第四项 `message_preparation=1/4` 与上述三项共同构成 5/2，仅为本实例时间模型的一部分，不是额外新增研究模块。[Mech L1：mechanism.work_units][Mech]

### 3.1 额度与实际账本

以下数值取自 [Pre L12–19][Pre]、[Mech L1：run_limits][Mech]、[Run L1：limits/counts/phase_seconds/trace_attempts][Run]；只登记既有选择，不裁定新的额度。

|项目|本次预登记额度|封存实耗或适用性|
|---|---|---|
|每随机轨迹/全部执行 attempts|每份预定 32、触顶点 40；累计触顶点 512|六份各 32；总 394=192 主生成+192 主回放+4 覆盖生成+4 覆盖回放+2 边界执行|
|统计/审计遍历|1024 个有名遍历触顶点|24；只是封存统计读取及审计，未重算训练计数|
|单机工作负载时间|总 300 秒；输入/注册 60、事件 90、审计/回放 90 秒|总 1.688 秒；startup 1.078、registration 0.078、events 0.250、audit 0.282 秒|
|注册本地编码|上/下行合计 1 MiB|70757 byte；真正的上/下行分别 62937、7820 byte，为本地编码载荷|
|事件本地元数据编码|2 MiB，包含回放/测试|1098062 byte；不含模型/梯度包，未发生物理网络发送|
|证据累计写入账本|16 MiB，含账本重复写与预扣 64 KiB 应急槽|记账 5262413 byte，减未动用的 65536 byte 预留为账本所记实写 5196877 byte；不是当前目录体积|
|搜索/修正重跑|搜索 0；最多 1 次修正重跑|0/0；Run 的 retries=2 是停止阈值，不是允许重跑 2 次|
|模拟系统时间|每主轨迹 32×8 模拟秒|每份 256 模拟秒，与单机计算时间分别报告|
|模型、梯度、实际预测器与网络|本次不执行|Acceptance 记录前向/更新/类梯度请求均为 0；网络发送量 null，模型/梯度载荷不适用|

[推断] 接受本次有界额度与实际账本，无触顶，无重新授权余额的含义。账本的停止语义是达到阈值即阻止下一动作；40、512 等不应被解释为还能执行到该值后再额外运行。依据：[预算源文件 L138–154][BudgetCode]、Pre L19。本轮只读裁决没有调用该工作负载，不把阅读文档的时间混入执行账本。

### 3.2 合同登记方式

**[推断] 在 C §四表后增加一次实例的补录引用，在 §7.2 的 G1.1/G1.2/G1.3 行更新“当前数值和正式放行状态”单元格；§六不改。** 采用引用登记可保留原字段的正式待办，避免把 smoke 额度覆盖正式额度。细节与预算数值以本节、Pre、Mech、Run 为准，登记日期为本裁决日期，不倒填为执行前正式冻结。C §2.2 R01–R05 的既有总体和 0.2 选择沿用 AD02；R03–R05 的历史正文同步待办不借本次重选或顺带改写。[AD02 §三 B2–B4、§五、§六][AD02]

## 四、事项 4：与后续节点的接口

**[推断] 检查点顺序、硬依赖、回退点以及 B 规定的候选快照接口均“无需调整”。** K G1.2 仍接收 0.2 和候选快照的生成配置/任务哈希；G1.1 与 G1.2 并行，二者完成后才到 G1.3。B §2.2 明确不新增“G1.1 通过后才能准备参考”的依赖；准备训练需记录自己实际采用的参与/完成口径，不能借用一次 smoke 替自己签定支持。[K L61–64、130、136、140、156–160][K]、[B L67、101–110][B]

本次需要登记的交接边界如下，均为 **[推断]**，是既有规则在真实文件上的定位，不是新接口实现要求：

|交接对象|交付与使用边界|依据|
|---|---|---|
|共同任务/注册身份|以两份 registration 的 task_identity、source_file_sha256、全 C 计数及逐端 train_split_hash 绑定既有任务；不以数据集名称或同名 client_id 代替完整身份。|Reg10/Reg100 L1；K §0.2 L121；B §3.2。|
|候选骨干准备与 G1.2|继续按 B 的 manifest、task_binding、checkpoint、generation_config、run_record、validation_record、handoff、哈希清单交付；本次没有新增候选包字段或参考资格阈值，也没有提供合格快照。|B §3.2–3.3；K §G1.2。|
|G1.3 的事件输入|已有 Mech、Plan、Speeds、注册/支持文件和六份 Trace 可作为 smoke 证据定位。正式使用须明确相应任务、工作量/机制身份与参考集合；本轮正式 G1.1 尚未封“通过”，故不能仅凭该包解除 G1.3 输入门。G1.2 也仍须独立验收。|K L84–85、156–161；C §四、§六；本记录 §二。|
|版本对应|Trace 的 version_id 只标事件逻辑槽；后续绑定合格参考必须明确实际 reference_id、模型/BN/head/变换身份，不能把槽编号当模型哈希或把不同参考的结果拼接。|Pre L28–29；B §3.2；K L138、161。|
|概率通道|q 可进入邀请日志；support 中真实 r/p 与外生未观测量留在模拟/离线诊断，不当 E05 的轮前预测输入。执行历史预测器时仍需 G2.1 对此前信息与更新顺序重新验收。|F §二 A1 L121–123；I 方向 A §2 A1 L85–89；K §G2.1。|
|范围变更|完成机制/工作量改变回 G1.1；split/count 改变回 0.2；参考改变回 G1.2/P。无需因为当前事件包不含训练快照而重开已完成 0.2；也不把代理支持自动扩展到不同工作量。|K L88、121；Acceptance L1：future_revalidation；B §四。|

## 五、事项 5：执行报告的待裁与未认证声明

AC 全文没有另列一个名为“待裁”的数值清单；其明确保留项主要出现在 L5、63、73、75、88、107、118–120，RR L10、26、29、31、37 也有对应限制。下表逐项与证据对应，裁决均为 **[推断]**。

|执行层保留/未认证项|证据核对|设计层处理|
|---|---|---|
|实际训练耗时、W01/W02 正式计算协议未冻结|Mech 的 binding/workload_status；Acceptance 的 forwards/updates/gradient_requests=0；Pre L26。|确属待补事项；接受代理实例，不补造实测值。这是正式 G1.1 尚不通过的范围资格原因，处理见 §2.2。|
|真实设备/网络接入未认证|Reg10/Reg100 的 transport、network_sent_bytes=null；Run 只记本地编码；没有网络测量文件。|认可限制；不把真实部署扩成 G1.1 新判据，也不把网络成本填零。以后若改变注册/完成环境，按相关节点验收。|
|模型质量、G1.2 冻结参考、G1.3 来源偏差未认证|全部 Trace 的 actual_model_updates=0；Acceptance 的 scope、gradient_requests；证据目录无模型或类梯度产物。|留原节点处理；本关不得替其通过。模型未训练不是在 G1.1 追加的精度失败项。|
|E05 未实现，事后比率不是预测器|Acceptance 的 actual_predictor、random_trace_audits.observed_rates.interpretation；Channel 的 actual_predictor_implemented=false。|留 G2.1；不要求本关顺手实现。AC L5 所说“不实现 A1”只按“未完成 A1 全模块/实际预测器”理解；已经交付的注册与事件子接口仍按本记录验收，不能因该简写抹去实际交付。|
|逻辑 round/version 不是真实更新/模型版本|Pre L28–29、Trace 的 version_id/actual_model_updates；Run 计的是 attempts。|保留该语义；不将 31/32 个逻辑完成槽列为训练更新。|
|连续理想概率与实现格点概率的区别、finite zero returns 的限制|Support 的 ideal/grid/error/finite_zero_returns；离线分数公式与各来源行一致。|采纳 §2.3 的条件解释；不改 §六 `ε_num`，不把连续近似或有限经验率替代权威概率。|
|范围内通过的自报状态|Acceptance 的 status 与 AC L5 一致，但 Mech/Pre 同时限定 smoke。|由本记录明确“smoke 成立、正式证据不足”；保留原报告和 JSON 作为历史材料，不反向改写。|

## 六、两条协调者观察

### 6.1 .gitattributes 追加：纳入工程影响登记，接受保留

本轮实际读取根文件，并核对 `git diff e3ca623 6ea9bd1 -- .gitattributes`：原 L1–9 未改，新增 L10–14。新增实质规则为：[.gitattributes L11–14][Attr]

|新增规则|影响与裁决（均为 [推断]）|
|---|---|
|`/artifacts/direction_a/phaseG1_1_v1/** -text`|覆盖本证据目录及未来放入其中的文件，禁止 Git 文本换行转换；不影响其他证据目录。|
|`/scripts/accept_direction_a_event_support.py text eol=lf`|只命中指定入口脚本。|
|`/tests/test_direction_a_event_support.py text eol=lf`|只命中指定测试文件。|
|`/docs/DIRECTION_A_G1_1_*.md text eol=lf`|覆盖本关报告及未来同前缀文档，包括本裁决记录；并非只影响本次已列的两个文档。|

实际 `git check-attr --all` 对 G1.1 账本返回 text unset，对上述入口/测试及本裁决路径返回 text set、eol lf；0.2 账本仍保留原 text unset 和 whitespace=cr-at-eol；合同、K 未命中这些规则。四份 event 源码继续受原 L6 的 `/direction_a/*.py` 规则约束，不是此次新增的全局规则。[Attr L3、5–14][Attr]

**[推断] 这不是修改用户/系统 Git 全局配置，也没有对全仓库统一强制换行；无需本轮调整。** 它与 AD02 §四的路径约束评估一致，只增加本关目录和文档前缀的作用域。后续 Agent 若批量规范化封存证据、改属性规则或让编辑器转换换行，仍可能破坏原字节哈希；-text 不能阻止编辑器改写。保留当前规则并记录这一影响，不据此新增工程任务或研究判据。[AD02 L173–190][AD02]、[Attr][Attr]

### 6.2 执行与裁决提交时序交叉：纳入版本来源登记，不据此判机制失效

本轮读取 Git 的父提交及提交时间，核对链条为：

|对象|可核验的时间/身份|
|---|---|
|执行基准|Acceptance L1 的 base_commit 为 `e3ca6236b04f4dd4bf4caf73e421083d6321dd8d`；AC L12 已说明当时合同有改动、AD02 尚未提交，并未宣称只读取干净 HEAD。|
|执行开始/结束|Acceptance L1：2026-10-13 11:24:18.039941 至 11:24:19.709933（+08:00）。|
|G1.1 交付提交|`6ea9bd191e1f2489670d37bb60cb42a737d401e7`，父提交 e3ca623，提交时间 11:36:27（+08:00）。其路径清单含 G1.1 文件与属性追加，不含合同、AD02、B。|
|随后裁决/合同同步提交|`e3c3528722cd4c4f55f96b37182255a4ade961b8`，父提交 6ea9bd1，提交时间 15:22:32（+08:00）；只包含合同、AD02、B 三文件。|

AC L32、RR L41 报告用户确认保留并排除 B；B L157 也记录其结束时出现 G1.1 运行记录的交叉现场。**[推断] 报告中的确认引语不单独作为本轮独立复核的用户授权证据；可独立核验的是文件实际被排除、随后独立提交及依赖内容是否冲突。** 本轮不向其他线程索取确认，也不因提交顺序晚就假定该文件当时不存在。

合同的执行时哈希为 `aaef7e3fc36764bcb38c397e55e4e49b67c2ca122039f3b149ab567eaeebadb8`，本轮修改前为 `078a006d35a34ba196337461ee53d9bc73f48ffaf851f50f77ca20782ca2e1f9`。[Acceptance L1：input_file_sha256][A] 本轮按本线程保存的执行前合同文本比较，仅 R07 行和 §7.2 G1 行不同；在内存中仅把当前这两行还原为同步前原文，保留原换行，所得原始字节 SHA-256 **恰为上述 aaef…**。未写回任何旧版本。两处新增内容分别对应 [B §五 L148–149][B]，没有改 W/E 事件定义、§六阈值或 G1.1 通过判据。

**[推断] 时序交叉应登记，但没有造成需要重跑 G1.1 的输入冲突。** 正确追溯单位为“基准提交 + 实际输入文件哈希 + 实现哈希”，不能只写一个基准提交而忽略当时未提交输入；也不能将当前合同哈希倒填入封存证据。B 本来不是此次事件执行输入，其候选准备归属与 G1.1 并行关系已在本轮作为裁决依据检查，和执行实例没有接口冲突。[B L67、75、101–110][B]

## 七、本轮合同更新与边界核对

本轮授权包含按裁决同步合同；实际更新限于以下两处：

1. **C §四字段表后增加“G1.1 已执行实例补录”。** 引用本记录 §三及 Pre/Mech；明确 W01/W02 代理、W03 本地注册与 E01–E04 事件参数的 smoke 身份、正式 G1.1 状态以及剩余待办。原 W01–W07、E01–E05 表格单元格保持不动。
2. **C §7.2 的 G1.1/G1.2/G1.3 行，仅更新“当前数值和正式放行状态”。** 引用本次已登记额度与实耗，说明不转正式额度/新运行授权；保留 G1.2/G1.3 待实测及正式识别裁决关闭。预算覆盖对象中先前登记的骨干生成/来源核验、验证选点、快照保存成本原样保留。

**[推断] 不改 C §六：**没有采纳新的数值阈值、正式 attempt 上限或正式阶段预算，不能用此 smoke 填掉正式待定项。不改 R01–R07、K、AD02、B、执行报告/运行记录/封存证据或任何代码；不改变检查点结构和回退点。不重新执行 G1.1、不生成新事件、不重划分、不重算训练计数、不训练、不 commit、不 push。

## 八、本轮未裁决、留待后续节点的事项

|事项|后续位置与恢复条件（均为 [推断]）|
|---|---|
|正式工作量、机制与资源绑定|按 C W01/W02、E01–E04、§六/§7.2 补交正式协议与有限额度及必要测量记录；在 G1.1 对其适用范围重新验收。未指定或猜测缺失数值，未授权本轮开跑。|
|真实端/网络成本|仅在后续实际选择该执行环境时登记/验收；不是此次必须补做的现场实验。当前仅有本地编码成本，不据此承诺网络成本。|
|合格骨干、多个参考点、类梯度与测量容差|继续属 G1.2 的准备/接收/测量，按 B §三交付；不以 G1.1 当前正式状态阻断允许并行的候选准备。|
|来源偏差大小及正式识别|仍由 G1.3 在 G1.1/G1.2 满足输入条件后按 `ε_bias`、预定参考/场景与重复要求裁决；当前正支持不等于已证明来源偏差。|
|E05 实际历史概率预测与诊断隔离|G2.1；本次的事后观察率和离线真实概率不能替代轮前预测验收。|
|P、G2/G3、后续完整方案|按原门槛与预算推进；本轮不选择阈值、搜索范围或宣告收益。|
|R03–R05 正文同步|AD02 已裁定的定义继续生效；这一历史文档维护待办未在本次事件裁决中改写，也不重新开放选择。|

依据：[K §一、G1.2、G1.3、G2.1][K]、[C §四、§六、§7.2–7.3][C]、[B §三–四][B]、[AD02 §六][AD02]。这些是已明示的未来交付，不是缺少本次裁决所需的既存输入文件。完成本轮后等待协调者确认。

## 引用定位

下列均为本项目实际文件；JSON 除特别说明均为 L1，正文另给键。六份 Trace 的逐文件路径在 §1.2 列齐，统一位于 Traces 链接所指目录；使用表中任务/场景可唯一定位，文件本身均为 L1。

[K]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_CHECKPOINTS_v1.md:52>
[C]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md:113>
[AC]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_G1_1_ACCEPTANCE_v1.md:1>
[RR]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_G1_1_RUN_RECORD_v1.md:1>
[AD02]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_0_2_ADJUDICATION_v1.md:115>
[B]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_BACKBONE_PREPARATION_ADJUDICATION_v1.md:57>
[F]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:54>
[I]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:83>
[Pre]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/preregistration.md:1>
[Mech]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/mechanism.json:1>
[Plan]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/exogenous_plan.json:1>
[Speeds]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/speed_assignments.json:1>
[Reg10]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/registration_CIFAR10.json:1>
[Reg100]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/registration_CIFAR100.json:1>
[Sup10]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/support_CIFAR10.json:1>
[Sup100]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/support_CIFAR100.json:1>
[CovPlan]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/coverage_plan.json:1>
[Cov]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/coverage_trace.json:1>
[Channel]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/diagnostic_channel_audit.json:1>
[A]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/acceptance.json:1>
[Run]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/run.json:1>
[Hashes]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/artifact_hashes.json:1>
[Traces]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phaseG1_1_v1/>
[Runner]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/scripts/accept_direction_a_event_support.py:39>
[RegCode]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/direction_a/event_registration.py:63>
[EventCode]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/direction_a/invitation_events.py:54>
[DiagCode]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/direction_a/event_diagnostics.py:12>
[BudgetCode]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/direction_a/event_protocol.py:138>
[Tests]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/tests/test_direction_a_event_support.py:38>
[Attr]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/.gitattributes:1>
