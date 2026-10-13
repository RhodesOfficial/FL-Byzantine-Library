# 方向 A（FedPCC）0.2 基础口径验收裁决记录 v1

日期：2026-10-13（Asia/Shanghai）。裁决基准提交：`e3ca6236b04f4dd4bf4caf73e421083d6321dd8d`。

**[推断] 裁决：0.2 以“通过”封版。** 通过对象是本记录列明的两份 smoke、两份完整规模基础任务及已测模型适配、评价口径；不将此状态解释为 G1.1/G1.2 或正式训练实验已经通过或获准运行。依据：[K §0.2 第 3–7 项][K02]及本记录 §二、§三的逐项核验。

**这是本裁决记录的建议组织方式：**按现场与证据身份、0.2 判据、五个待裁项、工程改动、合同更新、后续事项排列。文件名采用 `DIRECTION_A_0_2_ADJUDICATION_v1.md`，保留方向、检查点和版本标识，以“ADJUDICATION”区别执行验收报告与运行记录。本文件是设计层裁决，不改写执行时封存的候选状态。

## 一、现场与证据身份

### 1.1 环境预检

以下为本轮修改前实际读取结果；三条 Git 命令均在 `E:\Federated Machine Learning\FL-Byzantine-Library-astra` 执行，目录存在。只读 Python 操作显式使用 `E:\anaconda3\python.exe`。

|预检项|实际结果|
|---|---|
|`git branch --show-current`| `feature/direction-a`，符合期望|
|`git status`|工作区干净；本地分支与 `origin/feature/direction-a` 同步|
|`git log --oneline -5` 第 1 条|`e3ca623 phase0.2: baseline protocol and model acceptance`|
|第 2 条|`902af7e docs: add non-attack research base and direction selection`|
|第 3 条|`9d0cfa8 Merge remote-tracking branch 'origin/master'`|
|第 4 条|`0cc8aa3 update papers`|
|第 5 条|`8ff3e14 merge: D1 branch (failed experiment, infrastructure retained for D2')`|

|必需文件实际路径|存在性|
|---|---|
|`E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_0_2_ACCEPTANCE_v1.md`|存在，已全文读取|
|`E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_0_2_RUN_RECORD_v1.md`|存在，已全文读取|
|`E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_PROTOCOL_FREEZE_v1.md`|存在，已读取指定判据|
|`E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_CHECKPOINTS_v1.md`|存在，已读取指定判据|
|`E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_FEASIBILITY_v1.md`|存在，已读取任务、模型、评价、成本及测试选择依据|

### 1.2 证据索引与本轮核验方法

本节别名只用于定位，均指向实际文件。四个任务目录名完整保留，不将 smoke 改名为正式任务。

|任务身份|配置与索引|计数与独立验收|
|---|---|---|
|`FedPCC-0.2-smoke-CIFAR10-v1`（S10）|[info.json][S10I]、[data.json][S10D]|[counts.json][S10C]、[acceptance.json][S10A]|
|`FedPCC-0.2-smoke-CIFAR100-v1`（S100）|[info.json][S100I]、[data.json][S100D]|[counts.json][S100C]、[acceptance.json][S100A]|
|`FedPCC-0.2-candidate-CIFAR10-N20-v1`（C10）|[info.json][C10I]、[data.json][C10D]|[counts.json][C10C]、[acceptance.json][C10A]|
|`FedPCC-0.2-candidate-CIFAR100-N20-v1`（C100）|[info.json][C100I]、[data.json][C100D]|[counts.json][C100C]、[acceptance.json][C100A]|

本轮完整解析指定的六个公共证据文件及上述十六个任务文件；只读取封存索引、计数和测量值，核对已有字段的一致性与文件 SHA-256。没有调用任务生成器、计数器、验收脚本、模型或测试函数。为确认 `data_pass` 的具体含义，定向阅读了已有核验逻辑与手算对照，而未执行它们：[task.py L174–259][TaskAudit]、[tests L15–59][Tests]。因此，下文关于索引守恒和逐端计数的通过结论来自已封存的独立核验及其代码身份，不冒称本轮重新从标签计数。

本轮只读哈希检查结果：

- [artifact_hashes.json L2–21][Hashes] 登记的 20 个文件全部逐字节匹配；四份 `info.json/artifact_sha256` 的内层校验也全部匹配。`counts.json/N_c` 和分组与各自 `acceptance.json` 的对应字段一致。
- [verification.json L39–47][Verify] 登记的 7 个实现文件哈希全部匹配；C10/C100 `info.json/source_file_sha256` 登记的 8 个原始数据文件逐字节匹配。本轮只读原始文件做哈希，不解析标签、不重算计数。
- [preregistration.md][Pre] 的原始字节是 [RUN_RECORD][RunRecord] 的前缀，其 SHA-256 为 `61622c4dc166dbfa5fcaa81b29e014e4cc6f97fecea1f740df03c59ffd843a82`，与 [summary.json L31][Summary] 一致。追加核验额度独立记在 RUN_RECORD L36–38。
- 清单不包含 `run.json` 自身。本轮另外核对它与基准提交中的同一路径逐字节一致，SHA-256 为 `fee816acb4312ea8b43052101b7301cf2c9875b2a63ab9ccf048fae7096e4241`；不把“20 项清单通过”写成全部文件均由该清单覆盖。

**输入文档哈希的换行差异单独登记。** [summary.json L22–28][Summary] 保存执行时输入的原始字节哈希。本轮修改前，K、F、合同的工作区为 CRLF，登记值对应的 Git 基准版本为 LF；将工作区 CRLF 转为 LF 后，三者分别与登记值逐字节哈希匹配。仅在内存比较，没有改写输入文件。具体如下：

|输入|执行时登记 SHA-256|本轮修改前工作区 SHA-256|核验结果|
|---|---|---|---|
|K|`7477775cba2ed891b5b324a9b70b010aaec96b39612e37155e7dea5413b19986`|`8fe09ca87e9cdb5dd053a22e8ee3ba02a37d64f72dcc96e8987c338b8c09e98a`|基准提交字节匹配登记值；差异仅 CRLF/LF|
|F|`9f8659f9c4bf1168ebc2d4ace6f6ebac4c4d98624314f44f9174a583ab74005d`|`3a516ba17bc84c72b3da7fd69822a89e5b377a8730f5e6890eb4a3998a2392f4`|同上|
|合同|`1ffeba3f73e64e5a795df17c1dc9b4de8cedf69dc215c7c2777c9db15df8d8fe`|`70e31c19b25a5ff825e1d980c9b124a9179b9968fef949956bec80c6347f53bd`|同上；本轮 §6 修订另成新版本|

另外两份登记输入 S、I 的工作区原始字节直接匹配登记值；I 的工作区为 CRLF，不能统一假定所有登记输入均按 LF 计算。[推断] 这些检查足以把本次裁决绑定到执行时研究文本；不能据此声称三份工作区原始哈希未变，也不能对任意未来哈希不符直接用“换行差异”放行。

## 二、0.2 通过判据逐条核验

K §0.2 第 4 项原文如下：[K L118][K02]

> 先做小样本基础 smoke，再验收正式任务：索引守恒、约定集合互斥；逐端训练计数加和等于总体训练计数；类别维度分别为 10/100；缺类、单来源、多来源均显式记录；模型完整前向与 encode/head 拼接结果在 `ε_num` 内一致；参数、BN、损失及变换定义齐备；独立客户端测试和头/中/尾分组规则确定。正式任务不因 smoke 通过而免检。

### 2.1 数据交付实况

以下数值取自各任务 `acceptance.json` 的既有字段，不是本轮重算结果；分组、缺类和来源清单另存于相应 `counts.json`。

|任务|N × C|train / validation / test|舍弃 train / 未用 test|实测 IF|零来源 / 单来源 / 多来源类数；缺失端类对|
|---|---|---|---|---|---|
|S10|4 × 10|242 / 20 / 80|49738 / 9920|100|0 / 6 / 4；23。依据：[S10A L46–90][S10A]、[S10C][S10C]|
|S100|4 × 100|2131 / 200 / 800|47669 / 9200|100|0 / 55 / 45；238。依据：[S100A L136–360][S100A]、[S100C][S100C]|
|C10|20 × 10|11165 / 1000 / 10000|37835 / 0|100|0 / 0 / 10；115。依据：[C10A L110–153][C10A]、[C10C][C10C]|
|C100|20 × 100|9754 / 1000 / 10000|39246 / 0|112.5|0 / 0 / 100；1407。依据：[C100A L200–423][C100A]、[C100C][C100C]|

四份配置的任务划分 seed 均为 `20261012`；模型数值测量另用初始化 seed `20261012/20261013`，身份为零训练步随机初始化。[S10I][S100I][C10I][C100I] 的 `spec`；[Model L18–83][Model]。[推断] 这属于基础工程验收，不是主实验的三个配对重复；不解除 [K 共用规则 L86][KRule] 的后续配对重复要求。

### 2.2 逐条裁决

下表“裁决”列均为 **[推断] 本次设计层裁决**，不是执行 Agent 自行宣布的正式状态。

|K §0.2 第 4 项的判据片段|核对的封存证据及含义|裁决|
|---|---|---|
|先做小样本基础 smoke，再验收正式任务|[run.json L29 起 events][Run] 中每个数据集均先 smoke，再单独构建/验收 20 端候选；四份 acceptance 均为 `data_pass`。逐任务落盘后还执行过独立复核，见 [task.py L243–259][TaskSave]。|通过。完整规模任务独立受检，没有用 smoke 替代。|
|索引守恒、约定集合互斥|四份 data 的 `index_namespaces`、train/validation/discarded、client test/global test/unused 明确；四份 acceptance 的 `independent_reference` 为集合守恒与独立标量核验。核验断言覆盖范围、重复、客户端间互斥及全集守恒，见 [task.py L181–200][TaskAudit]；负例记录见 [Summary L1110–1116][Summary]、[tests L40–59][Tests]。|通过。允许的唯一视图重叠是 global test 等于 client test 的并集；跨 official_train/test 的同号索引不是同一记录。|
|逐端训练计数加和等于总体训练计数|四份 counts 保存 `n_ic/N_c/a_ic`，与各自 acceptance 对应；独立核验由落盘索引及标量标签生成参照，核对矩阵和逐类加和，见 [task.py L202–212][TaskAudit]。|通过。冻结现有计数，不要求本轮重新生成。|
|类别维度分别为 10/100|四份 info 的静态 label_mapping、acceptance 的 `matrix_shape` 分别为 4×10、4×100、20×10、20×100；模型两头维度也分别为 10×128、100×128。[Model L3597–3640][Model]。|通过。完整标签空间保留。|
|缺类、单来源、多来源均显式记录|§2.1 所列来源及缺失端类对有完整清单；counts 的 `empty_train_clients` 均为空，零来源类也以空清单显式记录。独立核验涵盖来源数与缺类，见 [task.py L219–226][TaskAudit]。|通过。完整任务没有单来源类，也显式登记“无”；没有把静态来源数当成完成概率支持证明。|
|模型完整前向与 encode/head 拼接结果在 ε_num 内一致|[Verify L8–12][Verify] 最大 L∞/Frobenius 差均为零；[Model measurements L86–3591][Model] 保存两数据集、两初始化、CPU/CUDA、实际图与零输入逐项结果。B1 采纳限定范围的 `1e-6`。|通过。须连同精确一致性与独立参照约束读取。|
|参数、BN、损失及变换定义齐备|[Model L3597–3645][Model] 保存 308650/320260 参数、128 维特征、有 bias 头、9 个 BN、eval 及运行缓冲身份、raw logits 与均值 CE；[Verify L69–100][Verify] 保存 float32、RGB /255、各数据集 mean/std、无增强变换。|通过。仅基础适配验收，不认证训练模式、训练质量或参考资格。|
|独立客户端测试和头/中/尾分组规则确定|完整任务每端均为 500 图、覆盖全部 10/100 类，见 C10A L22–65、C100A L112–155。counts 保存分组；原规则按训练数降序、并列按类 ID、两切点为 floor(C/3)、floor(2C/3)，见 [task.py L99–103][TaskBuild]。|通过。测试选择按 B4 采纳；固定现有分组与尾类持有端清单。|

依据 [K §0.2 第 3 项][K02]，除上述判据，还核对了任务清单、最终索引/哈希、评价分母和成本说明。评价分母的手算与缺失值对照已记入 [Summary L1110–1116][Summary]；具体规则见 [AC §六 L113–118][AC]，并由 [evaluation.py L8–39][Evaluation] 与 [tests L23–38][Tests] 对照核实。[推断] 该交付满足本关“规则与基础”要求，不代表已生成正式模型精度结果。

### 2.3 有限额度与合同输入的对应

[RunRecord L9–20、36–42][RunRecord] 与 [run.json L4–28][Run] 一致：

|项目|既定上限|封存实际值|
|---|---|---|
|总工作负载时间|900 秒|15.906 秒；分段累计，写文档间隔不作计算耗时|
|数据 / 模型 / 追加核验|600 / 240 / 60 秒|1.562 / 9.797 / 3.500 秒；另有启动 1.047 秒|
|路径求值 / 统计扫描|128 / 4096|73 / 484|
|证据文件累计写入|33554432 byte（32 MiB）|3348021 byte|
|候选搜索 / 最多修正重跑|0 / 1|0 / 0|

`run.json/hit=null`；追加核验 [Verify L48–68][Verify] 记录新前向 0、重新划分 0及四任务只读加载通过。实际通信/注册在 [Summary L5–18][Summary] 及各 acceptance 中为未执行/不适用；理论计数载荷与本地文件写入明确区分。[推断] 已有额度足以覆盖该次 0.2 工作负载，未发生预算耗尽。合同 §7.2 的 0.2 行要求“运行前给有限额度，测得成本另存”，本次由预登记与最终账本具体履行；不据此冻结任何 G1/G2/G3 正式预算。[合同 §7.2 0.2 行][ProtocolBudget]

[推断] R01/R02 的 20 端总体、静态标签及最终训练计数以 C10/C100 文件为本关交付；注册事件实际覆盖仍留 G1.1。R03–R05 的待选项由 §三明确采纳；R06 本关模型/损失/变换身份齐备；R07 的训练 checkpoint、训练预算与合格参考继续留 G1.2，故不是 0.2 缺交项。依据：[合同 §2.2 R01–R07][ProtocolR]、[F §三 L174–177、181–183][FIII]。

## 三、五个待裁项

### B1. ε_num 候选值与合同登记方式

**[推断] 采纳 `1e-6`，仅作为已测 float32 eval logits 的归一化 L∞ 容差；在 §6 表外另立限定对象的补录，并仅更新原行“当前值”单元格的指引，不以它覆盖整行所有对象。**

测量证据：[Model L2–17、84–85、3592–3645][Model]；独立归纳的误差记录：[Verify L2–32][Verify]。完整前向/拼接、重复、旧 forward/log_softmax 兼容以及零输入 bias 的最大误差均为零；独立 float64 标量 head 参照最大 L∞ 差为 `5.229451813248964e-8`，CPU/CUDA 最大为 `8.940696716308594e-8`，两者 Frobenius 差另存。

预登记选择程序见 [Pre L30][Pre]；float32 machine epsilon 为 `1.1920928955078125e-7`。8 倍该值为 `9.5367431640625e-7`，4 倍实测最大归一化差为 `3.5762786865234375e-7`；按已登记的向上取有效位程序得到 `1e-6`。[推断] 候选量有数值尺度及独立参照支持，且主要结构等价检查仍要求精确一致，足以作为本次基础适配的接受限额；不是为使性能结论过关而新增百分点。

判定式沿用 [Model L2][Model]：`Linf(delta logits) <= 1e-6 * max(1,Linf(reference logits))`。Frobenius 为报告量，不另设同值阈值。适用对象绑定两种类别维度、两个初始化种子、固定 BN/变换及所记录 CPU/CUDA 环境；梯度、估计、恢复、训练模式、其他精度与未测平台不在范围内。[Model L4–83、3641–3645][Model]、[Verify L69–100][Verify]。

[推断] 冻结记录时刻为 **2026-10-13 10:11:45（Asia/Shanghai）**：这是在预登记数值测量后、0.2 正式封版裁决前的设计层采纳。保留 2026-10-12 原证据的 `candidate_pending_review_not_frozen` 历史状态，不倒填时间；未来正式测量所依赖的其他容差仍按合同 §6 提前冻结。

### B2. C100 实测 IF 偏离

**[推断] 接受该偏离，属于 R04 明确留待登记的整数处理范围；不要求更换构造规则。**

[Pre L25][Pre] 已在运行前分别定义构造参数 100、`max(1,floor(H*100**(-c/(C-1))))` 与实测 `max(N_c)/min(N_c)`。C100 的 [info.json L2345–2356][C100I] 记录 H=450、C=100、IF=100；[counts.json L2–103][C100C] 记录首类 450、末类 4；[acceptance.json L3][C100A] 记录实测 112.5。[推断] 450/4=112.5 是既定 floor 的直接结果，不是另外把 IF 主点改选为 112.5；不存在要求实测比值必须恰等于名义值的已冻结容差。[合同 §2.2 R04][ProtocolR]

**[推断] R04 需要登记的内容是“名义构造参数与整数化后的实测比值同时报告”，不是补造一个允许偏差百分比。** 本次正式采纳现有公式、作用于最终训练池、预留验证、未选训练索引单列及当前 C100 实测结果；名义 100 与实测 112.5 必须并列使用。采用同一基础任务的后续比较不得各自换一份类频率。若未来改变公式、取整、H 或 split，则按 [K 共用规则 L88及 §0.2 第 7 项][KRule] 回 0.2。

写回安排见 §五：本轮授权只允许合同 §6 更新，因此不改 R04 单元格；本节是 R04 此次选定结果的正式登记，后续授权的正文同步应引用本节，不重新选择取整规则。

### B3. α 统计定义

**[推断] 采纳执行 Agent 已选的统计定义；本次不要求额外训练计数审计。**

采用对象逐项沿用 [Pre L26][Pre]：每个类别独立抽取 `Dirichlet([0.1]*N)`；不按全局类频率缩放参数；该类最终训练数按最大余数法分配、余数并列按端 ID；类内索引随机排列；不强制最小类数、不重抽、不平衡端容量，空端显式记录。

证据不限于报告文字：C10 的 [info.json L9–253][C10I]、C100 的 [info.json L9–2233][C100I] 保存逐类抽样向量与 20 维参数向量；[task.py L83–96、109–136][TaskBuild] 与该规则一致。两份 counts/acceptance 已保存最终训练分布、端类计数、来源与缺失清单；独立计数审计定义及落盘复核见 [task.py L202–226、243–259][TaskAudit]。封存的 C10 每端训练总数包括 2、5、3508 等值，C100 每端为 214–845；并未因端容量不均衡重抽。[C10A L88–109][C10A]、[C100A L178–199][C100A]

[推断] R05 要求的“选定统计定义并用训练计数审计”在本次采纳与已有独立审计结合后完成，不需要为相同索引再做一遍计数。它不证明后续邀请/完成机制的正支持，也不证明参与偏差存在；这些仍按原检查点验收。[合同 §2.2 R05][ProtocolR]、[K §G1.1 第 3–4 项][KG1]

**[推断] R05 的正文最终应同步这一已选定义并指向固定任务哈希；本轮不改 §2.2。** 选定结果在本节生效，正文同步属于留待授权的文档维护，不是把研究选择重新交给执行者。新种子、新 split 或任何划分规则变化仍按 K 回退要求验收。

### B4. 客户端测试划分

**[推断] 采纳，满足本轮固定独立客户端测试要求；保留并明确均衡测试的解释边界。**

F 原文定位为 [F §三 L181][FIII] 的固定客户端评价，以及 [F §五.2 L247][FTest] 对现有 local_test 或自定义官方测试分配的选择与互斥、样本量、覆盖核验要求。F 没有把“复制客户端自然训练分布”设为此处唯一合法选项；合同 R03 也将具体分配留待选定。[合同 §2.2 R03][ProtocolR]

[Pre L24、27][Pre] 预登记官方测试按类打乱、轮转均分；C10/C100 info 的 `test_rule/allowed_overlap`、data 的 `index_namespaces` 与固定索引相符。C10A L22–65、C100A L112–155 实际记录每端 500 图且每端覆盖全部类别；已有独立核验逐类检查测试数、互斥与 global test 并集。[C10I][C100I][C10D][C100D]、[task.py L187–218][TaskAudit]

**[推断] 必须随此口径保留的解释：**客户端测试是与训练用途隔离的、按类均衡的固定官方测试子集；global test 是这些子集的并集评价视图，不是额外独立测试样本。客户端最低/最差 10%/尾类持有端指标只能解释为这些固定均衡子集上的表现，不能据此宣称自然本地训练分布下的收益。尾类持有端身份来自冻结训练 counts，不能从测试类别覆盖反推。[Pre L24、26–27][Pre]、[C10C L699–718][C10C]、[C100C L5951–5973][C100C]

本说明登记于裁决记录；无须更换现有划分或重新运行 0.2。R03 本轮不作正文修改，范围处理与 B2/B3 相同。

### B5. 正式封版状态

**[推断] 从 K 规定的五个状态词中选择“通过”。** 所有 K §0.2 第 4 项均有对应封存证据；本次 B1–B4 完成了设计层采纳；没有发现需要修正重跑、收窄重验或认定预算耗尽的本关缺口。[K 共用规则 L84][KRule]、本记录 §二。

封版身份是基准提交、§1.2 的任务文件及哈希，不改任务目录中的 `candidate` 名称，也不改原 JSON 的历史 `pending_review` 状态。**[推断] 后续读取“是否正式接受”应同时引用本裁决；原 JSON 是当时执行记录。** smoke 身份继续保留，两个完整规模候选在本裁决限定范围内作为已验收基础任务使用。

[推断] 0.2 这个前置依赖已经满足；G1.1/G1.2 仍需各自的预登记、预算和输入资格，不能用本次“通过”替代它们。各后续关口与回退点不变。[K §0.2 第 6–7 项][K02]、[合同 §2.2 R07、§6、§7.2][ProtocolR]

## 四、.gitattributes 工程改动裁决

**[推断] 纳入本次证据完整性与交付边界审计；不把它列为新的研究选择。接受保留，无需本轮调整。** 理由是它直接影响封存字节能否经 Git 保存，但实际规则没有对全项目所有文件统一施加行为。

逐行核对 [项目根 .gitattributes L1–9][Attributes]，并只读执行 `git check-attr --all` 检查指定路径，结果如下：

|原规则|实际作用范围与本次裁决|
|---|---|
|`/.gitattributes text eol=lf`|属性文件自身按 LF；不是设置用户或系统 Git 全局配置。|
|`/artifacts/direction_a/phase0_2_v1/** -text`|仅该封存目录及其后续新增文件不作 Git 文本换行转换；保护原始字节。|
|`/artifacts/direction_a/phase0_2_v1/run.json whitespace=cr-at-eol`|仅指定 run.json 的行尾空白检查处理 CR；不对其内容作换行转换。|
|`/direction_a/*.py text eol=lf`|匹配 direction_a 直接下属 Python 文件，包括未来直接新增文件；所查子目录示例不匹配。|
|`/scripts/accept_direction_a_baseline.py text eol=lf`、`/tests/test_direction_a_baseline.py text eol=lf`|仅两个指定脚本路径。|
|`/docs/DIRECTION_A_0_2_*.md text eol=lf`|匹配 0.2 文档，包括本裁决记录及未来同名前缀文档。|

[推断] 因而它超出“仅当前已列文件”的影响在于三个通配路径下的未来文件，但仍受路径约束。实际属性查询确认：合同、K、抽查的既有模型路径和其他脚本未获得上述属性；`direction_a/future.py` 与本裁决记录路径获得 `text/eol=lf`。这不是“根目录文件必然改变全仓库”的情形，也不能宣称它只影响当前 0.2 清单。

[推断] 与后续 Agent 的潜在冲突是：修改这些属性、批量规范化封存文件，或编辑器主动转换其换行，会改变证据字节；`-text` 只约束 Git，不阻止编辑器改写。LF 源码规则也意味着后续脚本不能假定 Git blob 与任意工作区原始字节始终一致。保留规则、按确切版本与字节语义核对即可，不要求新增全局属性或重写旧证据。依据：[Attributes L2–9][Attributes] 及 §1.2 已实际发现的输入文档换行差异。

**[推断] 登记的局限：**现有属性不保护 F、K、合同这三份输入文档的工作区原始换行。本轮已用基准提交和只含换行变化的等价检查追溯登记输入；未来若发现正文差异，则不得套用本次结论。无须为了修复这一已定位差异扩大 `.gitattributes` 范围。本轮不修改该文件、不执行 Git 规范化。

## 五、合同更新与权限范围

本轮只对 [DIRECTION_A_PROTOCOL_FREEZE_v1.md §6][Protocol6] 作以下更新：

1. `ε_num` 行仅更新“当前值”单元格：明确已测 float32 eval logits 的 `1e-6` 已冻结，其余对象待实测。
2. 在 §6 表后增加“0.2 数值容差补录”：登记冻结时刻、判定式、范数/尺度、选择依据、测量证据和适用边界。保留原行其他单元格以及其余阈值原文。

**[推断] R03、R04、R05 的研究选择已由本记录 B2–B4 裁定，但本轮不改合同 §2.2。** 原因是本次任务将合同更新明确限制在“0.1 §6 中本次被采纳的字段”。后续获准同步 §2.2 时，应把本次选定结果及本记录引用写回相应行；无需重新征集选择或更改数据。这一待办是正文同步，不是尚缺的设计层裁决，也不据此阻断已完成的 0.2 封版。

§7.2 的 0.2 行、其他阶段预算、其他阈值、章节结构、检查点依赖与回退点均保持原样。已有 0.2 额度和实际消耗由本记录 §2.3 与原运行账本登记，不扩展为未来运行额度。封存证据、执行报告、运行记录及算法代码不改；执行时输入合同的旧哈希继续作为历史身份保留，不回写 summary 或哈希清单。

## 六、本轮未裁决及后续事项

|事项|保持的状态与位置|
|---|---|
|训练计数实际注册、邀请/完成事件、正支持|仍由 G1.1 验收；本轮只接受固定训练计数表，不认证完成概率。依据：[K §G1.1][KG1]。|
|合格冻结参考、类梯度测量及其数值容差|仍由 G1.2 交付；随机初始化不是合格参考。依据：[合同 R07][ProtocolR]、[Model identities][Model]。|
|ε_bias、τ_probe、ε_match、允许的头类/客户端代价等|未被本轮采纳为数值，继续按合同 §6 的原状态和截止点办理。[Protocol §6][Protocol6]|
|后续 attempt、时间/字节/搜索、重复与修订预算|未冻结，0.2 的测量成本不能替代。依据：[合同 §6及 §7.2][ProtocolBudget]。|
|其他划分种子、压力点或新数据身份|本裁决只覆盖已封存任务；不能自动继承相同计数或通过结论。变化按既定回退点验收。[K L88、121][KRule]|
|R03–R05 正文同步|研究选择已裁定；因本轮写入范围限制，留待允许编辑 §2.2 的文档维护，按 B2–B4 同步，不重选。|
|任何新的工程规范扩大|本轮未批准扩大属性模式或全仓库换行整理；现有 .gitattributes 已登记且不需修正。见 §四。|

本轮新增本裁决记录，修改合同 §6；不执行任务、训练、重新划分或重新计数，不修改代码或封存证据，不 commit、不 push。完成后等待协调者确认。

## 引用定位

以下行号按本轮读取的输入版本；合同 §6 补录导致后续行号顺移，合同引用以节号与字段名定位。

[K02]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_CHECKPOINTS_v1.md:113>
[KRule]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_CHECKPOINTS_v1.md:80>
[KG1]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_CHECKPOINTS_v1.md:123>
[ProtocolR]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md:66>
[Protocol6]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md:177>
[ProtocolBudget]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md>
[FIII]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:174>
[FTest]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:247>
[AC]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_0_2_ACCEPTANCE_v1.md:113>
[RunRecord]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_0_2_RUN_RECORD_v1.md:5>
[Pre]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/preregistration.md:24>
[Summary]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/summary.json:19>
[Run]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/run.json:2>
[Model]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/model_acceptance.json:2>
[Verify]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/verification.json:2>
[Hashes]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/artifact_hashes.json:2>
[Attributes]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/.gitattributes:1>
[TaskBuild]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/direction_a/task.py:83>
[TaskAudit]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/direction_a/task.py:174>
[TaskSave]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/direction_a/task.py:243>
[Tests]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/tests/test_direction_a_baseline.py:15>
[Evaluation]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/direction_a/evaluation.py:8>
[S10I]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-smoke-CIFAR10-v1/info.json:2>
[S10D]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-smoke-CIFAR10-v1/data.json:2>
[S10C]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-smoke-CIFAR10-v1/counts.json:2>
[S10A]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-smoke-CIFAR10-v1/acceptance.json:2>
[S100I]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-smoke-CIFAR100-v1/info.json:2>
[S100D]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-smoke-CIFAR100-v1/data.json:2>
[S100C]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-smoke-CIFAR100-v1/counts.json:2>
[S100A]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-smoke-CIFAR100-v1/acceptance.json:2>
[C10I]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR10-N20-v1/info.json:2>
[C10D]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR10-N20-v1/data.json:2>
[C10C]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR10-N20-v1/counts.json:2>
[C10A]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR10-N20-v1/acceptance.json:2>
[C100I]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR100-N20-v1/info.json:2>
[C100D]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR100-N20-v1/data.json:2>
[C100C]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR100-N20-v1/counts.json:2>
[C100A]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR100-N20-v1/acceptance.json:2>

