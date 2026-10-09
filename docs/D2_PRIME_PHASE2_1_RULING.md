# D2′ 裁剪版 2.1 开工裁决

日期：2026-10-09。审查对象：`728c0bdb4cbafdc7f09cc51f29593cc9dcb0b49e` 工作树中的代码与文档。本文件只裁定执行契约，不包含实现或新的实验结果。

**结论：采用独立的正式异步入口；GPU/float32；K=20 缓冲聚合；两个无防御机制的干净基线独立运行；从平均基线日志离线计算 H/beta；保留同步冻结的 B_M。无需用户再选择架构或参数。** H/beta 的数值必须等本关日志，不能现在填猜测值。

下文 `[事实]` 表示已核对文件，`[推断]` 表示由证据作出的判断，`[裁决]` 表示本次确定的执行规则。已有裁剪版结构、单元数及通过门槛不变；本文件补齐六项未定语义，并明确恢复保证的适用范围。

## Q1．架构、精度与 recovery

**[裁决] 选 (b)：新建正式异步 seam，供本关平均/RFA及后续同协议比较使用。保留 `d2_prime_algorithm.py` 的 0.7 验证用途和限制，不在该入口加入“关闭 D2′”模式。** 正式入口可以复用 FLGo 的通信、时钟、客户端训练及已经验证的协议原语，但不能直接继承原生 FedBuff 的聚合行为作为本关定义。

### 证据与理由

- [事实] 旧 seam 强制 CPU/float64、无 buffers，并无条件构造参考和预算；客户端还强制单步 SGD、固定单批取样和 double 输入。这不是单个 dtype 检查的问题。[初始化约束 L49–61](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d2_prime_algorithm.py:49>)；[客户端约束 L224–241](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d2_prime_algorithm.py:224>)。
- [事实] 1.4 的实际训练是原 CNN、float32、1 epoch、batch64、SGD lr=0.1；0.7 报告则明确排除了 CUDA、多步训练等模式的恢复保证。[1.4 配置 L25–34](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE1_REPORT.md:25>)；[0.7 适用限制 L83–85](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE05_07_REPORT.md:83>)。
- [推断] 为运行纯基线而构造虚假参考、无限预算或调用实际 D2′ 提交路径，会模糊“未启用机制”的对照含义。分离正式入口可以保留旧验证证据，同时让所有正式方法共享明确的运输与调度规则。

### 正式精度与接口边界

1. **训练参数、客户端训练和模型聚合/写回采用 GPU/float32，沿用 1.4 的 CNN 与本地优化设置；本关不启用混合精度。** CPU/float64 可用于被动范数统计、独立贡献核验，以及后续参考/账本的标量计算，不能因此把整条真实训练路径改成 CPU/double。
2. **buffer-free 限制本关可以保留。** [事实] 当前 CNN 定义为卷积、ReLU、池化、Flatten、Linear，没有 BatchNorm 或显式注册的模型 buffer。[CNN L4–24](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/benchmark/cifar10_classification/model/cnn.py:4>)。[裁决] 启动时仍核对实际 buffers 为空；本次不扩展到含 buffers 的模型。若实例不符，报告配置不一致，不能静默忽略其状态。
3. **基线不构造 ReferenceConfig/BudgetConfig，不调用 `commit_event`，不做 D2′ 裁剪、评分、参考写入或预算缩放。** 任务号、源模型、期限、版本、队列、终态、真实贡献记录仍必须存在。这里的“关闭机制”不能关闭协议校验。
4. **新入口必须有自己的短程入口验收。** 必须覆盖异源版本、同刻多批、过期边界、尾批及 float32 实际写回；零延迟只做小规模退化核验，不新增完整训练矩阵。零延迟与同步比较须采用相同 K 和相同源模型，不能拿 K=20 的两次提交冒充同步 40 端的一次提交。
5. **0.7 PASS 不自动覆盖新入口。** 正式 D2′ 接入后、2.2完整训练前，还须复核新路径中受影响的源快照因果性、参考逐端重构、账本和原子提交不变量；这属于已有入口验收的迁移，不增加一套检查点，也不要求本次2.1先实现 D2′ 或 GPU 恢复。

### recovery 的最终地位

- **0.5/0.7 的逐步状态哈希一致契约继续有效，但只适用于已经验证的 CPU/float64、规定客户端与安全保存点。** [事实] 已通过的证据是代表性状态的 7 个哈希一致及小 CNN 后缀恢复；报告明确否认任意中断位置和未覆盖模式的恢复保证。[恢复证据 L29–35](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE05_07_REPORT.md:29>)；[训练后缀 L57–71](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE05_07_REPORT.md:57>)；[范围 L83–85](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE05_07_REPORT.md:83>)。
- **2.1 起的最低正式实验路径暂不支持中途恢复。** 本关不要求完成 GPU 逐步哈希恢复方案；中断单元保留失败记录，从同一登记种子和初始状态重跑整个单元，不拼接两段轨迹，不按结果选择重跑。仅保存模型的文件必须标为模型产物，不能标为可续跑检查点。此规则持续到后续明确扩展恢复验收为止。
- **这不撤销源快照、队列、版本、任务唯一性和预算原子性的运行时要求，也不放宽数值正确性。** 若以后启用正式恢复，必须保存全部影响决策的状态并另行验收该设备/精度/客户端模式；不能直接引用 0.7 PASS。设计原有保存清单仍是届时的必要条件。[保存契约 L317](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_DESIGN.md:317>)。
- **论文允许报告受限配置的精确恢复验证，不能声称正式 GPU 实验已经验证精确续跑。** 真实模型仍执行“贡献分解＋独立写回舍入”两层核验；这与跨进程恢复哈希一致是两回事。[数值判据 L57](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:57>)；[两层误差定义 L17–24](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/contribution_diagnostics.py:17>)。

## Q2．异步 RFA 的定义及权重契约

**[裁决] 使用 K=20 的缓冲 RFA，按 Q3 的统一规则开批；不按一次通信返回包的大小定义批次，不常规执行单客户端 RFA。每一批重新运行 T=5、nu=1e-6 的 RFA，跨批不携带 Weiszfeld 中心或权重。**

[事实] 当前 RFA 每次以零向量初始化、输入等先验权重，保存实际生成最终 z 的末轮 betas 和归一化混合系数。这个定义不要求输入来自同一源版本。[RFA 调用 L127–146](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/rfa.py:127>)；[末轮捕获 L91–104](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/rfa.py:91>)。1.4 已冻结其 T、nu 与语义标签。[冻结 L134](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE1_REPORT.md:134>)。

### 两层权重必须分别命名

设本次有效候选批次大小为 m≤K，源模型为 θ_(s_i)，本地模型为 θ_i，提交前版本为 k：

\[
u_i=\theta_{s_i}-\theta_i,\qquad
\ell_i=k-s_i,\qquad h_i=(1+\ell_i)^{-1}.
\]

**RFA 层：**对原始、未裁剪、未乘 h 的有序向量 u_i 运行 RFA，取得实际末轮系数 w_i：

\[
w_i\ge0,\quad \sum_iw_i=1,\quad z_{\rm RFA}=\sum_i w_i u_i.
\]

这里的等式按已登记的浮点核验口径检查。`rfa_final_mix_v1` **只标记这一层**，继续表示“同一次调用、同一输入顺序的末轮归一化混合系数”，不改为跨迭代因果贡献。

**异步提交层：**设服务端 eta_M=1，固定批次尺度 f=m/K：

\[
a_i^{\rm avg}=\eta_M\frac{h_i}{K},\qquad
a_i^{\rm RFA}=\eta_M\frac{m}{K}w_i h_i,
\qquad
\theta^+=\theta^- -\sum_i a_i u_i.
\]

- 满批 m=K 时，RFA 实际系数为 w_i h_i；尾批/超时小批按 m/K 缩放。
- **不得把 h 放进 RFA 距离计算或先验权重，也不得在乘 h 后重新归一化。** 本次选择的是“原始更新 RFA 权重＋提交时陈旧度衰减”，应登记适配标签 `async_rfa_post_staleness_v1`；不冒称它与原生 FedBuff 相同。
- [推断] 这保留了同步 RFA 的几何判别定义，并把时序衰减作为两基线共有的外部规则。m/K 使均匀 w_i=1/m 时恰好退化为上述平均系数 h_i/K，避免小批无条件获得整批步长。后续筛选/预算作用后，**不能用剩余人数重新计算 m/K**。
- [事实] D2′ 本身采用提交版本差、h=1/(1+ℓ)、固定 K 分母；小批也不能按筛选后人数重新归一化。[设计 L244–254](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_DESIGN.md:244>)。

### `bind_final_mix` 的消费契约

1. 必须继续用实际 u_i、z_RFA、同次调用号和真实有序 client_id 消费 `bind_final_mix`。另记录 task_id、source_version、batch_id；批内身份不得重复，来源/输入/输出指纹必须匹配。
2. w_i 是 **RFA 中间聚合权重**；a_i 才是 **实际异步模型系数**；实际逐端贡献为 C_i=−a_i u_i。两者同时保存。一般不能写成“实际模型位移=−z_RFA”。
3. [事实] 现有绑定器校验调用号、语义、指纹、权重与 beta 的关系，但其返回说明写死了同步口径“minus-aggregate; C_i=-w_i*u_i”；现有写回校验也假定实际位移为 −aggregate。[绑定检查 L11–56](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/rfa_contributions.py:11>)；[返回说明与写回 L59–79](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/rfa_contributions.py:59>)。
4. **[裁决] 允许正式异步适配层扩展这部分记录/消费边界，必须保留原 RFA 层校验，并为实际 a_i 的模型写回另做两层核验。** 同步含义必须保持兼容；同步说明不能原样充当异步实际写回说明。不得为省事把 w_i 改存为未归一化 a_i，或把经过 h 加权后的位移冒充原调用输出交给绑定器。
5. 非法、重复或过期更新必须在 RFA 开批前剔除；若提交前有效性发生变化，原批次结果失效，不得删一项后沿用旧 w_i。没有真实末轮权重就停止，不得均匀兜底。

## Q3．异步协议、调度与同步对应关系

**[裁决] 使用离散模拟时间、提交序号版本、每身份一个未终结任务、全局最多40个未终结任务；补足空槽派发；K=20 满批优先，固定超时及尾部排空规则。两基线完全同协议。**

### 冻结的协议规则

| 项目 | 本关裁决 |
|---|---|
| 时钟 | 模拟时间 t，从0开始，每 tick 增加1；不使用真实 GPU 耗时推进协议时钟。 |
| 源与陈旧度 | 签发时冻结源模型与源版本 s；ℓ=k−s，在**每一批提交前**以当前 k 计算。时间差只用于时延、期限、H，不代替 ℓ。 |
| 版本 | 有正系数的有效提交使 k 加1；参数相消不阻止加1；空事件不加1。同一 tick 的第二批须看到第一批推进后的版本。 |
| 未终结上限 | 每身份最多1个；全局40个。训练/传输中以及已经到达但等待提交者均占槽；到达本身不释放槽。 |
| 派发 | t=0补足40；以后每个 tick 先处理到达、过期和提交，再从没有未终结任务的身份中均匀无放回补足空槽。每 tick 最多派40个，且不超过剩余训练任务预算；同一 tick 不反复“派发—立即回收—再派发”。 |
| 同刻顺序 | 同刻到期优先于到达；到达按 task_id 升序入队。全部到达入队后，再按 FIFO 分批，每批提交前重新核验来源、期限和陈旧度。 |
| 批次 | 待处理的合法到达达到 K=20 时，取最早20条。满批处理完后，剩余不足20条的最老候选若已等待8个模拟时间单位，允许处理该小批；不足8则等待。等待起点是该候选首次合法到达时刻。 |
| 尾部 | 已执行满12,000个训练任务后不再新派；在途继续按固定期限处理。当没有待到达的未终结训练任务时，剩余合法候选允许立即作为尾批处理，不额外训练凑整。 |
| 时间有效期 | lifetime=32；t≥issued_at+32 即过期。 |
| 最大陈旧度 | max_staleness=64；ℓ>64 过期，ℓ=64仍合法。 |
| 结束与资源 | 所有12,000个已训练任务达到终态，并排空仍待交付的运输包；迟到包只作拒绝记录。过期/拒绝已训练任务照计工作量，不补训抵消。 |

[事实] 现有协议已经规定：未终结身份占槽、签发绑定版本、同刻到期优先、到达只改变队列，以及版本过大过期。[签发与槽位 L157–203](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/protocol.py:157>)；[事件与接收 L228–281](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/protocol.py:228>)。设计明确版本是有效提交序号。[设计 L307–315](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_DESIGN.md:307>)。

**[裁决] 上表的“等待满20／等待8后小批”、每 tick 补足40及32/64，是本次正式入口的明确取值，不是声称0.7已经采用或验证了这些取值。** [事实] 旧 seam 在缓冲非空时即可尝试提交；0.7 使用每次最多派10、延迟1–3、期限30等工程配置。[旧提交触发 L79–89](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d2_prime_algorithm.py:79>)；[0.7 工程配置 L57](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE05_07_REPORT.md:57>)。

后续同协议的 D2′/预算对照必须沿用上述外部调度和开批规则，保留原有预算等待、释放、过期与固定 K 分母；筛选后不能重新等齐20个“通过者”再放大其系数。预算等待任务不得因已有一次提交尝试而被重复签发。若后续改变外部协议，当前基线不能继续作为“同协议”控制。

### 99%覆盖规则如何落地

- [裁决] lifetime=32、max_staleness=64、缓冲等待8以及 Q6 的延迟分布，**全部在 smoke 前登记**。两条完整干净基线均核对至少99%的已训练任务没有因期限/陈旧度失效；所有尾部保留并报告，不重采样、不删日志。
- [推断] 在 Q6 最大到达延迟8、上述批处理规则下，正常基线候选的提交年龄至多约16个 tick；每 tick 最多处理40条，即最多两批，版本差有保守的约32上界。因此32/64是留有余量的固定协议界，不是依据准确率挑选的参数。该推断以已裁定事件规则成立为前提，仍须用实测年龄/版本差核对。
- [事实] 完整版允许初始有限协议采集后修订，但修订影响终态须重跑；裁剪版进一步要求 smoke 前冻结期限/时延/终态，以便只跑两条基线直接定 H/beta。[完整版2.1 L171–172](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:171>)；[裁剪版 L64–67](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS_TRIMMED.md:64>)。
- **[裁决] 这里将99%作为冻结协议的覆盖验收，不再要求额外拟合最紧的99%分位期限。** 若覆盖不足，2.1不能PASS；先区分接线错误与协议设定问题。需要改期限/调度时显式修订并重跑受影响基线，旧运行不抵扣。不得偷偷改值后继续复用旧日志。

### 与1.4的对应关系

保留相同任务/模型/本地优化/初始种子/评价数据用途和 M 定义；资源基准是**12,000次完整本地训练**。异步 M 使用已训练且已终结任务数的10,400／10,800／11,200／11,600／12,000五点，不用模型版本或模拟时间替代。[指标及任务轴 L47–48](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:47>)。

必须额外声明：同步每轮40端同源；本关是最多40个未终结任务、K=20且可能混合源版本，满批量级约600次提交。**不能称为“300轮异步”或声称聚合步数/有效步长与同步相同。** [设计中的对应限制 L569–580](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_DESIGN.md:569>)。

两异步基线配对的是相同初始条件、客户端数据、调度规则与外生延迟随机源；每种方法在自己的源模型上重新训练。记录样本访问和 minibatch 数；差异超过5%时，未进一步按实际工作量对齐不得声称等计算量效率优势。[工作量与配对限制 L59](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:59>)。

本关方法名称应写作“本项目缓冲异步平均／缓冲异步 RFA”。[事实] 原生 FedBuff 使用整缓冲清空及 `(1+版本差)^(-0.5)`，不是上述固定分批与 h 规则。[原生实现 L12–26](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbuff.py:12>)。不得把本关结果标为未修改原生 FedBuff 的复现成绩。

## Q4．H/beta 的计算层级与名义贡献

**[裁决] 两基线 Server 独立记录协议和实际贡献日志；完整干净平均基线完成后，离线计算 H/beta。不进入 D2′ Server，不调用 `commit_event`，不初始化参考，不实际扣账。名义参考费用规则保留，eta_R=0.1，eta_M=1，评分 g=1，K=20。**

[事实] `commit_event` 要求参考和预算同时存在；默认参数明确 eta_R=0.1、eta_M=1、K=20；裁剪版仍要求用正常干净平均基线日志定 H/beta。[提交前置条件 L347–355](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/protocol.py:347>)；[首版参数 L327–328](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_DESIGN.md:327>)；[裁剪版 L64](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS_TRIMMED.md:64>)。

### 本次消除“相邻任务”和“名义贡献”的歧义

1. **H 的间隔取同身份连续两次有效模型提交的模拟时间差。** 只取正间隔，合并全部身份的这些间隔，取 linear 95%分位数；不采用签发间隔、到达间隔或模型版本间隔。无正间隔时 H=1 tick。逐身份公布提交数和可用间隔数，不隐去采样稀少身份。
2. **名义贡献取平均基线实际有效提交的任务**，在其真实提交时刻记一条只读的校准记录。用该任务在该批提交前的 ℓ_i 算 h_i：

   \[
   a_i^{\rm nom}=\frac{h_i}{20},\qquad
   b_i^{\rm nom}=\frac{0.1h_i}{20},\qquad
   q_i^{\rm nom}=a_i^{\rm nom}+b_i^{\rm nom}=0.055h_i.
   \]

   这是“若采用 D2′ 固定步长、令 g=1时”的候选费用，不是声称平均基线写过参考。零向量但合法正系数的提交仍按系数记名义费用；被拒绝、过期和未提交任务不收费，另列终态和资源计数。
3. 对100个身份分别求完整轨迹上的最大滑窗名义费用：

   \[
   Q_c^{\max}=\max_t\sum_{i:\,c_i=c,\ t-H<t_i\le t}q_i^{\rm nom},
   \qquad \beta=\operatorname{quantile}_{0.95}^{\rm linear}
   (Q_0^{\max},\ldots,Q_{99}^{\max}).
   \]

   无提交身份的最大值为0，不能从身份总体中删掉；最大值检查各名义提交时刻即可。H 保留分位数实数值，不擅自向整数取整。
4. **不使用 RFA 的 w_i 定 beta，不从两基线中挑更有利的一组统计，不按快/慢组分别调额，不以 B_M 或范数乘进 q_i。** RFA仍记录其真实 a_i，只用于贡献核验及比较。H/beta必须有限且正；异常/不足以计算时报告证据不足，不填默认值伪造校准通过。

[事实] 滑窗是 `(t−H,t]`，实际提交时记账；累计的是最终非负系数而非更新净范数。[时间与窗口 L5–12](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_DECISIONS.md:5>)；[系数约定 L17–23](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_DECISIONS.md:17>)。[推断] 用提交时序校准 H，才能与以后预算释放/收费的时钟一致；从同份平均基线日志计算不需要先知道 H/beta，也不引入 D2′ 评分反馈。

**日志须区分两种陈旧度。** 校准费用使用提交前 ℓ；慢端保留指标的名义分母仍按首次合法到达时版本差、未到达者按到期版本差计算，不能用本节的提交口径覆盖它。[原慢端指标 L55](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:55>)。因此至少保留签发、首次合法到达、提交/终结时间及对应版本、身份/任务号、原始范数、实际系数；校准字段明确标为 nominal，不混入实际账本。

## Q5．同步 B_M 的异步适用性

**[裁决] 本关及紧随其后的2.2沿用 `B_M=0.9701598816245317`。本关两个无D2′机制的基线不使用它裁剪；同时被动采集异步原始上传范数，用于检查该固定尺度的适用性，不在2.1自动重校准。**

- [事实] 该数来自同步干净 FedAvg 的12,000个合法、聚合前、未裁剪上传范数的 linear 95%分位数；当时严格超阈值600个，并没有给 FedAvg/RFA增加裁剪。[尺度证据 L119](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE1_REPORT.md:119>)。裁剪版仍规定从同一次阶段1干净 FedAvg取得 B_M。[裁剪版 L67](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS_TRIMMED.md:67>)。
- [推断] 这个同步5%比例不能外推为异步也截断5%；异步源模型和身份训练频率改变时，范数分布可能不同。它不影响本关未裁剪基线的模型轨迹，却会影响以后 D2′ 的特征和模型裁剪。
- [裁决] 两条异步基线均记录原始 `source_model−local_model` 范数；收到但过期的合法形状/有限上传也保留为单独统计，不能只看最后被消费的样本。尚未到达内容不得供当时的模型决策或校准参考使用。所有已训练任务均应有资源/终态记录。
- 至少报告原始范数的 p50/p95/p99、超过固定 B_M 的比例，并按快/慢端、陈旧度及消费/过期状态分组。若全部12,000个原始更新可完整取得，另报全上传总体；否则明确缺失量和可观测分母，不能假称完整分位数。
- **只保存 `async_raw_norm_p95` 这样的诊断量，不把它命名成第二个已冻结 B_M。** H/beta仍按 Q4计算，与此范数分位数无关。
- 若2.2出现裁剪/参考抑制，可在既有“一次诊断驱动修订”额度内提出 B_M 的正式修订，并重跑受影响单元；必须保留原运行、声明新尺度来源，不能按 D2′ 输赢在同步/异步阈值间择优。[既有修订边界 L180](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:180>)。**本关不预先触发这次修订。**

## Q6．快慢身份、延迟分布与固定时点

**[裁决] 本关100端全为良性；固定50个慢端、50个快端。身份分组与类别/样本量独立。快端延迟均匀取 `{1,2,3}`，慢端延迟均匀取 `{6,7,8}`，单位为模拟 tick。该分布由本裁决定，不交由执行 Agent 按成绩选择。**

| 项目 | 明确约束 |
|---|---|
| 慢端选择 | 客户端身份按0–99排序；使用独立 NumPy RandomState/MT19937，seed=1801，无放回抽50个作为慢端，其余为快端。保存最终名单及哈希。 |
| 派发随机源 | 独立 RandomState，seed=801；对排序后的空闲身份均匀无放回抽样，抽中身份按ID顺序签发任务。 |
| 延迟随机源 | 每身份 c 独立 RandomState，seed=2801+c；其第 j 次签发只消耗该身份第 j 个延迟抽样。两方法复用相同分组/种子/规则，各自实际训练。 |
| 外生性 | 延迟表示签发到可交付的总模拟时延；不再叠加一次按真实GPU耗时计算的延迟。快慢名单不得作为评分、RFA先验或预算参数的输入，只供模拟器和事后分组诊断使用。 |
| 其他系统条件 | 单进程顺序执行本地计算，模拟40个未终结任务；无丢包、无掉线、完整本地训练。计算顺序与模拟到达顺序区分，尚未到达包不可供服务端决策读取。 |
| 固定时点 | 分组、随机源、分布、缓冲等待8、任务期限32和最大陈旧度64，在任一2.1 smoke及完整训练前一并登记。2.2继承同一配置，不看D2′结果重抽快慢身份。 |

[事实] 裁剪版只保留一个预先指定的、含快慢良性端的正常有界延迟条件，并要求 smoke 前固定时延/期限/终态规则。[裁剪版 L64–67](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS_TRIMMED.md:64>)。完整版要求在观察 D2′ 成绩前固定快慢身份，且慢端身份真值只作诊断。[固定要求 L171](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:171>)；[慢端诊断 L55](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:55>)。

[推断] 分离身份延迟随机流可以避免某方法调度次数不同，导致另一身份被动拿到不同的随机延迟；它不要求各方法最终到达/版本轨迹相同。离散且有界的快慢分布足以形成可审计的版本落后与速度差，但不代表真实设备延迟分布，也不支持多种时序条件上的泛化结论。

**本关交付与放行：**两条干净完整基线各12,000次训练；均高于15%的 M 地板；贡献/协议验收通过；正常任务期限/陈旧度覆盖≥99%；提交本裁决规定的分组及协议清单、原始日志、离线 H/beta 计算和范数诊断。具体 H/beta **待定，需先完成干净异步平均基线**，其余本文件所列设计决策已经确定。失败按原2.1先查协议/优化或修正规格，不从本关直接判 D2′ 机制失败或切D3。[2.1 失败处置 L172](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:172>)；[地板定义 L52](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:52>)。
