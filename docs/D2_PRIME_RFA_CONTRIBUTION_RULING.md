# D2′ 阶段1：RFA逐端贡献接口裁决

日期：2026-10-09。审查基准：`b832abed31b5e34b0c0e51f09860245bb3278ab6`，与阶段1清单登记一致。[M7]

本轮只作源码/调用链、文档及静态清单核对，输出本裁决；不修改实现，不运行训练，不把接口设计获准等同于实现已经通过。本文件中，**[裁决]**表示本次确定的规范，**[推断]**表示从列明证据推出的判断；其他事实均附文件行号。

**[裁决] 最终采用语义(a)，并补充身份与写回方向契约：权重必须是产生本次返回向量的最后一次真实Weiszfeld迭代的归一化混合系数。不是跨迭代累计beta，不是反事实因果影响，也不是事后拟合出的任意一组重构系数。允许执行Agent扩展RFA及必要的调用边界；不得改变RFA算法。接口前置验收通过后，才能继续原同步校准关。**

## 一、“逐端贡献权重”的最终定义

### 1.1 数学对象与有效域

现有RFA调用以均匀`alphas`、零初始向量开始；迭代中按距离计算beta，再用本轮beta加权并归一化得到新z。证据：[RFA:49–55][R49]、[RFA:19–36][R19]。

**[裁决]**设本次实际输入按顺序为向量`u_1,...,u_m`，使用当前RFA的`alpha_i=1/m`、`z^(0)=0`、已登记的T和nu。对`t=1,...,T`：

\[
\beta_i^{(t)}=\frac{\alpha_i}{\max(\|z^{(t-1)}-u_i\|_2,\nu)},\qquad
z^{(t)}=\frac{\sum_i\beta_i^{(t)}u_i}{\sum_j\beta_j^{(t)}}.
\]

本关要输出的是：

\[
w_i=\frac{\beta_i^{(T)}}{\sum_j\beta_j^{(T)}},\qquad
c_i=w_i u_i,\qquad z=z^{(T)}=\sum_i c_i.
\]

必须满足以下语义：

- 每个位置恰有一个有限、非负的`w_i`，数学上`sum(w_i)=1`；数值验收见第五节。
- `w_i`来自**计算当前返回z的最后一轮**。不得在返回`z^(T)`上再计算距离，拿下一轮系数冒充最后一轮系数。
- `sum(w_i*u_i)`能重构z只是必要条件；存在重复/线性相关输入时，重构系数未必唯一。因此还必须证明它等于实际最后一轮beta的归一化结果。
- 接受域：非空、同形状、同计算设备/类型的有限向量；`T`为正整数，`nu`为有限正数；本次归一化分母必须有限且大于零。不符合条件时拒绝本次调用/验收，不生成伪权重。
- 单端、全零、相同向量属于有效情况；它们可能产生合法的1或均匀权重。禁止的是**缺接口或错误时的均匀兜底**，不是禁止算法本身得到均匀结果。

现有检查只排除了`nu<0`，没有在辅助函数入口排除`T=0`或`nu=0`；`RFA.__call__`还直接访问`inputs[0]`。[RFA:9–19][R9]、[RFA:49–52][R49] **[推断]**若允许无真实迭代的调用，也承诺“最后一轮混合系数”，该承诺没有定义基础。本次允许收紧上述非法/退化参数的入口验证，不以兼容无效参数为由伪造权重；有效域内的算法和既定参数不变。

### 1.2 从输入位置到客户端身份、再到模型写回

同步桥接实际构造`u_i = base - client_model_i`，按`models`与`received_clients`的位置对应；返回模型采用`current - aggregate`。[桥接:223–240][A223]、[桥接:122–130][A122]。普通RFA路径没有sign聚合器那项额外服务端步长乘法。[桥接:268–282][A268]

**[裁决]**接口分成两个契约层，均须验收：

1. **RFA层：**输出按本次`inputs`顺序排列的`w_i`，不要求纯张量聚合器自行知道客户端ID。
2. **调用边界层：**把同次调用的位置`i`、`received_clients[i]`、实际输入`u_i`和`w_i`绑定，形成逐身份记录。身份来自可信接收记录；恶意/良性真值只用于事后分组，不进入权重计算。

同步RFA的模型贡献方向为：

\[
C_i=-w_i u_i,\qquad \widehat d=\sum_i C_i=-z.
\]

须分别验收“聚合向量重构”与“模型实际写回”；不能把`+w_i*u_i`直接记作模型位移。浮点写回误差单独记账，不能分摊到客户端来补齐漏项。

**[裁决]**本关要求身份映射完整，不要求把ID强塞进`smoothed_weiszfeld`。后续若输入有预先声明的裁剪/缩放，则权重针对**真实送入RFA的向量**；折算原始更新或最终写回系数时必须展开实际尺度，不能假定`w_i`已经包含服务端步长、陈旧度或预算缩放。当前同步校准不得为方便记账自行新增这些机制。

### 1.3 各检查用途所需语义

裁剪版把阶段1合并，`B_M`取同一次完整干净FedAvg的更新范数；原始子编号把其冻结放在1.4，而非1.1。[裁剪版:63–67][C63]、[完整检查点:155–160][F155]

| 用途 | 本次确定的语义 | 明确不需要什么 |
|---|---|---|
| **1.1输入/接口检查；合并关内的`B_M`采集与冻结** | `B_M`使用完整干净FedAvg中合法客户端更新的**聚合前原始L2范数**95%分位数。RFA接口是该合并关的独立前置验收。 | `B_M`的定义不依赖RFA权重，更不是`norm(w_i*u_i)`或beta的分位数。无需跨迭代因果量。 |
| **1.3攻击校准** | 攻击损害仍由干净/攻击的M差值判定，活性由合法非零上传判定；若报告RFA恶意有效贡献，使用同次调用的`w_i`、`C_i`与真实身份事后分组。 | 不用两组beta均值衡量攻击有效性；贡献非零也不替代准确率实际损害。无需语义(b)。 |
| **1.4基线结果与冻结** | B仍固定RFA；比较真实z产生的训练结果，记录实际末轮混合系数以审计。`B_M`与攻击条件按既定规则冻结。 | 不重新排名选方法，不用因果归因分数替代性能结果。无需语义(b)。 |
| **后续B＋预算的接口承接** | 在实际写回路径中，把末轮系数折算为真正提交的模型系数，记直接写入额度；发生预算缩放后，要记录缩放后的实际系数。 | 不把未归一化beta当额度，不把归一化混合系数直接称为全局因果影响。 |

攻击损害与地板指标的既定定义见[完整检查点:47–52][F47]，RFA禁止均匀兜底及影响上限匹配约定见[完整检查点:199][F199]。本裁决不改变这些门槛。

**[推断]**`w_i`本身依赖全部输入及前面的迭代；移除或改变某客户端，其他客户端的系数也可能变化。因此`w_i*u_i`是**本次实际输出的直接混合项**，不是移除该端后的反事实差值。把各轮beta或各轮`w_i*u_i`相加，会把用于求解的中间迭代当成额外模型写入；现有函数仅返回最后z，并未把中间z逐次提交。[RFA:19–36][R19]、[桥接:268–282][A268]

**[裁决]**语义(b)不属于本关，既不要求实现，也不得用(a)声称已经证明(b)。后续直接贡献预算不能据此宣称限制了该端通过改变其他系数造成的全部间接影响。

## 二、源码与消费路径核实

### 2.1 返回时最后一轮beta到底保留了没有

| 核实结论 | 证据 |
|---|---|
| `betas`每轮重新创建；辅助函数的返回签名中没有独立的末轮beta或权重对象。 | [RFA:19–20][R19]、[RFA:36][R36] |
| 但每轮beta都按前缀/后缀拆开并追加到两条历史；最后一轮数值仍在各历史末段，不能说“最后beta全部丢失”。 | [RFA:26–32][R26] |
| 这两条历史被返回，并赋给RFA实例属性；RFA调用本身只返回z。 | [RFA:36][R36]、[RFA:52–55][R52] |
| 当前没有归一化末轮系数属性，也没有按客户端身份绑定的贡献记录。 | [RFA:39–60][R39]、[桥接:268–282][A268] |

**[推断]**在当前`b=5`、`m>0`、`T≥1`且输入顺序已知时，令`p=min(5,m)`、`q=m-p`，两条历史各自最后`p`/`q`个元素可恢复末轮后缀/前缀，拼回后再归一化。`q=0`时前缀为空，不能把Python的`[-0:]`误当空切片。这解释了信息仍在，但**不是要求实现者采用这种历史解析方案**；新的公开契约应直接表述末轮系数，不能让调用者依赖隐含分组宽度。

### 2.2 `get_attack_stats()`在哪里被消费

1. **同步桥接：**`_aggregator_stats`调用getter，异常时返回空字典，过滤非标量张量/不支持类型；除有限数值外，还允许字符串、布尔和None。[桥接:87–112][A87] 随后统计写入`byz_last_round`，模型仍由原`aggregate`写回。[桥接:268–282][A268] 日志器把该字段追加到输出。[日志器:37–45][L37]
2. **原训练入口：**`FL.get_aggr_success_info`转调getter；`main.train_epoch`先聚合并更新模型，再收统计、求均值和输出；学习率衰减按epoch配置，不读取这些beta均值。[FL:295–302][FL295]、[main:27–51][MAIN27]、[main:90–107][MAIN90]
3. **混合聚合器：**`hybrid_aggr.py`读取子聚合器统计并构造命名空间字典，但该方法当前最终返回`None`。其RFA聚合值在另一条路径计算。[Hybrid:427–467][H427]

**[推断]**在本次核对的仓库可见调用链中，RFA统计数值没有反馈到模型向量、权重、客户端筛选或学习率决策。不能把这一点扩张为“随意改变统计接口完全不会影响运行”：原入口会对字段值直接求和/求均值，返回嵌套权重列表或非数值对象会破坏这类消费；部分入口也没有捕获getter异常。[main:37–51][MAIN37]

### 2.3 返回值与组拆分的其他依赖

- 同步桥接直接访问RFA返回对象的`.shape`、有限性并传入模型写回函数，依赖返回**Tensor**。[桥接:268–282][A268]
- 原FL把返回值存为`last_aggregate`，可能`.clone()`传给攻击端，并交给模型更新函数。[FL:244–284][FL244]
- 混合聚合器最终RFA返回值也会`.clone().detach()`；其“保留全部客户端”的集合是选择接口，不是混合权重。[Hybrid:275–298][H275]、[Hybrid:427–440][H427]
- `smoothed_weiszfeld`当前可见执行调用是RFA内部的三项解包；混合模块有导入该名称，未见额外执行调用。[RFA:52][R52]、[Hybrid导入:7][H7]、[Hybrid2导入:7][H2_7]
- `self.b=5`传给辅助函数后，仅用于`betas[-b:]`和`betas[:-b]`统计切片。计算z的循环使用**完整betas和完整weights**，没有按这两组筛除或重新加权。[RFA:45][R45]、[RFA:26–35][R26]

**[推断]**`b=5`与本关的旧统计误命名有关，但不是RFA聚合公式的恶意人数参数。同步桥接用`received_clients`与真实恶意集合另算位置，未把恶意端重排到末五位。[桥接:226–240][A223] 因此旧字段名不能保证对应真实恶意/良性身份，不能用“修b”替代最终权重接口。

## 三、扩展允许边界与禁止项

以下均为**[裁决]**，执行Agent可在范围内独立实施；具体代码组织和实现是否满足要求由其交付证据，不由本裁决预判。

| 对象 | 允许边界 | 禁止项 |
|---|---|---|
| **`smoothed_weiszfeld`签名** | **允许向后兼容扩展。**现有六参数调用必须仍有效且默认返回原三项`(z, malicious_betas, benign_betas)`；可新增显式请求权重的可选参数，显式扩展结果为原三项加末轮归一化权重。也允许由内部辅助接口承载相同契约，不强制只能新增独立公开方法。 | 不得把所有默认调用静默改成四项；不得要求现有调用者猜测返回形状。不得从返回z重新算一轮“权重”替代真实末轮。 |
| **`RFA.__call__`** | 默认继续返回同形状、同设备/类型的聚合Tensor。允许在同一次调用暴露旁路贡献记录。 | 不得默认返回`(z, weights)`、字典或数据类，破坏上述非D1调用链。不得改变有效输入的z计算。 |
| **`last_client_weights`** | **确定采用此名称。**含义固定为`rfa_final_mix_v1`：本次成功调用、按输入位置排列的独立一维数值序列，长度m，值为上节`w_i`。不携带梯度，不与之后调用可变内容共用同一份记录。首次调用前或失败调用后为`None`，不得沿用上次成功值。 | 不得放alpha、跨迭代均值、未归一化beta、selection mask、贡献范数、因果分数；不得缺失时填`1/m`。 |
| **贡献记录的关联信息** | 必须能判定记录对应哪一次聚合及哪些实际输入。桥接输出至少明确调用标识、输入位置、客户端ID、权重语义、权重与更新/位移方向；可附T、nu及重构误差。`last_contribution_trace`可作为附加记录，但不要求沿用D1的字段结构。 | 不得把攻击候选试算或前一轮调用覆盖后的“last”记录误配给已选z；不得只输出匿名均值而声称逐身份验收完成。 |
| **旧`malicious_betas`/`benign_betas`与getter** | **本次保留默认两条历史及两个数值均值字段的旧含义，可明确标为deprecated/legacy位置统计。**允许补充未初始化/失效状态的安全处理；真正逐ID或末轮诊断另用明确名称。D2′贡献验收与后续账本不消费这些旧均值。 | 本次不删除默认字段、不把旧字段静默改义为“最终权重均值”。不向原统计字典塞整条权重向量；当前消费路径不承诺支持嵌套结构。 |
| **`b=5`** | 可保留其legacy统计分组角色；真实恶意/良性贡献在调用边界按真实身份对新权重事后分组。若整理统计实现，同一有效输入的z和末轮权重必须与统计分组无关。 | 不得把真实恶意身份、数量或`b`转为RFA筛选/降权机制；不为让旧统计名字“正确”而改变接收顺序或算法输入。 |
| **算法定义** | 允许接口扩展、有效域验证、诊断初始化与身份绑定。既定均匀alpha、零初始化、T轮数、nu、距离和归一化递推不变。 | 不得加预算、裁剪、根数据、D2′参考/门控、额外过滤、早停、热启动、数据量权重或新回退算法；不得调T/nu来让接口验收通过。 |
| **D1边界** | D1不作为本扩展的兼容验收目标，也不限制新贡献trace。D2′使用独立、显式的RFA契约；无需为了沿用D1诊断而模仿其代理字段。 | 不得复用D1的缺权重均匀兜底来满足本关；不得把恢复D1实验或D1性能回归列为放行条件。 |

默认Tensor及统计兼容要求来自当前同步桥接、原FL和混合聚合器消费，不是为已归档D1增加负担，证据见第二节。旧D1确有均匀兜底，但其贡献收集还限制为三种D1/B方法；这不构成RFA新契约。[D1桥接:202–219][D1202]

**[裁决] 观测接口与预算接口必须分开处理失败：**可选旧统计失败不改变聚合；但本关强制要求的末轮权重缺失、过期、身份错配或重构失败，必须阻止该验收/运行继续。不能套用`_aggregator_stats`“异常返回空字典”的行为，把必需贡献证据静默吞掉。

## 四、对阶段1报告的逐条核实

审查对象为[阶段1报告][P1]及其[清单][M7]。本次重新核对清单列出的源码/文档和任务文件SHA-256，均与当前文件一致；这是静态输入一致性，不是重跑执行历史。[清单:18–29][M18]、[清单:65–69][M65]

| 报告中的陈述 | 裁定 | 具体证据与限定 |
|---|---|---|
| 第36行：RFA只返回z，没有末轮归一化权重/trace接口 | **准确** | [RFA:39–60][R39]、[桥接:268–282][A268]。停止原因成立。 |
| 第37行：保存跨迭代、拆分两组的未归一化beta历史 | **准确** | [RFA:17–36][R17]。不得将其误读为最终系数已完全丢失。 |
| 第37行：b硬编码5、不绑定真实恶意身份，只用于统计 | **准确** | [RFA:45–52][R45]、[RFA:26–35][R26]；身份位置来自[桥接:232–240][A232]，没有传入RFA。 |
| 第38行：getter只返回两组跨迭代beta均值 | **准确** | [RFA:57–60][R57]；这两数不是归一化末轮系数。 |
| 第38行：同步桥接仅保留标量统计，没有权重—received_clients对应记录 | **准确（数值诊断层面）** | [桥接:87–112][A87]确实过滤多元素张量；另外允许字符串/布尔/None，不能理解为“只接受数值”。调用与日志处无权重映射：[桥接:268–282][A268]、[日志器:37–45][L37]。 |
| 第39行：D1桥接有均匀兜底，不能借用；混合聚合器保留全部客户端不等于贡献权重 | **准确** | [D1桥接:217–219][D1217]、[Hybrid:275–298][H275]。不因此要求修复D1。 |
| 第41行：不是所有内部权重信息丢失，有效迭代/顺序已知可从末轮beta归一化恢复 | **准确** | [RFA:26–36][R26]支持该判断；缺的是直接、经验证的输出契约，不是数学对象本身。 |
| 第43–49行：`[1],[3]`、T=1的系数为`(3/4,1/4)`，z=1.5；均匀会得2 | **准确（公式与记录一致）** | 由[RFA:23–35][R23]独立代入即得；清单保存这些预期及输出：[清单:82–129][M82]。本审查未重跑该Python探针，不把记录比对冒称新的运行验证。 |
| 第19行：固定RFA、4–6单元、B_M来自干净FedAvg、H/beta本轮不冻结 | **准确** | [裁剪版:63–67][C63]；原编号下B_M冻结在1.4，不能解释成需要RFA因果贡献才能算B_M。 |
| 第53行：100端、IR50/alpha0.1、根池2000、客户端池11201、隔离且无重复 | **准确（静态索引）** | 本次只读重算与[清单:31–69][M31]一致；原始[info:1][TASKINFO]、[data.json:1][TASKDATA]。标签真实性/运行时使用仍没有由索引检查证明。 |
| 第55行：普通avg/RFA无根要求，label_flip仅包装指定恶意训练端 | **准确（源码路径）** | [桥接:43–74][A43]、[桥接:243–267][A243]、[桥接:288–294][A288]。不替代未做的运行时审计。 |
| 第9/11/15/75行：分支、当前HEAD、最近提交，现有代码未改 | **准确（当前状态）** | 只读Git结果与[清单:7–16][M7]及[报告:75][P75]一致；检查开始时工作区仅有两份阶段1未跟踪交付，源码哈希与清单一致。[M18] |
| 第10/15/28/75行：“初始干净”“始终使用指定解释器”“实际0训练”“从未产生其他输出/未push”等完整执行历史 | **无法核实（独立运行审计）** | 报告与[清单:71–80][M71]、[清单:153–157][M153]一致，用户本轮也明确给定训练0单元；但静态文件和当前Git状态不能独立证明过去全部进程行为，且未联网核验远端实时状态。本裁决接受其未训练交付范围，不宣称重新审计了历史。 |
| 第61行：“本轮强制复用IR50/alpha0.1任务”中的“强制”授权来源 | **无法核实** | [报告:53/61][P53]及[清单:148][M148]记录了此要求，但未附可追溯的用户指令。设计仍写IR5/alpha1，[设计:562–567][DES562]；0.7明确其任务/参数只用于工程检查，[0.7报告:55–57][S55]。不能从0.7的PASS推出正式任务变更已获授权。 |
| 第57–66行：旧FedAvg/Smoke B/根方法/0.7不自动抵扣，实际抵扣0 | **准确（所列差异足以拒绝自动抵扣）** | [清单:144–150][M144]，与[设计:564–567][DES564]和[0.7报告:55–57][S55]的任务/预算差异相符；未证明所有历史单元都永久不可复用，报告本身也未如此声称。 |
| 第77行：需输出末轮真实归一化系数、绑定身份、重构写回、禁止兜底 | **准确；由本裁决补齐可验收语义** | 与[RFA真实递推][R19]和[同步更新方向][A122]一致。工程前置未通过不等于RFA性能或D2′机制失败。 |

**核实结论：没有发现报告对RFA迭代、统计或停止原因的实质数学错误。**“最后beta全丢了”“b=5参与防御筛选”“必须求跨迭代因果贡献”“只能在RFA函数内直接接收客户端ID才能合格”均不是报告已经证明的事实，也不应成为后续实现限制。

**[裁决] 状态处理：**保留该次尝试的“接口前置FAIL”历史及0训练记录，不把它改写成性能失败，也不触发3.4换向。语义与边界已在本裁决确定；无需再请求用户选择(a)/(b)，执行Agent可开展获准的接口扩展及验收。验收成功只解除该接口前置，不自动把合并关1.1–1.4标PASS。

### 训练输入的独立待核实项

**[推断]**设计IR5/alpha1与报告IR50/alpha0.1属于不同实验场景；仅沿用0.7工程任务不能证明后者是正式校准任务。[DES562]、[S55]

**[裁决]**这不阻止RFA接口实施，但真实训练前须由执行Agent补入已有的用户授权原文及来源。若确有授权，按用户授权执行，不要求重复确认；若不存在，则本裁决不授权覆盖设计中的IR5/alpha1。若仍想使用IR50/alpha0.1，由用户明确裁定。不要把该输入核对变成RFA数学不可行的结论，也不要由执行Agent根据好坏结果选任务。

## 五、执行Agent下一步的约束清单

以下是**[裁决]验收要求**，不是实现伪代码。工作仍归入原1.1–1.4的接口前置，不新增阶段或性能实验矩阵。

### 5.1 可以开展的工作

- 在第三节范围内扩展`aggregators/rfa.py`及必要的同步调用/诊断边界，交付`rfa_final_mix_v1`契约、身份映射证据和独立验证结果。
- 验证同一有效输入的旧z与扩展后的z一致，默认Tensor返回与旧helper三项返回兼容。可增加专门的接口/重构检查；不要求重新评估D1。
- 接口前置通过、训练输入依据核对后，继续原同步smoke与4–6完整校准单元，维持原先性能/攻击规则。

### 5.2 必须满足的性质及判据

| 验收项 | 必须交付的可检查结果 |
|---|---|
| **真实来源而非任意拟合** | 权重等于同次实际最后一轮beta归一化；记录对应输入顺序、T、nu。不得仅以“能重构z”作为全部证据。 |
| **单轮独立锚点** | `[1],[3]`、T=1、nu=1e-6、z0=0：预期权重`(3/4,1/4)`、z=1.5，均匀2.0必须被判错；预期来自手算，不从被测实现回填。[清单既有锚点][M82] |
| **多轮独立锚点** | 三个二维输入`(1,0),(0,1),(-1,0)`，T=2、nu=1e-6、z0=0。按第一节公式，首轮z为`(0,1/3)`；第二轮权重必须为`(2/(4+sqrt(10)), sqrt(10)/(4+sqrt(10)), 2/(4+sqrt(10)))`，z的第二坐标为中间权重。它不同于首轮的均匀权重，须能检出拿错迭代轮次。此项为本裁决给定的数学锚点，不是本轮运行结果。 |
| **正常边界与分组无关性** | 覆盖m小于、等于、大于5，单端、全零、相同输入、相互抵消、不同连续批次长度；权重长度/归一化/重构正确。改变纯统计分组不得改变z或末轮系数。 |
| **身份与调用一致性** | 非连续客户端ID、输入与ID同步置换时，贡献仍归同一真实身份；浮点向量结果按登记容差比较。输入/ID长度不符、阶段1重复身份、旧调用记录混入当前调用必须明确失败，不能静默截断、排序或覆盖。 |
| **失败与新鲜度** | 非法参数、空输入、非有限数值、权重缺失/长度错/分母失效必须拒绝；失败后记录不可冒用上次成功权重。连续有效调用不串批，统计读取/日志开关不改变z、随机状态或贡献记录。 |
| **数值层次** | CPU/float64合成检查逐元素`atol=1e-10, rtol=1e-8`，沿用既定规则。[完整检查点:57][F57] 必须同时检查系数与z。真实float32模型沿用独立“写回前重构＋写回舍入”两层判据，不因归档D1而取消数学核验；无需依赖D1对象/trace结构。[两层定义:17–26][CD17] |
| **模型写回** | 以`C_i=-w_i*u_i`重构传给写回的位移，再独立核对参数减法及舍入。浮点误差不能记为某客户端贡献；故意漏掉一端、翻转符号或错配权重的负例必须失败。[两层判定:80–108][CD80] |
| **调用兼容性与诊断隔离** | 实际同步桥接仍能接收Tensor并正确写回；原helper默认三项返回可用。新身份真值只影响诊断分组，不能影响RFA计算。旧统计不得被本关用作贡献来源；强制贡献缺失不能按可选统计静默忽略。 |

真实float32两层核验的既有数值界为：写回前`E_alg <= 1e-12 + 1e-5*||d||`；独立float32参考写回须与实际新参数一致；写回后`E_model <= 2e-12 + 1e-5*||d|| + ||q||`，其中q仅由旧参数与实际写回位移求得，不由重构残差定义。[两层实现:84–108][CD84] **[裁决]**允许复用数学规则或独立诊断组件，不要求继承D1接口。其他精度/设备若被采用，必须明确相应数值核验依据，不能静默放宽上述已登记条件。

### 5.3 不得实施的替代方案

1. 不得换掉固定RFA，或用均匀权重、两组均值、保留客户端集合冒充真实系数。
2. 不得用新聚合向量覆盖旧z，只为了让想要的权重重构通过；不得改变算法/参数/训练场景来修接口。
3. 不得在旁路重新训练模型或运行另一套RFA结果，拿其系数归因当前z。独立重算只作验收预期，不参与模型决策。
4. 不得以权重直接贡献界声称反事实/全局因果影响已被限制。
5. 不得把源码审查、固定张量验收或0.7smoke替代1.2可学性、1.3攻击损害和1.4冻结。

### 5.4 必须交付与放行顺序

交付一份接口前置验收记录及其配置/结果清单，至少含：本裁决版本、改动文件、实际运行的锚点/负例、默认返回兼容结果、逐ID重构证据、数值误差、旧z与新z对比、失败/统计读取行为、采用的训练任务授权依据。不得预填PASS。

**接口验收FAIL → 修复接口并重验，不开训练；接口PASS → 继续原阶段1剩余工作，不自动进入2.1。**B_M无需等待因果贡献研究，RFA基线无需承受D1兼容设计负担。若实施中发现无法满足本裁决，应报告具体违反的性质和证据，不能自行放宽语义或改用另一种基线。

## 证据索引

链接定位的是本次审查时的实际文件行；本裁决不改这些源文件。

[R9]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/rfa.py:9>
[R17]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/rfa.py:17>
[R19]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/rfa.py:19>
[R23]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/rfa.py:23>
[R26]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/rfa.py:26>
[R36]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/rfa.py:36>
[R39]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/rfa.py:39>
[R45]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/rfa.py:45>
[R49]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/rfa.py:49>
[R52]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/rfa.py:52>
[R57]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/rfa.py:57>
[A43]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/algorithm.py:43>
[A87]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/algorithm.py:87>
[A122]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/algorithm.py:122>
[A223]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/algorithm.py:223>
[A232]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/algorithm.py:232>
[A243]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/algorithm.py:243>
[A268]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/algorithm.py:268>
[A288]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/algorithm.py:288>
[L37]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/run_flgo_byzantine.py:37>
[FL244]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/fl.py:244>
[FL295]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/fl.py:295>
[MAIN27]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/main.py:27>
[MAIN37]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/main.py:37>
[MAIN90]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/main.py:90>
[H7]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/hybrid_aggr.py:7>
[H2_7]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/hybrid_aggr2.py:7>
[H275]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/hybrid_aggr.py:275>
[H427]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/hybrid_aggr.py:427>
[D1202]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_full_algorithm.py:202>
[D1217]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_full_algorithm.py:217>
[C63]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS_TRIMMED.md:63>
[F47]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:47>
[F57]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:57>
[F155]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:155>
[F199]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_CHECKPOINTS.md:199>
[DES562]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_DESIGN.md:562>
[DES564]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_DESIGN.md:564>
[S55]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE05_07_REPORT.md:55>
[P1]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE1_REPORT.md:1>
[P53]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE1_REPORT.md:53>
[P75]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE1_REPORT.md:75>
[M7]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE1_MANIFEST.json:7>
[M18]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE1_MANIFEST.json:18>
[M31]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE1_MANIFEST.json:31>
[M65]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE1_MANIFEST.json:65>
[M71]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE1_MANIFEST.json:71>
[M82]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE1_MANIFEST.json:82>
[M144]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE1_MANIFEST.json:144>
[M148]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE1_MANIFEST.json:148>
[M153]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE1_MANIFEST.json:153>
[TASKINFO]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d1_3b/smokeB_20260930/shared/tasks/cifar10/s1_m20_a0p1_ir50_v2/info:1>
[TASKDATA]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d1_3b/smokeB_20260930/shared/tasks/cifar10/s1_m20_a0p1_ir50_v2/data.json:1>
[CD17]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/contribution_diagnostics.py:17>
[CD80]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/contribution_diagnostics.py:80>
[CD84]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/contribution_diagnostics.py:84>
