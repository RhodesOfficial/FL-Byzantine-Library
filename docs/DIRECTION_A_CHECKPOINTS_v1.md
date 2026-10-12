# 方向 A（FedPCC）完整检查点结构 v1

日期：2026-10-12。范围：进入开发前至具备论文主线写作证据；本轮仅设计决策门。

**[推断] 本报告建议：基础口径独立验收；三关口按识别、估计、校准收益依次裁决；可分性探针提前；冻结骨干形成充分证据后先开放收窄版论文写作，再选择是否完成训练闭环与扩展。** 以下编号、拆分、依赖、交付结构及操作判据均为本报告建议，不是原文已经规定的流程，也不是已通过的实验结果。

## 阅读、预检与引用约定

### 本次环境预检

所有 Git 命令的实际工作目录为 `E:\Federated Machine Learning\FL-Byzantine-Library-astra\`。以下为本次现场输出记录，不能用可行性报告里的旧工作区状态替代。

|项目|实际结果|核验状态|
|---|---|---|
|`git branch --show-current`|`master`|命令成功|
|`git status`|与 `origin/master` 同步；无暂存改动；唯一未跟踪文件为 `docs/DIRECTION_A_FEASIBILITY_v1.md`|状态已查明；任务未要求干净工作区，该文件作为指定输入保留|
|`git log --oneline -3`|`902af7e docs: add non-attack research base and direction selection`；`9d0cfa8 Merge remote-tracking branch 'origin/master'`；`0cc8aa3 update papers`|命令成功|
|必需文件 1|`E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\RESEARCH_INNOVATIONS_v1.md`|存在，文件|
|必需文件 2|`E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_SELECTION_v1.md`|存在，文件|
|必需文件 3|`E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\RESEARCH_CONTEXT_NONATTACK.md`|存在，文件|
|必需文件 4|`E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_FEASIBILITY_v1.md`|存在，文件|

文件存在性检查首次出现命令语法错误，修正后四项均成功核验；后续读取和检查显式使用 `E:\anaconda3\python.exe`。未启动训练，未执行算法测试，未修改输入文件，未 commit、未 push。没有遍历 `paper/`、`master's thesis/`、`refs/`。本次不需要新增论文数字或核对 CReFF 原式，因此未打开 PDF；下文引用已有文档的分析，不冒称重新核验论文原文。

### 文档依据与停止条件核对

下文 `F`、`I`、`S`、`C` 分别指以下文件。引用统一给出文件别名、原文件行号和可点击定位；这些行号针对本次读取版本。

|别名|文件|本次阅读范围|
|---|---|---|
|F|[DIRECTION_A_FEASIBILITY_v1.md](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:1>)|全文 L1–256|
|I|[RESEARCH_INNOVATIONS_v1.md](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:44>)|方向 A 全文 L44–235；共用评价纪律与旧优先级 L678–699|
|S|[DIRECTION_SELECTION_v1.md](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:122>)|第五节 L122–152；识别论证 L19–36；结论边界 L154–160|
|C|[RESEARCH_CONTEXT_NONATTACK.md](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_CONTEXT_NONATTACK.md:89>)|T6、T7、T8、R01、R05 卡片相关内容，以及共同前提、长尾与参与边界 L248–268|

**三关口原文逐行照录**，来源为 [S §五 L134–138](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:134>)：

|关口|继续主线需要看到什么|失败后的裁决|
|---|---|---|
|A 的识别前提|训练计数可得、目标来源有正支持；有可观测的类内来源偏差；邀请与完成日志能区分。|[推断] 若来源偏差基本不存在，应否定该场景下的主创新需求；若永久缺席导致不可识别，不能靠调截断权重补救。|
|A 的估计环节|固定参考模型下，真实概率与实际估计概率版本的误差可分解；实际版本相对目标匹配对照具有可重复的误差优势。|[推断] 仅真实概率有效时，说明实际概率环节未通过，不能把诊断版本当成果。若有限预算下仍无法识别足够信息，暂停 A。|
|A 的校准与收益环节|同版本、同优化预算下，估计优势能传到校准残差与尾类指标；明确头类/客户端代价。|[推断] 若 (A7) 是瓶颈，先依据 v1 已有的直接分类器梯度对照及冻结骨干降级范围定位；不得把未成立的合成校准写成成功。若可分表征与这些对照仍无收益，停止扩大 A。|

模块核对：完成概率模块见 [I L83–89](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:83>) 与 [F L114–125](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:114>)；缓存校正模块见 [I L91–143](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:91>) 与 [F L127–140](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:127>)；合成匹配、重训和版本模块见 [I L145–177](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:145>) 与 [F L142–165](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:142>)。未发现模块定义不一致。

执行顺序依据是 [F §四 L203–213](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:203>)。旧创新文档在表征失败时建议优先考虑 C，见 [I L228](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:228>)；裁决文档明确将 B 前移为唯一备选，并说明这是独立修订，见 [S L140–152](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:140>)。因此本报告按 S 的修订组织转向，不把这项已解释的顺序更新当作模块冲突。

背景仅按本地基座引用：标签偏斜与全局长尾应区分，见 [C L92–96](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_CONTEXT_NONATTACK.md:92>)；分类器偏置、额外校准成本及梯度不能唯一确定特征的边界，见 [C L162–166](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_CONTEXT_NONATTACK.md:162>)；参与偏差与尾类保留的待研究设定及成本边界，见 [C L260–268](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_CONTEXT_NONATTACK.md:260>)。不把本地文献覆盖范围外推为全领域新颖性。

**[推断] 本次没有触发“信息缺失则停止”的条件。** 尚未构建的任务清单、概率机制、合格快照、实测资源与实验结果，已被 F 列为后续验证对象（[F L239–249](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:239>)），本报告将其设为未来关口的必需输入或交付，不假定其存在。未来执行时缺少这些交付必须停在对应关口，不能沿用本报告中的“计划”当作已完成证据。

## 一、检查点总览

**[推断] 下表全部为本报告建议。** `G1/G2/G3` 是决策关口编号；原文“模块 A1/A2/A3”和“式(A1)–(A8)”仍保持原含义。`P` 是提前探针，`T` 是理论审计，`M` 是收窄版写作门，`E` 是完整方案后续工作。smoke 是各关内部的小规模验收，不能独立给研究关口盖章。

|编号|名称|硬依赖与可并行关系|
|---|---|---|
|0.0|现场与输入预检|起点；本轮已完成|
|0.1|研究口径、预算与判据冻结|0.0|
|0.2|基础口径验收|0.1；含基础 smoke|
|G1.1|训练计数、邀请完成事件与正支持|0.2；可与 G1.2 并行|
|G1.2|冻结参考与类梯度测量验收|0.2；可与 G1.1 并行；含梯度 smoke|
|P|提前的可分性与校准空间探针|G1.2；可与 G1.1、G1.3、G2 并行|
|G1.3|来源偏差识别裁决：第一关总验收|G1.1＋G1.2；不以 P 通过为必要条件|
|G2.1|历史概率预测接口验收|G1.3；可与 G2.2 并行；含概率 smoke|
|G2.2|缓存校正算术与状态验收|G1.3；可先用固定概率输入，不等 G2.1；含缓存 smoke|
|G2.3|条件重复、历史回放与实际优势：第二关总验收|G2.1＋G2.2|
|T|条件命题、误差分解与主张边界审计|G2.2 后启动；与后续实验并行，范围定稿后收尾|
|G3.1|同预算直接分类器更新诊断|G2.3＋P 合格；含直接更新 smoke|
|G3.2|受约束合成目标可实现性与成本|G2.3＋P 合格；通常接 G3.1 后；有余力可并行；含 A7 smoke|
|G3.3|冻结骨干校准收益与收窄裁决：第三关总验收|G3.1＋G3.2 的完整记录；合成路线另需 G3.2 通过；含 A8 smoke|
|4.1|比较线、评价和预算完整性验收|0.2 后可准备；正式验收依赖 G3.3 的范围裁决|
|4.2|最小论文证据包复核|G3.3＋4.1；与 T 收尾并行|
|M|可开始写收窄版论文的决策门|4.2＋T；是最小研究方案的写作起点|
|E1|普通骨干训练闭环、版本与恢复|M 后；含端到端 smoke|
|E2|完整训练方案主结果复验|E1；沿用 4.1 的比较口径|
|E3|规模、压力与失败边界扩展|E2；独立单轴实验可并行|
|E4|完整方案论文证据封版|E2＋E3＋更新后的 T/4.1 审计|

### 共用的可检查裁决规则

**[推断] 以下是本报告新增的操作规则，依据原文“预先固定判据、有限预算、配对重复、不提前许诺成功百分点”的要求细化。** 依据：[F L67、90](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:67>)、[I L682–688](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:682>)。

- 每关交付一份决策记录：输入版本与哈希、配置、实际预算、指标分母、对照、逐种子结果、证据路径、结论及其范围。状态只能是“通过”“修正后重跑”“收窄后重验”“证据不足/预算耗尽”“停止当前范围”。smoke 通过另记，不能替代正式通过。
- 0.1 必须填实并冻结：数值误差容差 `ε_num`、偏差实质阈值 `ε_bias`、探针门槛 `τ_probe`、匹配容差 `ε_match`、允许的头类/客户端代价界限、attempt 上限、各阶段时间/字节/搜索预算及最多修订次数。这里不虚构未测量的数值；“字段已填、单位已定、来源可追溯、冻结于主结果之前”本身是结构性判据。未完成时不能进入依赖它们的正式实验。
- 对误差用“对照误差减实际版误差”，对收益用“实际版指标减目标匹配对照指标”定义配对差值，使正数统一表示改善。至少 3 个配对种子是文档要求；本报告建议同时给逐种子方向、均值、标准差及预先约定的配对不确定性区间。若区间不能支持正优势，只能判“证据不足”，在预定重复上限内补充，耗尽则不通过；不以客户端数量冒充重复次数。
- 主要成功设定预先指定为拟议的尾类端偏慢主点；随机、尾类端偏快作为配对机制对照，不要求 A 在所有设定、所有类别必胜。主场景、主指标、参考点和汇总方式必须先固定；阴性对照不符合预期也须解释，不能删掉。
- 任何数据、总体、参考模型、概率机制或评价定义变更，都有明确回退点：split/count 变更回 0.2；完成机制变更回 G1.1；参考变更回 G1.2/P；估计器变更回 G2.1/G2.2；校准目标变更回 G3.2。下游结果不得自动继承“通过”。
- 每关第 7 项只列本报告新增的、跨关交付才会产生的边界，并给推导依据。原文已明写的公式、信息限制、版本顺序等放在输入引用与验收项中，不在第 7 项复述成“新约束”。

## 二、每个检查点的完整定义

### 0.0 现场与输入预检

1. **名称与编号：**0.0，现场与输入预检。
2. **输入：**本次任务指定的根目录、解释器、四个文件和只读分析边界。
3. **产出：**本报告前部的分支、状态、三个 commit、绝对路径与存在性记录；文档范围核对。
4. **通过判据：**Git 三项成功；四份文件可读取；F 全文、I 方向 A、S 第五节及 C 相关部分可定位；三模块和三关口无未解释冲突。本轮通过；这不代表任何研究关口已通过。
5. **不通过处置：**立即停止，列出缺失文件或冲突原文的文件与行号；不补造内容。
6. **依赖关系：**最前置，不能与依赖文档内容的设计结论倒置。
7. **本关特有约束：**[推断] 后续执行者重做预检时，不得把本报告的状态表当作当前现场证据；它只认证本次输入时刻。依据：F 自身将存在性和状态限定为“本次实际输出”，见 [F L9–29](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:9>)。

### 0.1 研究口径、预算与判据冻结

1. **名称与编号：**0.1，开发前的研究合同。
2. **输入：**0.0；[I L58–89、185–218](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:185>)、[F L90、244–247](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:244>)及本报告共用规则。
3. **产出：**一份配置和判据清单，写明总体、标签空间、split、IF/α 的含义、模型、骨干来源、训练与校准工作量、事件机制、指标、对照和资源上限。列明主设置、smoke 设置及其差异；列明计划采用冻结合成路线或待裁决的直接路线。
4. **通过判据：**清单必填项无空缺；拟议主设置为两种 CIFAR-LT、ResNet-8、20 端、40% 邀请、α=0.1、IF=100、三种速度对应关系及每主设置 3 个配对种子；200 更新轮的初始上限之外另有独立 attempt 上限。未完成资源测量时可先批准有界 smoke，但正式阶段预算冻结前不能开跑正式实验。协议明确每项成功/失败由哪个指标及哪个阈值裁决。[I L191–196](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:191>)、[F L230](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:230>)。
5. **不通过处置：**缺定义则补定义；缺资源测量则仅安排相应 smoke；不以任意成功百分点填空。范围变更必须留修订理由，再验收。
6. **依赖关系：**0.0 后；是 0.2 的输入。预算测量可按阶段补交，未补交的阶段保持关闭。
7. **本关特有约束：**[推断] 数据集、模型和主点的“试运行替代值”必须拥有不同的配置身份，不能在后面仅改文件名升级为主实验。依据：F 区分历史任务与 A 参考资格，见 [F L215](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:215>)；本条将这一边界延伸至新建 smoke 产物。

### 0.2 基础口径验收

1. **名称与编号：**0.2，数据、模型、评价共同基础。
2. **输入：**0.1；[F §三 L174–175、181–182](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:174>)及 [F L207](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:207>)。
3. **产出：**A 专用任务清单、最终 train/validation/test 索引和哈希、全端全类计数矩阵、模型适配验收、评价分母与成本字段说明。
4. **通过判据：**先做小样本基础 smoke，再验收正式任务：索引守恒、约定集合互斥；逐端训练计数加和等于总体训练计数；类别维度分别为 10/100；缺类、单来源、多来源均显式记录；模型完整前向与 encode/head 拼接结果在 `ε_num` 内一致；参数、BN、损失及变换定义齐备；独立客户端测试和头/中/尾分组规则确定。正式任务不因 smoke 通过而免检。
5. **不通过处置：**修共同基础并重跑；计数或评价错误不触发换方向。依据：[S L146](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:146>)。
6. **依赖关系：**0.1 后独立封版；随后 G1.1、G1.2 可并行。
7. **本关特有约束：**[推断] 本关封存的计数和分组表只由基础任务交付产生；后续估计器或校准器不得各自重算一份并悄然替换。若需重算，必须回到本关比较差异并作废依赖旧表的结论。依据：注册表的不可变设计 [F L120](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:120>) 与共同基础先验收 [F L207](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:207>)。

### G1.1 训练计数、邀请完成事件与正支持

1. **名称与编号：**G1.1，识别前提中的观测与支持。
2. **输入：**0.2；[F L60–63、118–123](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:118>)及 [I L85–89](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:85>)。
3. **产出：**注册清单；计划邀请、派发、掉线、超时、有效返回的事件轨迹；每个有训练样本的来源的正支持证据；诊断概率的来源与误差说明。
4. **通过判据：**所有目标端注册成功，所有 `n_ic>0` 来源有 `q_i>0` 和 `r_i>0` 的机制依据；计划邀请与有效完成逐条可对应；空返回尝试仍被计入日志和预算；三种速度分配保持同一速度集合；固定工作量包含协议声明的新增计算；真实概率通道可单独审计。短轨迹必须覆盖按时、未派发、掉线、超时、全失败及重复 round 下不同 attempt。
5. **不通过处置：**事件实现错误修正重跑；若机制证明某来源永久缺席，则原总体目标不通过；如缩小总体，回 0.1/0.2 重定义，不能沿用原来的总体主张。有限零返回只记录观测不足。
6. **依赖关系：**0.2 后；可与 G1.2 并行，二者都完成后才到 G1.3。
7. **本关特有约束：**[推断] 本关封存的是可回放的机制与事件方案，不能先用 G2 的误差好坏挑选一条“最合适”的事件轨迹再追认 G1 通过。依据：固定配对事件与预定预算要求 [F L80、90](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:80>)；这是对关口交接的额外限制。

### G1.2 冻结参考与类梯度测量验收

1. **名称与编号：**G1.2，可信的测量对象。
2. **输入：**0.2；候选快照的生成配置和任务哈希；[F L77、133–136、215](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:133>)及 [I 式(A1) L58–65](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:58>)。
3. **产出：**合格参考包、逐端逐类完整分类头梯度、全端目标诊断包及对应成本。快照不合格或缺失时，交付的是缺失项清单，不能交付“可用参考”的结论。
4. **通过判据：**先做梯度 smoke：含偏置/不含偏置按声明实现，包含完整输出维度；单端类均值与逐样本平均在容差内一致；`G_c` 与按 `a_ic` 汇总一致；重复读取参考后参数与缓冲哈希不变；缺类不产生伪梯度；完整数据梯度与小批量噪声口径有明确选择。正式参考须匹配模型、split、IF/α、训练记录与变换；至少按 0.1 指定的多个参考点留包。
5. **不通过处置：**测量错误修正；缺合格快照则停在此关，列出需提供的 checkpoint、生成配置和任务清单。未来单独完成合格骨干准备后再进入；本报告不假定已有文件可直接用。
6. **依赖关系：**与 G1.1 并行；通过后可立即开 P，不必等待第一关总裁决。
7. **本关特有约束：**[推断] 不得用“本参考使 FedPCC 更好”作为参考资格条件；参考资格与方法收益的记录应分别签定。依据：多参考点核验 [F L242](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:242>) 和快照资格边界 [F L215](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:215>)。

### P 提前的可分性与校准空间探针

1. **名称与编号：**P，第三关所需表征条件的提前诊断。
2. **输入：**G1.2 的合格参考及 0.2 的独立验证；[F L106、209](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:209>)、[I L175、228–235](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:228>)。
3. **产出：**冻结特征的均衡线性探针结果；参考头、探针头及无信息对照的验证损失和逐类召回；尾类可分性、可改善空间及诊断成本记录。
4. **通过判据：**探针训练只用训练数据，选择只用验证；达到预先冻结的 `τ_probe`，且尾类表现不能由无信息对照解释；同时记录参考头到探针的改善空间。判“可分但校准空间不足”时不可当作第三关收益预期的正证据。判据不引用历史小 CNN 的门槛替代当前参考。
5. **不通过处置：**先排查数据、参考和训练资格；只否定或收窄该表征场景。需要新合格快照则回 G1.2；不能仅据 P 失败断言实际估计失效或自动切 B/C。
6. **依赖关系：**可与 G1.3 和 G2 并行；G1.3/G2 的数学与估计结论不依赖 P 成功；G3 正式收益验收依赖 P 合格。
7. **本关特有约束：**[推断] 若探针促使更换参考，旧参考上的 G1.3/G2 结果只能保留为旧范围证据，不能与新参考的校准收益拼成一条机制链。依据：同版本要求 [I L173](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:173>)；本条是跨关证据拼接边界。

### G1.3 来源偏差识别裁决

1. **名称与编号：**G1.3，第一关总验收。
2. **输入：**G1.1＋G1.2；[S L23–34、136](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:23>)与 [F L65–69、208](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:65>)。
3. **产出：**每类持有端数、来源梯度差异、`G_avail−G` 的范数及相对量、三种速度配对和多参考点结果；第一关决策记录。
4. **通过判据：**注册、支持、事件三项已通过；在预定主场景和汇总类别范围内，可用性加权目标与全端目标的差超过预定 `ε_bias`，并经重复/概率近似误差核验仍可辨认。相对量分母的零范数处理预先声明。至少报告全类汇总、尾类汇总和每类值，标明单来源及近同梯度退化。均匀概率对照应在容差内给零来源偏差；非均匀概率不预设必定非零。
5. **不通过处置：**实现错误回前关；偏差基本不存在则停止该场景的来源校正主张；低支持仅有覆盖/方差问题时按该事实记录。达到预算仍不能判断则暂停当前范围，不为制造偏差事后改数据。
6. **依赖关系：**G1.1/G1.2 后；通过才开放 G2 正式验收。P 可独立继续诊断。
7. **本关特有约束：**[推断] 每次通过都绑定具体总体、速度分配与参考集合；不得凭一个场景通过给全部拟议场景统一放行。依据：F 将快速否定和失败限定在声明场景 [F L208、215–217](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:208>)，这里对正结论作同样的范围管理。

### G2.1 历史概率预测接口验收

1. **名称与编号：**G2.1，完成概率的实际可用接口。
2. **输入：**G1.3；G1.1 事件契约；[F L116–123](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:116>)。
3. **产出：**逐尝试的历史截止点、邀请/完成计数、平滑、`r_hat/p_hat/p_tilde` 和截断记录；实际与诊断概率的分离验收。
4. **通过判据：**概率 smoke 使用可手算短序列：未邀请不增加完成率分母；邀请未完成增加分母；当前事件改变时当前预测不变、下一次预测按规定变化；完全无历史时的先验明确；实际预测范围合法、截断比例可计算。固定前缀后置换未来事件，前缀输出必须一致。诊断真值可用于评价预测误差，但正式结果尚不要求概率接口单独赢得最终收益。
5. **不通过处置：**分母、时序或通道错误修正重跑；预测不准但实现合格，交由 G2.3 按有限预算裁决，不在本关无限调参。
6. **依赖关系：**G1.3 后，可与 G2.2 并行。
7. **本关特有约束：**[推断] G2.1 交付时冻结概率输出及历史边界；G2.2 不得为了减小当前残差而反向改写本次概率。变更预测规则必须退回 G2.1 并重做 G2.3。依据：概率和缓存先冻结的算法顺序 [I L143](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:143>)；本条规定两子关的交接权责。

### G2.2 缓存校正算术与状态验收

1. **名称与编号：**G2.2，缓存估计器的正确性。
2. **输入：**G1.3；固定概率接口契约和手算输入；[I 式(A3)–(A6) L93–143](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:93>)、[F L79、129–140](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:129>)。
3. **产出：**手算/小数组对照、估计前后状态记录、seen/age/version、未覆盖与截断统计；缓存内存账本。
4. **通过判据：**缓存 smoke 核对式(A3)输出；零缓存、全返回、空返回、旧缓存等于当前梯度、极小正概率、缺类、首次观测均有案例；估计前旧值与刷新后新值可区分；加权缓存和与直接求和在容差内一致；固定数邀请的经验期望核验不误套独立方差式。此关只验正确性，不能把恒等式通过写成均方误差获胜。
5. **不通过处置：**算术或状态错误修正；内存超预算先量化条目和副本，按预定允许实现选择处理后重验；若改变估计式则停止沿用 A 的原公式结论，先补新的定义审查。
6. **依赖关系：**可不等 G2.1，用固定输入验算；接真实历史预测后的总验收必须等 G2.3。T 可在本关通过后启动。
7. **本关特有约束：**[推断] smoke 中人为设置的“完美缓存”“全返回”等状态不能直接作为正式轨迹的初始存档；正式起始状态须由协议指定并重新生成。依据：零/未见初始化 [I L93、143](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:93>) 与条件重复、历史回放的区分 [F L86](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:86>)。

### G2.3 条件重复、历史回放与实际估计优势

1. **名称与编号：**G2.3，第二关总验收。
2. **输入：**G2.1＋G2.2；G1 冻结数组和事件方案；[F L79–90、210](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:79>)及 [S L137](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:137>)。
3. **产出：**两份互不混用的误差报告：固定 `h,g` 的条件重复；逐次更新历史的完整回放。包含真实概率、不截断估计概率、截断实际概率，以及无校正、仅逆概率、仅缓存、缓存加逆概率。
4. **通过判据：**在共同目标、消息和事件预算下，实际版本对目标匹配无校正对照的预定主误差指标有可重复正优势；本报告建议主误差采用全类等权 MSE，同时报逐类和尾类 MSE。概率、截断、缓存残差对误差的贡献可定位；共同固定 `h,g,I` 时的版本差量与直接计算一致；随历史更新仍保留实际优势。至少 3 个配对种子，区间不足以支持优势则不通过正式裁决。原始持有端等权对照另列，不替代目标匹配对照。
5. **不通过处置：**真实版有效、实际版无效：只在冻结预算内排查概率与日志，仍失败则暂停 A；真实版也无效：核对目标、缓存残差和方差，再判收窄/暂停；正支持但有限预算效果差记录为实际不可用。不得用真实版替代实际版毕业证据。
6. **依赖关系：**G2.1/G2.2 后；通过才开放 G3 正式收益结论。P 可与本关并行，尚未合格时只完成估计结论。
7. **本关特有约束：**[推断] 固定缓存重复报告与历史回放报告必须各有独立通过栏；其中一个通过不得覆盖另一个失败。依据：[F L86](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:86>) 的两类实验区别；这是防止跨实验替代的交付约束。

### T 条件命题、误差分解与主张边界审计

1. **名称与编号：**T，理论证据与实验命题对齐。
2. **输入：**G2.2；[I L104–143、183、216](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:104>)与 [S L21–36](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:21>)。
3. **产出：**条件表、式(A4)/(A6)推导核对、固定数量邀请的协方差说明、各误差项与日志字段映射、理论命题与实测命题清单；范围收窄时相应修订。
4. **通过判据：**每个等式的条件、随机量和条件化对象明确；不把(A5)无协方差式用于固定数邀请；实际截断版未被称作自动无偏。最小理论交付为条件期望与偏差分解及校准断点的清晰解释；若论文声称局部下降界，则必须补完整假设和推导，否则删去该强主张。完整深网统一收敛不设为本关前置，依据 [I L183](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:183>)。
5. **不通过处置：**修证明或收窄理论主张；若暴露目标/实现不一致，回对应 G2/G3 节点重验；不能以经验曲线补一个不成立的等式。
6. **依赖关系：**G2.2 后并行开展；最终路线由 G3.3 决定后收尾；M 和 E4 均需审计通过。
7. **本关特有约束：**[推断] 推导稿必须标注它对应的估计器和校准路线版本；从合成路线转为直接路线后，不能只换标题而沿用未适用的校准证明。依据：理论目标与冻结降级范围 [I L183、235](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:183>)。

### G3.1 同预算直接分类器更新诊断

1. **名称与编号：**G3.1，先检验估计是否能产生有用更新。
2. **输入：**G2.3＋P 合格；[F L106–108、211](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:106>)。
3. **产出：**冻结同一骨干和参考头上的直接更新对照；无校正与实际校正梯度的同消息比较；损失、尾类、头类、客户端和成本差值。
4. **通过判据：**先做一步更新 smoke，核对更新方向与步长；在相同允许消息和预算下验证实际估计带来的头部收益。若做多步新参考梯度，新增请求和费用完整计入；真实全端更新只列诊断。作为后续直接路线候选，实际版必须相对无校正直接更新有可重复的预定尾类主指标收益并报告代价；只比原参考头改善不足以支持“来源校正有用”。
5. **不通过处置：**若 P 合格、G2 优势存在但直接更新无收益，记录梯度到效用的断点；结合 G3.2/G3.3 定位，不能凭这一项单独宣告合成路线失败。预算耗尽后不扩展新的骨干修复模块。
6. **依赖关系：**通常先于 G3.2，帮助低成本定位；可提前做 smoke，但只有 G2.3/P 完成后才有正式研究裁决效力。
7. **本关特有约束：**[推断] 直接路线候选的训练/验证选择规则须先冻结，再与合成路线比较；不能在看完两者测试成绩后，只给获胜路线追加调参预算。依据：共同优化与搜索预算 [F L99](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:99>)。

### G3.2 受约束合成目标可实现性与成本

1. **名称与编号：**G3.2，式(A7)单独验收。
2. **输入：**G2.3＋P 合格；G3.1 记录可先提供；[I L149–171](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:149>)、[S L34](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:34>)及 [F L245–246](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:245>)。
3. **产出：**真目标诊断正对照、真实概率估计目标及实际估计目标的匹配曲线；同校正器余弦对照；到估计目标和到真目标的双残差；资源测量。
4. **通过判据：**先做小类数 A7 smoke，再做 `C=100、20端` 资源样例；真目标正对照在声明预算内达到预定匹配容差，或达到预定相对初值下降标准；实际目标匹配可稳定执行，半径约束违规为零，所有非有限值为零。实际版到真目标的残差优势需与目标匹配无校正校准比较；同时报告不可实现目标及发生比例。时间、内存、字节均在阶段预算内。此关不以匹配残差替代尾类收益。
5. **不通过处置：**真目标都匹配不好先查实现/优化；真目标可匹配而校正目标不可匹配，定位可实现性或幅值问题，按已有余弦对照核验。达到约定修订次数仍成本超标或不稳定，停止扩大合成链，向 G3.3 提交失败记录和直接路线证据。
6. **依赖关系：**通常 G3.1 后；有资源可并行准备。合成路线的 G3.3 必须等本关通过；直接收窄路线需要本关失败/成本裁决记录，不要求把失败修成成功。
7. **本关特有约束：**[推断] 不得在交付给 G3.3 时把未能匹配的类或尝试从分母中删去；“成功匹配子集”只能作为附加诊断。依据：支持不全仍报告全类 [I L177](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:177>)；本条把该评价原则延伸至匹配失败的交付。

### G3.3 冻结骨干校准收益与范围裁决

1. **名称与编号：**G3.3，第三关总验收及 A/B 转向裁决。
2. **输入：**G3.1、G3.2 完整记录，G2.3/P 通过；[F L94–110、211–213](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:94>)与 [S L138–146](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:138>)。
3. **产出：**A8 短运行验收、冻结骨干收益与成本报告、头/中/尾及客户端代价表，以及三选一的范围裁决：保留冻结合成路线、收窄为直接分类器路线、停止扩大 A 并提交 B 转向评估。
4. **通过判据：**合成路线先完成 A8 smoke，再证明“G2 实际估计改善→到真目标的校准残差改善→预定尾类指标改善”，各段绑定同一参考与预算；相对目标匹配无校正校准，主尾类收益具有配对重复支持，头类/客户端代价满足 0.1 已接受的范围或先收窄主张再重验。直接路线只有在 G2.3 通过、G3.1 实际校正对无校正直接更新有独立收益且 G3.2 瓶颈记录成立时，才可进入收窄候选。该状态明确写“直接路线范围通过；原合成 A3 未通过”，不能标完整 FedPCC 通过。
5. **不通过处置：**先检查版本、预算与评价；确认可分表征、有效支持、实际估计及已有对照后仍无同预算收益，停止扩大 A。若只有合成链失败而直接路线已形成清晰贡献，先收窄 A；若匹配/成本持续瓶颈且不能合理收窄，触发 B 评估。工程基础错误回 0.2，不触发换题。
6. **依赖关系：**第一、二关及 P 均不可省略。G3.3 是投入完整训练闭环前的最终方向裁决；通过某条收窄路线后到 4.1/4.2。
7. **本关特有约束：**[推断] 裁决记录必须保留“原合成路线状态”和“收窄路线状态”两个独立字段；不得通过改名覆盖原失败。依据：合成瓶颈与直接降级必须区分 [F L108、213](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:108>)。

### 4.1 比较线、评价和预算完整性验收

1. **名称与编号：**4.1，论文比较是否回答同一个问题。
2. **输入：**G3.3 的路线与主张；[I L200–210、682–688](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:200>)；[F L98–102、187–191](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:187>)。
3. **产出：**比较矩阵，逐行注明原论文方法、复现或适配、骨干来源、目标、消息、版本、优化与搜索预算；评价和实际成本账本；未复现项的阻塞清单。
4. **通过判据：**文档列出的 FedAvg、FedProx、Fed-LTNF、q-FedAvg、原版 CReFF、样本加权无校正 CReFF 以及可选 IPW 构造对照有明确身份与用途；决定性四项估计消融齐备。比较线数量不能把本文变体算成独立已发表方法。冻结路线的核心因果对照共享骨干和参考；使用不同骨干训练策略的外部基线另报完整训练成本，不能冒称同骨干对照。采用适配版须注明改变；实际校正直接路线须另有无校正直接路线。所有全局/客户端测试分母、未覆盖类、最低端不确定性、注册/诊断/方法费用均可追溯。拟省略基线必须在正式证据封版前形成有依据的范围修订，不能默默删项。
5. **不通过处置：**缺基线或资源核算则补齐；尤其 Fed-LTNF 的实现可用性和工作量在 F 中仍未确定，本关执行时必须定向核对方法与本地入口，缺资料则停下列文件。不能因此删掉目标匹配对照。不能完成既定比较矩阵时，M 保持关闭，先调整并重新验收论文范围。
6. **依赖关系：**比较规格可从 0.2 后准备；最终验收依赖 G3.3。未开展的算法复现不由本报告暗示已经完成。
7. **本关特有约束：**[推断] 原版、流程对齐版、目标加权版应有分别可识别的结果身份；汇总程序不能因显示名称相似而合并行。依据：F 要求原版和受控版本分开命名 [F L110](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:110>)；这里落实为证据汇总边界。

### 4.2 最小论文证据包复核

1. **名称与编号：**4.2，从一次可行转为可写的证据。
2. **输入：**G3.3＋4.1；[I L191–218、233–235、685](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:191>)及 [F L213、253](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:213>)。
3. **产出：**两数据集冻结骨干主证据包、逐种子原始结果、主表与机制图、消融、成本及失败边界；每个论文候选结论对应的证据索引。
4. **通过判据：**本报告建议最小包仍保留两数据集、20 端主点、三种速度对应关系、每主设置至少 3 个配对种子和经 4.1 验收的比较矩阵；把节省集中在不做完整训练闭环与大范围扩展。G1/G2/G3 的正结果需在声明支持的场景复现，不只靠一个快照或最佳种子；阴性场景、失败与额外成本完整呈现。对第二数据集不成立的结果必须缩小跨数据集主张，重新评估剩余贡献后再判是否通过，不能默认单数据集足够。
5. **不通过处置：**证据不稳在预算内增加重复；超出预算则写明证据不足，回 G3.3 收窄或停止。估计优势与尾类收益不能同时建立时，不开放该因果链的写作结论。
6. **依赖关系：**G3.3＋4.1；可与 T 并行收尾；完成后交 M。
7. **本关特有约束：**[推断] 主表中的每一行必须反向定位到同一组登记过的原始产物；不得把不同预算、不同种子集合的最优列拼成一个“方法结果”。依据：配对差值与同预算要求 [F L80、99](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:80>)。

### M 可开始写收窄版论文的决策门

1. **名称与编号：**M，最小研究方案的论文写作资格。
2. **输入：**4.2＋T；G3.3 的范围裁决；[I L183、235](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:235>)与 [S L142、158](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:142>)。
3. **产出：**论文题目范围、两个递进章节的贡献表、主结果清单、局限与失败表、待补非关键事项；明确所写的是冻结合成校准，还是已获证据支持的直接分类器校准。
4. **通过判据：**每个核心贡献同时有成立条件、机制证据、目标匹配对照、收益/代价及资源证据；两章节可分别落在参与偏差估计和所选分类器校准路线；不存在以真实概率代替实际算法、以诊断探针代替方法输入、以合成失败冒称成功的主张。题目和摘要限定冻结骨干范围。M 表示可启动主线写作，不是保证学位审核通过。
5. **不通过处置：**缺核心证据回 4.2；缺独立贡献回 G3.3 重裁范围；不靠增加无关模块凑章节。
6. **依赖关系：**4.2＋T；通过即可以开始收窄版论文写作。E1–E3 是本报告建议的后续完整方案，不能成为拖延已成立收窄方案写作的默认理由。
7. **本关特有约束：**[推断] 论文贡献表应分别标“已有证据”和“待扩展”；后者不得进入摘要的完成式结论。依据：静态可行与经验效果的区分 [F L253](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:253>)，这里延伸到分阶段写作。

### E1 普通骨干训练闭环、版本与恢复

1. **名称与编号：**E1，完整训练生命周期验收。
2. **输入：**M；本报告完整 FedPCC 路线要求 G3 合成路线通过；[F L98、150、183、195–197、249](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:183>)与 [I L173–175](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:173>)。
3. **产出：**普通模型、参考模型、校准模型、下一骨干的完整时间线；所有状态恢复验收；终点校准与成本记录。
4. **通过判据：**先短闭环 smoke，至少经过一个参考版本切换并覆盖空返回、迟到、支持集为空/不全；所有评估对应正确参考与 BN；中断恢复和连续执行的下一事件、概率、缓存估计在确定性/数值容差内一致；RNG、优化器、特征、attempt 与预算恢复齐备；最终校准重新计费。smoke 后才开放 E2 的长运行。
5. **不通过处置：**修生命周期并重验；若完整闭环成本过大或收益不可复现，保留已通过 M 的冻结范围，不倒改其证据。若 M 通过的是直接路线，不能自动称为完整三模块 FedPCC，须先补 G3.2/G3.3 合成路线验收或保持收窄路线。
6. **依赖关系：**M 后，按本报告建议顺序避免过早投入；与收窄版论文撰写可以并行。
7. **本关特有约束：**[推断] 冻结参考证据包作为只读回归输入保留；训练闭环的新缓存、模型和恢复文件不能覆盖该包。依据：冻结与训练生命周期两种验收范围 [F L69、183、213](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:183>)。

### E2 完整训练方案主结果复验

1. **名称与编号：**E2，变化骨干下的主链有效性。
2. **输入：**E1；4.1 比较矩阵；[I L191–218、226](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:191>)与 [F L189](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:189>)。
3. **产出：**双数据集完整主训练结果；随轮次的来源/估计/匹配误差、缓存年龄、覆盖、精度和预算轨迹；最终模型评价。
4. **通过判据：**沿用主点、配对种子和三速度场景；比较线共享已声明邀请机制、普通骨干规则和评价；实际概率版的机制与收益证据在选定训练参考点仍成立；终点及达到共同验证目标所需时间/字节完整报告；未达目标明记预算内未达。不得把静态快照结果直接视为动态闭环证明。
5. **不通过处置：**按 G2/G3 误差来源回退核验；只在预定预算内调整校准频率等原范围设置。若冻结证据仍成立而动态失败，收回完整训练主张，回 M 写冻结范围。
6. **依赖关系：**E1 后；通过后开展 E3 的扩展，不以扩大规模弥补主点失败。
7. **本关特有约束：**[推断] 完整训练和冻结方案的结果必须分表或明确分层，不能把前者训练成本和后者最佳校准精度配成一个结果点。依据：训练/机器时间与冻结诊断范围的区分 [F L104、185](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:104>)。

### E3 规模、压力与失败边界扩展

1. **名称与编号：**E3，主点之外的证据边界。
2. **输入：**E2；[I L192–193、224–227](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:192>)及 [F L140、246](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:140>)。
3. **产出：**100 端一次扩展、20% 邀请压力、α/IF 单轴变化、一次速度分组交换、低概率及永久缺席边界记录；相应资源与限制表。
4. **通过判据：**扩展设置有独立登记、资源测量和有效结果；一次扩展的复现范围与种子数清楚，不能外推到任意规模。预期失败边界能被诊断记录，不要求全部压力点获胜；每项泛化主张必须有对应的配对证据，无证据则不写该主张。多轴不同时改动作为主要归因依据。
5. **不通过处置：**若主点仍成立，收缩扩展主张并如实报告失败；资源不足可保持 M/E2 的范围，不能声称已完成原拟议规模扩展。若发现主点共用错误，回溯重验受影响关口。
6. **依赖关系：**E2 后；各单轴实验可以并行，共享只读主点配置，不能互相修改输入。
7. **本关特有约束：**[推断] 100 端或漂移压力失败不得被用于追溯性更换 20 端主点的种子、尾类划分或成功定义。依据：主点先行与单轴展开 [I L193](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:193>)；本条固定主证据与扩展证据的关系。

### E4 完整方案论文证据封版

1. **名称与编号：**E4，完整三模块方案的写作资格。
2. **输入：**E2＋E3，以及更新后的 T、4.1；[I L214–218、233–235](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:214>)和 [S L156–158](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:156>)。
3. **产出：**完整结果索引、结论—证据对应表、成本和限制清单、最终写作范围，保留所有收窄和失败记录。
4. **通过判据：**完整三模块主张由变化骨干实验支持；所有基线身份、假设、公式、图表、配对结果与预算可追溯；扩展失败只限制相应主张，没有被省略；不存在待补的核心证据。通过后可写完整方案论文。
5. **不通过处置：**缺核心结果补证据；只有扩展主张不成立则删减该主张；完整方案不成立但 M 的证据未受影响则退回冻结范围，不把已经支持的研究整体丢弃。
6. **依赖关系：**E2/E3 和最终审计后；M 已经是更早的写作起点。
7. **本关特有约束：**[推断] 封版后若改变模型、目标、指标或数据范围，必须开启新证据版本并指出受影响关口，不能只更新论文文字保留旧的“全部通过”记录。依据：固定目标和同版本证据链 [I L173、181–183](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:173>)。

## 三、特别回答

### 1. 是否保留 smoke 小规模先行？放在哪里？

**[推断] 保留，但 smoke 只验接口、算术、生命周期和资源可承受性。** 本报告建议放在 0.2 正式基础验收前、G1.2 正式梯度采集前、G2.1/G2.2 大规模回放前、G3.1/G3.2/G3.3 正式校准前，以及 E1 长训练前。G1.1 先用短轨迹验收边界事件。G3.2 必须加 C=100、20 端资源样例，避免极小 smoke 掩盖实际负担。这些位置依据 [F L69、82–90、211、246、249](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:246>) 的冻结诊断、小预算及短接口核验安排组织。

**[推断] smoke 不用于证明来源偏差、实际估计优势或尾类收益，不替代两数据集和配对种子；成功不自动升级成主实验。** 不单列成一整套研究关口，是为了保持“工程能运行”和“三关研究命题成立”的状态分离。

### 2. 基础口径验收独立还是并入第一关？

**[推断] 独立为 0.2，成本仍计入共同基础，不能重复累计。** 可行性报告已明确推荐它先于第一关，见 [F L203–208](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:203>)。本报告新增的组织是把它做成可单独退回、重新封版的前置交付；只有这样，计数、BN/参考、测试分母等错误才不会被误裁为 A 的机制失败。

### 3. 三关内部是否需要拆分？

**[推断] 都需要，按可独立失败的机制拆，不按代码行数平均切。** 第一关拆“事件与支持—参考与梯度—偏差裁决”；第二关拆“概率预测—缓存算术—条件重复/历史回放的总裁决”；第三关拆“直接收益诊断—A7 可实现性与成本—A8 收益与范围裁决”。可行性报告把估计增量分为概率预测、缓存/估计、配对回放三个部分，合计约 300–500 行；它是工程估计，不是本轮实测，也不是验收指标，见 [F L88](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:88>)。第三关还包含较大的版本、指标和对照工作，见 [F L104–108](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:104>)，因此不能一个“训练跑通”状态就整关通过。

### 4. 提前可分性探针的位置与两关关系？

**[推断] 放在 G1.2 之后，G1.3 总裁决之前即可开始。** 它复用第一关的合格冻结参考，和来源偏差检验并行；不参与替代第一关的支持/偏差证据，也不替代第二关实际概率估计。它是第三关收益诊断的表征前置，帮助区分“没有可用表征”和“估计或校准链未产生收益”。依据：[F L203、209、213](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:203>)。探针换了参考时，必须重连同一参考的 G1/G2 证据，不能跨快照拼因果链。

### 5. 最小方案与完整方案的分界在哪里？

**[推断] M 之后可开始写收窄版论文；E4 之后可写完整方案。** 不是 G2 误差下降就能写完整方法，也不是一个第三关小实验成功就已经满足论文证据规模。

- **最小研究方案：**三关在冻结骨干范围内形成受支持的机制与收益证据，加 T、4.1、4.2；保留双数据集、主点配对重复、决定性对照和实际资源比较。本报告建议把 100 端及完整训练闭环后移，这是明确的范围收缩，不冒称原拟议全部配置已经完成。冻结降级的原文依据是 [I L235](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:235>)。
- **直接分类器路线：**不是天然足够毕业；必须先经 G3.3 和 M 审查独立贡献。其适用依据为 [F L108、213](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_FEASIBILITY_v1.md:108>)，合成失败必须保留。题目、方法与结论同步收窄。
- **完整方案：**E1–E3 补普通骨干闭环、动态主结果、100 端及压力边界，再到 E4。相对于已经成立的冻结论文，这些属于可选增益；若仍要声称完整三模块训练方案与原拟议扩展，则这些证据是必需项，不能称为可有可无。原拟议规模见 [I L191–196、233](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:191>)。

**[推断] “可开始写论文”指核心主张已能由证据支撑，不是学校学位标准的承诺。** 背景、定义和实验协议可以更早整理，但不能提前写出未获验证的收益结论。

### 6. A 失败后，切 B 的最晚节点是什么？

先保留定位原文。以下逐项照录 [S §五 L140–146、§六 L158](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:140>)：

> ### 备选：B，在 A 的估计—校准链失败且无法合理收窄时转向
>
> [推断] **保留 B。** 明确触发条件是：A 在有效观测支持和可分表征下，仍不能把估计改善转成同预算收益，或 (A7)–(A8) 的匹配/计算成本成为持续瓶颈；此时转向 B 的状态重建与聚合问题。A 的冻结骨干版本若已形成清楚、受支持的贡献，应先收窄 A，不必切换。
>
> [推断] 这是一条课题备选路径，B 不是 A 的数学特例。选择 B 而非 C 的原因是：已有异步/CA2FL 工程基础，且其跟踪问题不依赖从类均值恢复弱模型的未见类表示。它仍需先通过 (B2)–(B4) 的状态语义核验及“有/无相似度”对照。若分组无效，只能缩小 B 的主张并重新评估剩余创新，不能预先保证备选足够支撑论文。
>
> [推断] 若 A 失败源自永久缺席，不能直接宣称 B 会解决它；B 也需要控制缓存年龄。切换时须重新界定可用性与延迟范围。若失败源自通用数据分区或评价错误，则先修正共同实验基础，不把工程错误当作换方向的理由。

其中“条件备选”的原文表述为 [S L158](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:158>)：

> [推断] A 若未通过第五节的识别、实际估计或收益关口，应允许否定或收窄立项；B 是条件备选，不是保底成功；C 暂缓不代表其少样本尾类保留命题已被反证。最差客户端公平也不由尾类收益自动推出，三个方向都没有单端最低精度保证。

**[推断] 本报告建议的最晚“应作出转向裁决”的节点是 G3.3，且必须在 E1 的完整训练闭环投入之前。** 如果 4.2 的重复实验推翻 G3.3，立即回到 G3.3 重裁，不能因为已经接近 M 就继续扩大。它是决策依赖上的最晚节点；现有文件没有提交/答辩日期、可用工时或硬件吞吐，不能据此虚构某个最晚日历日期。

**[推断] 更早失败的处理分别是：**0.2 错误先修基础；G1.3 无偏差或无支持先否定/重界定 A 的场景，不能据此宣称 B 能补救；G2.3 实际概率长期不过关即暂停 A、做合理收窄和备选评估，不必为了等 G3.3 而继续开发 A7。B 真正立项仍需自己的状态语义与相似度对照，不能继承 A 的任何“通过”状态。依据：[S L136–146](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:136>)。

C 的地位也按修订后的裁决保留：不作为 A 的消融、不混合立项；仅当两架构同预算下真实原型明显超过纯锚点且弱模型获益，才重新考虑主线候选，目前不分摊实现预算。此处为文件与节号引用，不是本报告另设触发条件：[S §五 L148–152](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:148>)。

## 交付状态

本轮仅完成检查点结构文档。0.0 已完成；0.1 及后续节点均为待执行计划，未宣称任何算法、实验或理论验收已经通过。完成后停下等待确认，不自行开发、训练或提交。
