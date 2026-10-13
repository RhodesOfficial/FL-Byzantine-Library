# G1.1 训练计数、邀请完成事件与正支持验收 v1

日期：2026-10-13（Asia/Shanghai）。根目录：`E:\Federated Machine Learning\FL-Byzantine-Library-astra`。解释器：`E:\anaconda3\python.exe`。本次基准提交 `e3ca6236b04f4dd4bf4caf73e421083d6321dd8d`。

**结论：G1.1 在本记录声明的事件机制与本地注册范围内通过。** 两份已由 0.2 裁决封版的任务各 20 端全部注册；六份预选随机轨迹和一份独立短覆盖轨迹可精确回放；所有 `n_ic>0` 来源均有 `q_i>0`、`r_i>0` 的机制依据；真实概率通道独立可审计。未发现设计与实现冲突。此通过不认证真实设备接入/网络、实际训练耗时、模型质量、G1.2 冻结参考或 G1.3 来源偏差；不运行 FedAvg，不实现 A1/A2/A3 或 E05 实际预测器。

## 预检与输入身份

|项|本次预检实际结果|
|---|---|
|分支|`feature/direction-a`，符合期望|
|git status|与 origin 分支同步；既有改动为 `M docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md`、未跟踪 `docs/DIRECTION_A_0_2_ADJUDICATION_v1.md`，保留原样，不加入本关提交|
|最近 3 个 commit|`e3ca623 phase0.2: baseline protocol and model acceptance`；`902af7e docs: add non-attack research base and direction selection`；`9d0cfa8 Merge remote-tracking branch 'origin/master'`|
|解释器|`E:\anaconda3\python.exe` 存在，全部 Python 调用均显式指定并使用 `-B`|

以下四个必需文件存在、可读；实际路径如下：

- `E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_CHECKPOINTS_v1.md`
- `E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_PROTOCOL_FREEZE_v1.md`
- `E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_0_2_ACCEPTANCE_v1.md`
- `E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_0_2_ADJUDICATION_v1.md`

已读取 K 的 G1.1 七项全文；合同 R01–R05、W02/W03、E01–E05、attempt/时间/字节/搜索额度及 §7.2 G1 行；I 方向 A 模块 A1；F §一.2/§二 A1。0.2 裁决明确将完整候选任务作为已封版基础任务，不修改其历史 candidate/pending_review 名称与 JSON 状态。

本关只读以下两目录的 info/data/counts/acceptance：

- `artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR10-N20-v1/`
- `artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR100-N20-v1/`

每文件与 0.2 清单及 info 内层 SHA-256 匹配；清单本身与基准 Git blob 匹配。运行结束又核对全部八个文件原始字节不变。没有打开原始 CIFAR 标签、没有调用 0.2 builder/audit/计数器，不重算 `n_ic/N_c/a_ic`，不生成新索引。注册中每端 train_split_hash 是对封存 train 索引数组的确定性 UTF-8 编码求哈希，不是重新划分。运行前六文档、任务身份和最终六实现文件的哈希保存在 `acceptance.json`。

执行期间新增 `docs/DIRECTION_A_BACKBONE_PREPARATION_ADJUDICATION_v1.md`；已向用户报告并获得“是，保留并排除提交”的明确答复。它不作为本关输入，不修改、不提交。

## 运行额度与实耗

运行前原文在 `DIRECTION_A_G1_1_RUN_RECORD_v1.md` 登记，并精确封存到本关 `preregistration.md`；后者的哈希写入 acceptance。事件元数据上限在任何运行开始前，按生成/回放/测试全部成本选定为 2 MiB，运行中没有扩额。

|额度项|预登记有限值|实际/状态|
|---|---|---|
|数据集、N、C|已封存 CIFAR-10-LT/CIFAR-100-LT；均 N=20，C=10/100|两总体全部使用；IF/α/分组沿用 0.2 裁决，不替换数据|
|相对主设置缩小|保留 20 端、40% 邀请、三种同速度集合；每场景只 32 个事件 attempt、一个种子组；无 200 更新轮训练、3 个研究重复或模型/类梯度计算|固定配置，没有以 G2 或返回数筛轨迹|
|计划邀请数/次|8/20，均匀无放回，q=2/5|每主轨迹 256 条计划邀请，共 1536 条；派发后人数不作为 m|
|每主轨迹 attempt|预定 32，上限 40|六条各 32；原生生成共 192|
|所有执行累计 attempt|512，生成/回放/独立测试共用|394=192 主生成+192 回放+4 覆盖生成+4 覆盖回放+2 标量边界执行|
|统计/审计遍历|1024 个有名只读/公式/日志遍历|24；不从原始标签重新计数|
|单机时间|300 秒；输入/注册 60、事件 90、审计/回放 90|封存 ledger 1.688 秒：startup 1.078、registration 0.078、events 0.250、audit 0.282；解释器/工具完整执行约 2.23 秒另作外部观察值，不混入阶段计时|
|注册编码上/下行|合计 1 MiB|70757 byte，本地实际编码/解码/ACK；真实网络发送未执行|
|事件元数据编码|合计 2 MiB|1098062 byte；含生成、回放及边界测试；没有模型/梯度包|
|证据写入|16 MiB，含账本重复写及 64 KiB 应急槽|额度记账 5262413 byte（含预扣 65536 byte 应急预留）；未使用应急槽，运行证据实写 5196877 byte；验收说明文本另列为文档交付|
|搜索/修正重跑|搜索 0，最多修正重跑 1 次，费用不得清零|0/0；预算文件的重跑触顶点为第 2 次（即最多允许 1 次）|
|前向/训练/类梯度/校准/实际预测器|全部不执行|全部 0；进程未导入 torch|
|触顶动作|任一上限到达即停、保存已有证据/命中字段，不扩额、不凑结果、不提交通过 commit|未触顶；attempt、阶段/总时间、字节上限的手写边界测试通过|

## 注册清单与 W03 账本

端 ID 在两个任务中均为 `client_000`–`client_019`；完整身份为 `(task_identity,client_id)`，不能把两任务的同名端混为一份注册。全 C 标签、零计数也完整传递。每端消息包含封存 `n_ic/N_c/a_ic`、class_ids、任务文件 SHA-256、train_split_hash；ACK 绑定 upload SHA-256。接收端确实从编码字节解码，校验后存入 MappingProxyType 注册表；单端记录为 frozen dataclass，其计数为 tuple。独立测试核对每消息与封存来源一致，并拒绝未注册端邀请。

|任务|目标端/成功端|标签维度|上行 UTF-8 byte|下行 ACK byte|回环注册耗时|
|---|---:|---:|---:|---:|---:|
|CIFAR10|20/20|10|17100|3900|0.0014552 秒|
|CIFAR100|20/20|100|45837|3920|0.0019969 秒|

注册输入分别是 0.2 的 11165/9754 个最终训练样本对应计数；不重登记一份不同总体。注册处于独立 bootstrap 阶段，早于全部 attempt，不受每次 8 秒模拟截止时间过滤；其时间/字节单列，不算免费首次接入。这里是本地内存回环协议验收，不声称设备和物理网络已经注册成功，真实网络发送和带宽耗时记不适用。

证据：`registration_CIFAR10.json`、`registration_CIFAR100.json` 保存完整 40 条 upload/ACK 原始 UTF-8、长度、SHA-256、状态和逐端计时。

## 固定机制与可回放事件

每次均匀无放回选择 8 端；在线条件 `U_online<9/10`，否则记录 not_dispatched；派发后 `U_drop<1/20` 掉线。三个独立 U 流使用 NumPy PCG64 53 位格点，种子分别 invite=2026101301、online=2026101302、dropout=2026101303、jitter=2026101304；速度随机排列 seed=2026101305。计划/逐端潜变量先保存并求哈希，再生成场景，不从本轮未观测梯度或 G2 误差选择邀请/轨迹。

同一 20 端集合恰有 10 个 speed=1、10 个 speed=4（秒/逻辑工作单位）；三种分配的多重集合精确相同，慢/快中位耗时比 4。尾类占比仅由已有 n_ic 的冻结 tail 列及 acceptance 中已有端训练总数派生；并列按端 ID。偏慢将最高 10 个占比端设慢，偏快反向；随机场景一次预定排列。两个数据集的每场景均保存全部 20 端速度与尾占比分数，不用同数据集名称代替实际绑定。

每次固定 W=5/2 工作单位：ordinary_training=1、reference_class_gradient_scan=1、feature_norm_statistics=1/4、message_preparation=1/4。新增统计/类梯度逻辑成本没有从时间模型省略，但全部是本次时长代理，不实际计算。此处不冻结 W01/W02 的模型批量、扫描/FLOPs 或实际训练耗时；真实计算需相应后续节点补测，改变工作量必须回 G1.1 重新支持审计。

J=1/4+(3/2)U_jitter；D=speed*W*J；固定 deadline=8 模拟秒，D<=8 有效返回；掉线检测 min(D/2,deadline/2)；超过截止不接受迟到包。主轨迹每份为 32*8=256 模拟秒，不与实际计算时间相加。version_id 是逻辑完成槽 token，不是模型 checkpoint；round_id 是若接训练将推进的逻辑槽，空完成不推进，非空完成推进；实际模型更新仍为 0。

六个主轨迹文件都保存过滤前计划邀请、派发、掉线、超时、有效返回五类事件，并额外显式保存未派发原因。每事件有 client/attempt/round/version/task、时刻、原因；返回绑定相同 invocation 和 dispatch token。事件 ID 的作用域是其 trace_id，完整键为 `(trace_id,event_id)`。

|主随机轨迹（均 32 attempts）|计划邀请|派发|未派发|掉线|超时|有效返回|空完成 attempt|
|---|---:|---:|---:|---:|---:|---:|---:|
|C10 random|256|227|29|14|74|139|0|
|C10 tail_slow|256|227|29|14|67|146|0|
|C10 tail_fast|256|227|29|14|69|144|0|
|C100 random|256|227|29|14|74|139|0|
|C100 tail_slow|256|227|29|14|61|152|1|
|C100 tail_fast|256|227|29|14|75|138|0|

C100 tail_slow 自然产生的空返回照记，没有增加 attempt 凑返回数。每轨迹全部 20 端在这次有限观察中均至少有一次返回；**正支持结论仍来自机制，不来自这一观察**。逐端邀请/派发/返回次数及事后邀请率、以计划邀请为分母的完成率保存于 acceptance，标明“事后描述，不是预测器”。

独立短轨迹 `coverage_trace.json`（4 attempts）有计划邀请 32、派发 23、未派发 9、掉线 10、超时 2、有效返回 11、空完成 2。round 序列 `[0,1,1,1]`，attempt ID `[0,1,2,3]`：连续两个全失败仍计入预算，round 不推进。恰在 deadline 返回通过、一个格点步长后超时、在线/掉线严格阈值及未注册端拒绝均有手算对照。恰在 deadline 的 `U=11/30` 是非格点边界 fixture，不声称随机数能够抽到它；整份 fixture 不参与随机经验率或支持证明。

六份主轨迹和覆盖轨迹均从落盘计划/潜变量再读入回放，逐字段精确一致；另外使用独立标量分数公式核对事件分类、时间和邀请→派发→返回关系，不以“同一程序重跑相同”作为唯一证据。

## 每个非零来源的正支持与诊断概率

邀请 q 的独立组合数公式为 `C(19,7)/C(20,8)=2/5>0`。在线、连接、jitter 与邀请/标签/梯度独立，r 对应“给定计划邀请的有效完成”，未派发/掉线均在失败分母中。

连续理想模型的 `r=(9/10)*(19/20)*CDF_J(8/(speed*5/2))`，`p=q*r`：

|速度|最大/最小 D（模拟秒）|CDF 条件|r 理想值|p 理想值|
|---|---|---|---:|---:|
|快 1|0.625–4.375|始终在 8 秒以内，CDF=1|171/200=0.855|171/500=0.342|
|慢 4|2.5–17.5|J<=4/5，CDF=11/30|627/2000=0.3135|627/5000=0.1254|

实际 U 使用 M=2^53 个等距点。严格 `<a` 有 `ceil(M*a)` 个点，`<=b` 有 `floor(M*b)+1` 个点并截到 0..M；诊断以 Fraction 精确给出格点 r_true/p_true，而不是把连续近似直接冒称实现概率。独立参照包含手写 53 位格点基数和独立枚举的四点格；q 也以 N=5,m=2 的 10 个组合、每 ID 出现 4 次作手算检验。

实际网格分量为 online `8106479329266893/M`、connected `8556839292003942/M`；快 jitter CDF=1，慢 CDF=`3302639726738364/M`。因此两类速度的实际 r_true/p_true 均严格为正。每行还保存网格/连续绝对差的精确分数与界：`|Δr|<=3/M≈3.33067e-16`、`|Δp|<=q*3/M`；r 的 float64 展示舍入另以分数给出，权威值是 exact Fraction，float 只是展示。没有使用 Monte Carlo 近似或观察返回率作为真实概率来源，也不沿用 logits ε_num 去认证概率。

|任务|每场景非零端类来源|三场景逐来源支持记录|q>0/r_true>0/p_true>0|
|---|---:|---:|---|
|C10|85|255|全部通过|
|C100|593|1779|全部通过|

两份 support 文件逐个列出 `(scenario,client_id,class_id,n_ic)` 与概率行引用；独立集合检查覆盖每个封存 n_ic>0 来源且没有重复/遗漏，合计 2034 条记录。有限零返回应记观测不足，不是 p=0；此原则作为解释固定，即使本次主轨迹没有零返回端也不改变。

## 真实概率通道的独立审计

`direction_a/event_diagnostics.py` 只供离线验收读取声明机制/速度/封存计数；事件模块与注册模块不导入它。邀请策略输入只有注册端 ID、固定 m、预定随机流；事件完成由独立 draw 与机制条件计算，接口没有 r_true/p_true。

`diagnostic_channel_audit.json` 记录 AST 导入依赖检查及递归 payload 检查：事件观察、派发/返回编码包均无 r_true/p_true/r_hat/p_hat/p_min/p_tilde。已知 q 允许记录；理想与网格真实概率单独存于 support，不进入实际策略。没有 ProbabilityEstimator、平滑、截断、窗口或下一轮预测，没有 A2 缓存与 A3 校准，也没有 G2 误差供筛选。

## 文件清单与提交边界

本次新增 28 个文件，另仅修改 `.gitattributes` 为本关证据设置精确字节保留，并为本关入口/测试/文档指定 LF；不改旧模式、easyFL、0.2 封存证据或现有算法。以下根目录均为项目根：

|路径|文件|
|---|---|
|项目根|`.gitattributes`（本关路径追加）|
|`direction_a/`|`event_protocol.py`, `event_registration.py`, `invitation_events.py`, `event_diagnostics.py`|
|`scripts/`|`accept_direction_a_event_support.py`|
|`tests/`|`test_direction_a_event_support.py`|
|`docs/`|`DIRECTION_A_G1_1_RUN_RECORD_v1.md`, `DIRECTION_A_G1_1_ACCEPTANCE_v1.md`|
|`artifacts/direction_a/phaseG1_1_v1/`|`preregistration.md`, `mechanism.json`, `exogenous_plan.json`, `speed_assignments.json`, `registration_CIFAR10.json`, `registration_CIFAR100.json`, `support_CIFAR10.json`, `support_CIFAR100.json`, `coverage_plan.json`, `coverage_trace.json`, `diagnostic_channel_audit.json`, `acceptance.json`, `run.json`, `artifact_hashes.json`|
|同证据目录|`trace_CIFAR10_random.json`, `trace_CIFAR10_tail_slow.json`, `trace_CIFAR10_tail_fast.json`, `trace_CIFAR100_random.json`, `trace_CIFAR100_tail_slow.json`, `trace_CIFAR100_tail_fast.json`|

合计本关提交对象 29 个。SHA-256 清单覆盖封存证据（不包括自身/运行账本）；运行账本由 Git 逐字节对照保存。暂存前核对不存在本关产生的 outputs、.idea、临时脚本、__pycache__ 改动；仅显式 `git add` 本表文件，不加入用户已有合同、0.2 裁决或用户已确认的骨干裁决。一次最终提交，消息 `phaseG1.1: invitation and completion event support`；hash 在最终答复给出，不写提交自引用。不 push，完成后停在 G1.1 等确认。
