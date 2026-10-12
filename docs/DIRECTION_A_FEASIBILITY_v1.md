# 方向 A（FedPCC）工程可行性分析 v1

分析日期：2026-10-12。项目根目录：E:\Federated Machine Learning\FL-Byzantine-Library-astra。

范围：静态读取文档、代码与一份已有非攻击诊断报告；定向读取 CReFF PDF 物理第 3–4 页，并核对第 4 页图像。没有遍历 paper/、master's thesis/、refs/，没有外部检索，没有启动训练或修改算法。本次唯一交付文件是本报告。下文“可得”表示已有数据或接口可复用，不表示关口已通过；“需改造”表示已有部件的口径或调用语义需要适配；“需新增”表示尚需建立相应协议、状态或诊断工具。

[推断] **结论：现有 FLGO 路径在结构上能承载 A，但三个关口都未获现有证据通过。默认理想设备加均匀邀请甚至没有 A 所要校正的可用性来源偏差；必须先建立符合 A 的任务与完成事件，才值得投入完整校准。A 不是在现有聚合器中加一个权重即可完成。** 判断依据见第一节，接口与工作量见第二、三节。

预检记录（以下为本次只读命令的实际输出；存在性以 Test-Path 的结果记录，不用文档中的旧描述替代）：

|预检项|结果|
|---|---|
|git branch --show-current|master|
|git status|On branch master；Your branch is up to date with 'origin/master'；nothing to commit, working tree clean|
|git log --oneline -3：第 1 条|902af7e docs: add non-attack research base and direction selection|
|git log --oneline -3：第 2 条|9d0cfa8 Merge remote-tracking branch 'origin/master'|
|git log --oneline -3：第 3 条|0cc8aa3 update papers|

|必需路径（实际绝对路径）|存在性|类型|
|---|---|---|
|E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\RESEARCH_INNOVATIONS_v1.md|存在|文件|
|E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_SELECTION_v1.md|存在|文件|
|E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\RESEARCH_CONTEXT_NONATTACK.md|存在|文件|
|E:\Federated Machine Learning\FL-Byzantine-Library-astra\refs\R05_Shang2022_CReFF.pdf|存在|文件|
|E:\Federated Machine Learning\FL-Byzantine-Library-astra\paper|存在|目录|
|E:\Federated Machine Learning\FL-Byzantine-Library-astra\master's thesis|存在|目录|
|E:\Federated Machine Learning\FL-Byzantine-Library-astra\refs|存在|目录|

预检全部通过。指定解释器 E:\anaconda3\python.exe 仅用于只读检查模块可定位性及报告引用/格式；没有调用终端默认 Python。没有运行任何训练入口或测试套件。方向 A 的目标、三模块和第五节表格三行已完整对齐，核心入口已定位，没有触发“定义/关口/入口缺失则停止”的条件。

## 一、三个关口在现有代码库下的工程可行性

### 1. 判断所依据的实际路径与配置

**原生路径已定位。** main.py 的 run 经 Mapper.initialize_FL 建立实例，train_epoch 依次调用 FL.train、aggregate、update_global_model；FL.cross_device_step 无放回抽样后直接训练抽中端。其 get_grad 返回 SGD 动量或 Adam 处理量，不是冻结参考下的逐类分类头梯度。FL.aggregate 无条件读取 malicious_clients[0].relocate；零攻击者设置存在静态可见的越界入口。[main.py L13–46](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/main.py:13>)[main.py L58–76](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/main.py:58>)[fl.py L136–171](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/fl.py:136>)[fl.py L244–265](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/fl.py:244>)[client.py L159–173](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/client.py:159>)

[推断] 原生路径可复用模型、数据子集等构件，但不适合作为 A 的最小主路径：若坚持沿用，先处理非攻击入口，再新增完成事件、包字段和校准生命周期，工程面会扩大。上述越界是代码可判断的风险，本次没有运行验证其触发。

**FLGO 路径已定位。** run_flgo_byzantine.py 将本地 easyFL 放入导入路径，调用 flgo.init 再 runner.run；桥接 Server.iterate 为 sample → communicate → aggregate。FLGO 的 BasicServer/BasicClient 提供模型打包、任意字段解包、训练、客户端测试及 checkpoint 接口。[run_flgo_byzantine.py L17–24](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/run_flgo_byzantine.py:17>)[run_flgo_byzantine.py L160–162](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/run_flgo_byzantine.py:160>)[algorithm.py L213–229](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/algorithm.py:213>)[fedbase.py L456–486](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:456>)[fedbase.py L910–1001](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:910>)[fedbase.py L804–842](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:804>)

**当前配置与 A 拟议主点不同。**

|项目|A 的文档配置|现有代码事实|工程判断|
|---|---|---|---|
|数据、模型|CIFAR-10/100-LT、同构 ResNet-8[RESEARCH_INNOVATIONS_v1.md L191–193](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:191>)|已有两种 LT benchmark；默认分别是小 CNN、ResNet18。根目录注册了 ResNet-8[__init__.py L1–5](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_cifar10_lt/__init__.py:1>)[__init__.py L1–5](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_cifar100_lt/__init__.py:1>)[model_registry.py L32–39](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/model_registry.py:32>)|[推断] **可复用 + 需改造**：不能把已有默认模型当作 A 的 ResNet-8；需专用模型适配。|
|长尾与规模|20 端主实验、40% 邀请、主点 α=0.1、IF=100[RESEARCH_INNOVATIONS_v1.md L192–196](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:192>)|D1 LTGenerator 默认 IF=50；先抽 2000 个根样本，再取长尾客户端池；D1 执行器固定 100 端、20% 抽样[common.py L30–78](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_cifar_lt/common.py:30>)[d1_full_experiment.py L103–132](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_full_experiment.py:103>)[d1_full_experiment.py L151–171](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_full_experiment.py:151>)|[推断] **需改造**：复用按标签取索引和长尾缩减思路；A 另建任务，不把可信根样本当作免费信息。|
|完成机制|固定截止时间，速度、固定工作量及独立抖动产生返回[RESEARCH_INNOVATIONS_v1.md L194–195](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:194>)|FLGO 默认四种系统模式均为 IDL；默认 latency=0，BasicServer 容忍时延为 999999[fflow.py L65](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/utils/fflow.py:65>)[default_simulator.py L259–262](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/default_simulator.py:259>)[fedbase.py L284–285](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:284>)|[推断] **需新增**：当前入口配置不制造 A 的标签相关完成偏差；已有截止时间骨架可复用。|
|分区 α|文档只列压力参数[RESEARCH_INNOVATIONS_v1.md L193](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:193>)|FLGO 使用 Dir(alpha × 全局类频率)，然后按标签索引分配；原生 dirichlet_dist 按 i × 当前类样本数切排序数组[partition.py L127–162](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/benchmark/toolkits/partition.py:127>)[partition.py L204–217](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/benchmark/toolkits/partition.py:204>)[data_loader.py L148–155](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/data_loader.py:148>)|[推断] **需改造/声明口径**：不能把同一个 α 数字当作不同划分器的等价设置；原生切片不适用于一般不等类数。|

[推断] 建议以 **FLGO BasicServer/BasicClient 的独立扩展**承载 A，保留普通骨干训练，将校准模型作为独立版本管理。不要直接把桥接 avg 当作包含全部 FedAvg 状态语义的实现：桥接只向量化 parameters 再写回，而 FLGO 模型平均处理 state_dict，包括 BN 缓冲；两者对骨干状态的处理不同。骨干各比较线必须统一聚合权重和 BN 口径。[algorithm.py L115–130](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/algorithm.py:115>)[algorithm.py L223–229](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/algorithm.py:223>)[algorithm.py L282](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/algorithm.py:282>)[fedavg.py L9–11](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/fedavg.py:9>)[fedbase.py L605–622](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:605>)[fmodule.py L336–362](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/utils/fmodule.py:336>)[fmodule.py L638–649](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/utils/fmodule.py:638>)

**工期解释。** [推断] 以下行数是新增/适配逻辑的量级，非代码差分实测；时间按一名熟悉本仓库与 PyTorch 的开发者、全职实现和必要接口核验估计。不含骨干训练、调参、全部论文基线复现或 GPU 等待；共同基础只计一次，不能把各表直接相加。没有吞吐测量，因此不给训练耗时承诺。

### 2. 第一行：A 的识别前提

原文条件：“训练计数可得、目标来源有正支持；有可观测的类内来源偏差；邀请与完成日志能区分。”原文裁决：“若来源偏差基本不存在，应否定该场景下的主创新需求；若永久缺席导致不可识别，不能靠调截断权重补救。”[DIRECTION_SELECTION_v1.md L136](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:136>)

|逐项条件|现有状态|检验前所需工作|量级与时间（推断）|
|---|---|---|---|
|训练计数可得|**可得数据；注册接口需新增。** TaskPipe 保存端索引，运行时再拆 train/val/test；已有脚本按端索引统计尾类持有数[__init__.py L32–62](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/benchmark/toolkits/cv/classification/__init__.py:32>)[run_phase_a_learnability.py L72–95](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/scripts/run_phase_a_learnability.py:72>)|[推断] 在最终训练划分后注册 n_ic、N_c、a_ic；覆盖所有 C 类和端 ID，记录注册成功与载荷。不能直接把拆分前 pool 或根样本统计当 n_ic。|[推断] 60–100 行、0.5–1 日；A 专用数据划分另计。|
|目标来源有正支持|**默认设置的正支持可由配置判断；A 场景需新增机制并验证。** 均匀无放回抽样可得 q=m/N；IDL 时在线、连接和时延是理想值[fedbase.py L545–556](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:545>)[base.py L228–235](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:228>)[default_simulator.py L259–262](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/default_simulator.py:259>)|[推断] 对每个 n_ic>0 的来源检查 q_i>0 且 r_i>0，不仅检查该类至少有一个返回端。自定义速度/抖动/截止时间要给出可审计的概率支持；有限次零返回不能证明 p=0。|[推断] 支持审计 40–80 行、0.5–1 日；完成事件机制与日志合计约 300–450 行、3–5 日。|
|有可观测的类内来源偏差|**需新增；现有默认场景不具备所需非均匀完成概率。** 文档明确必须检查类内梯度—可用性关系，而非只检查尾类比例—速度[DIRECTION_SELECTION_v1.md L23–32](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:23>)|[推断] 冻结同一参考，求全端类梯度探针；检查每类持有端数、来源梯度差及可用性加权目标与全端目标的差；同速度集合做随机/尾端慢/尾端快三种配对。|[推断] 类梯度采集 200–300 行、2–3 日；来源偏差诊断 80–150 行、1–2 日；事件部分与上一项共享。|
|邀请与完成能区分|**瞬时信息部分可得；持续日志需新增。** with_availability 返回过滤后的抽样结果，并保留 _unavailable_selected_clients；dropout、clock 分别留下掉线、超时和 received_clients[base.py L480–496](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:480>)[base.py L515–523](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:515>)[base.py L643–665](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:643>)|[推断] 保留过滤前计划邀请、过滤后派发、掉线、超时、按时有效返回五种事件，明确同一事件的 round/attempt/version。已知 q 对应计划邀请；r 对应计划邀请后的有效完成。不要把过滤后的 selected_clients 当全部邀请。|[推断] 日志适配 100–180 行、1–2 日；包含在上述 300–450 行事件基础中。|

[推断] **默认设置已有一条零改动否定路径。** 当全体设备 IDL、邀请来自固定 m 的均匀无放回抽样时，所有来源 p=m/N 相同；将其代入 (A2)，可用性加权目标恰等于 (A1)。因此该默认场景没有 A 所声称的类内可用性来源偏差。有限轮抽样仍有方差与覆盖不足，不能把它们改称非零来源偏差。这否定的是该场景的主创新需求，不能否定文档拟议的标签相关完成场景。[fflow.py L65](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/utils/fflow.py:65>)[fedbase.py L545–556](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:545>)[RESEARCH_INNOVATIONS_v1.md L58–81](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:58>)[DIRECTION_SELECTION_v1.md L23–32](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:23>)

[推断] **裁决原则可直接采用，操作判据需补充。** “基本不存在”应由预先固定的检查点、逐类偏差范数/相对量、配对场景及重复误差区间判断；单轮小差异或单个随机初始化不能构成否定。若某类只有一个持有端，或类内梯度近似相同，应明确其来源偏差检验的退化情况，不能通过事后筛选数据或人为增加域差异来隐瞒。永久缺席须依据机制支持证明，而非由 200 次未返回断言；若缩到可接入端总体，必须重写 N_c 和目标范围，报告覆盖缺口。权重截断不能恢复缺席端知识。[DIRECTION_SELECTION_v1.md L30–34](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:30>)[RESEARCH_INNOVATIONS_v1.md L89](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:89>)[RESEARCH_INNOVATIONS_v1.md L224–225](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:224>)[RESEARCH_INNOVATIONS_v1.md L210](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:210>)

[推断] 第一行完整检验依赖第三节的数据、模型、事件与梯度基础。**最小冻结诊断约 550–900 行、5–8 日**；正式接入 FLGO 截止时间路径及完整训练/测试划分后约 **800–1300 行、8–12 日**。范围差异在于前者先用固定快照和事件回放回答识别问题，后者验收真实训练生命周期；均不需要先完成合成校准。只有默认理想场景的静态否定可零代码完成。

### 3. 第二行：A 的估计环节

原文条件：“固定参考模型下，真实概率与实际估计概率版本的误差可分解；实际版本相对目标匹配对照具有可重复的误差优势。”原文裁决：“仅真实概率有效时，说明实际概率环节未通过，不能把诊断版本当成果。若有限预算下仍无法识别足够信息，暂停 A。”[DIRECTION_SELECTION_v1.md L137](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:137>)

|逐项条件|现有状态|检验设计与改动|
|---|---|---|
|固定参考及全端目标可计算|**模型和客户端数据可复用；冻结类梯度接口需新增。** 现有客户端 reply 先训练模型再只返回 model；原生 get_grad 是优化器量[fedbase.py L957–1001](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:957>)[client.py L159–173](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/client.py:159>)|[推断] 在普通训练前保留完整参考快照，固定骨干参数、BN 缓冲、分类头、数据变换；只对头求类均值梯度。诊断可遍历全端训练子集取得 G_c，另列成本，不进方法输入。|
|真实概率可与实际估计分开|**需新增。** 默认模拟器暴露的是 availability/drop/latency 状态，没有面向 A 的“计划邀请后按时返回”概率接口[base.py L228–235](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:228>)[base.py L544–570](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:544>)|[推断] 自定义模拟器保留生成机制的真实条件概率作为诊断通道；A1 只从历史邀请/完成估计。r_true 由已声明的在线过程与时长分布计算，或由独立高精度模拟近似并报告误差；一次实际返回率不是本轮真实概率。|
|误差可分解|**需新增估计器及诊断。** A3/A6 已定义旧缓存残差、概率估计与截断影响；文档强调固定数邀请不能直接用独立 Bernoulli 方差式[RESEARCH_INNOVATIONS_v1.md L93–143](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:93>)|[推断] 共同固定 h、g、事件时，比较真实 p、不截断估计 p、截断估计 p；记录缓存残差、概率误差、截断比例、未见端类对、各类均方误差和偏差/方差。固定数邀请保留协方差或直接使用重复模拟的经验误差。|
|实际版本超越目标匹配对照且可重复|**需新增。** 文档要求样本加权无校正 CReFF、无缓存逆概率、仅缓存及真实概率诊断[RESEARCH_INNOVATIONS_v1.md L200–210](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:200>)[DIRECTION_SELECTION_v1.md L118–120](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:118>)|[推断] 相同 n_ic、目标、参考、消息、事件序列和预算，比较返回端类内样本加权均值、仅逆概率、仅缓存、缓存+逆概率；原始按持有端等权均值另列，不能混入目标改变的收益。按至少 3 个配对种子报告逐种子差值，不把客户端当独立种子。|

[推断] 误差诊断可先完全离线，无需运行 FedAvg 或 A3。一个直接可审计的差量是：

[推断] **同一 h、g、I 下，实际估计与真实概率估计之差 = ∑_i a_ic I_i [1/ṗ_i − 1/p_i] (g_ic − h_ic)。**

[推断] 该差量只用于隔离概率/截断环节；完整误差仍需相对 G_c 衡量。固定 h 的条件重复可隔离单轮估计误差；随后做历史缓存逐轮回放检验实际更新顺序，二者不能混为一个实验。若用小批量，要另外测量类内抽样噪声；最小诊断优先用固定全数据梯度。[RESEARCH_INNOVATIONS_v1.md L104–143](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:104>)[RESEARCH_INNOVATIONS_v1.md L210](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:210>)

[推断] 在第一行基础上，**新增约 300–500 行、3–5 日**：概率预测约 80–140 行，缓存/估计约 100–180 行，配对回放和误差分解约 120–180 行。对应最小累计约 **850–1400 行、8–13 日**。独立模拟重复本身的计算时间没有实测，不包括在开发估计内。

[推断] **裁决原则可直接采用，需把“有限预算”“足够信息”操作化。** 预先固定邀请尝试上限、注册与计算/字节预算、检查点、概率平滑和截断搜索范围；观察每端邀请数、每类有效来源与缓存残差，而非无限延长日志直到胜出。真实概率有优势而实际版无优势，判实际环节未通过；真实版也无优势，则进一步检查缓存方差、目标对齐和实现问题，不能只责怪概率估计。正支持但有限预算下误差过大属于实际不可用，不等于已经证明总体不可识别；“暂停 A”可用于项目裁决，但应准确记录原因。[DIRECTION_SELECTION_v1.md L11](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:11>)[DIRECTION_SELECTION_v1.md L32–36](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:32>)[DIRECTION_SELECTION_v1.md L137](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:137>)

### 4. 第三行：A 的校准与收益环节

原文条件：“同版本、同优化预算下，估计优势能传到校准残差与尾类指标；明确头类/客户端代价。”原文裁决：“若 (A7) 是瓶颈，先依据 v1 已有的直接分类器梯度对照及冻结骨干降级范围定位；不得把未成立的合成校准写成成功。若可分表征与这些对照仍无收益，停止扩大 A。”[DIRECTION_SELECTION_v1.md L138](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:138>)

|逐项条件|现有状态|必要改动与验收对象|
|---|---|---|
|同版本|**需改造生命周期。** 现有 iterate 收到模型后立即覆盖 self.model；logger 测当前模型[algorithm.py L213–221](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/algorithm.py:213>)[simple_logger.py L13–25](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/experiment/logger/simple_logger.py:13>)|[推断] 分开 ordinary_model、reference_model(u_t,v_t^0)、calibrated_model(u_t,v̂_t)、next_backbone(u_t+1)。匹配与评估绑定相同 version/hash，包括 BN；旧合成特征进入新版本前重新匹配。|
|同优化预算|**需新增预算控制。** 现有 D1 报告有 elapsed/root_compute 时间字段，但没有 A7/A8 的分阶段预算[d1_full_experiment.py L247–271](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_full_experiment.py:247>)|[推断] 统一特征数、匹配/重训步数、头初始化、批大小、验证调参次数、训练类梯度请求量；再报告实际服务器时间、端计算和字节。A7 的高阶求导成本不同，单纯“步数相同”不足以声称时间同预算。|
|传到校准残差|**需新增 A7/A8。** D1 有可信根数据类梯度和审计，但求的是全部模型参数梯度；没有合成特征匹配/分类头重训链[d1_category_coverage.py L213–261](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/d1_category_coverage.py:213>)[d1_category_coverage.py L421–430](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/d1_category_coverage.py:421>)|[推断] 同时记录匹配残差 ‖g_syn−Ĝ‖² 和相对全端真目标残差 ‖g_syn−G‖²，以及头部均衡训练/验证损失。只匹配到一个错误目标的低残差不能证明来源校正有效。|
|传到尾类指标|**逐类评估可复用；分组与一致性需新增。** D1 _evaluate 按真实标签记录正确数和总数，可用于 C=10/100；报告给出逐类及 macro/tail accuracy[d1_full_experiment.py L174–188](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_full_experiment.py:174>)[d1_full_experiment.py L223–253](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_full_experiment.py:223>)|[推断] 此口径就是逐类 recall；将其汇总为头/中/尾 macro recall，同时保留全类、已覆盖类和各类分母；尾类由最终训练计数预先划定。|
|明确头类/客户端代价|**全局头类统计可扩展；固定客户端测试及低分位汇总需新增/改造。** global_test 可逐端评估，但 Pipe 默认本地 test=None；SimpleLogger 汇总的是本地 val 分布[fedbase.py L624–644](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:624>)[__init__.py L54–62](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/benchmark/toolkits/cv/classification/__init__.py:54>)[simple_logger.py L19–26](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/experiment/logger/simple_logger.py:19>)|[推断] 固定独立客户端测试集，新增端等权、最差 10%、最低端、尾类持有端子群指标及不确定性。现有“尾类富集端”标签可作另一子群，不能冒称所有尾类持有端。[d1_full_algorithm.py L73–87](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_full_algorithm.py:73>)|

[推断] **该关口可实现，当前不可直接检验。** 在前两行基础上，新增模型/特征接口、A7/A8、版本编排、直接梯度对照、指标与预算，约 **700–1100 行、7–12 日**；最小冻结诊断的累计约 **1550–2500 行、15–25 日**。进入普通骨干训练闭环及可靠恢复，仍需第三节的剩余适配。此处包括校准小实验，不包括重新训练合格骨干的机器时间。

[推断] **裁决不是当前已有开关，需先补直接对照和可分性诊断，之后可应用。** 最小对照为冻结 u_t，在 v_t^0 上用类均衡的校正梯度做一次直接头部更新；它与 A3 使用相同客户端消息。若要多步“当前梯度下降”，须在每个新头参考点重新请求类梯度并计费，不能把 v_t^0 的固定梯度反复用作新点真梯度。离线全端梯度/均衡线性探针仅作诊断上界，不能给实际算法免费使用。[RESEARCH_INNOVATIONS_v1.md L58–65](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:58>)[RESEARCH_INNOVATIONS_v1.md L173–177](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:173>)[RESEARCH_INNOVATIONS_v1.md L229–235](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:229>)

[推断] 失败时按断点收窄：估计优势存在且直接头部对照有效、A7/A8 无效，可定位为合成链瓶颈，评估冻结骨干的直接分类器校准是否有足够独立贡献；不能写成合成校准成功。先做“校正器相同、原余弦匹配”对照排查幅值目标问题。若可分表征、实际概率、同预算直接对照均无收益，停止扩大 A。仅某个不可分骨干失败，则只能否定该表征/场景的校准需求或能力，不能升级为 A 的一般反证。[RESEARCH_INNOVATIONS_v1.md L171–177](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:171>)[RESEARCH_INNOVATIONS_v1.md L228–235](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:228>)[DIRECTION_SELECTION_v1.md L138–146](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:138>)

[推断] 原版 CReFF 与受控对照需分开命名：原文第 4 页将重训头与更新后骨干组合；A 要在 u_t 上校准并评估。原版复现可保留原流程，来源偏差实验则用统一版本、初始化与预算的 CReFF 对照，明确它是流程对齐变体；否则收益会混入版本安排。PDF 物理第 3 页式(3)、第 4 页式(4)–(7)；[DIRECTION_SELECTION_v1.md L71–77](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:71>)[RESEARCH_INNOVATIONS_v1.md L173](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:173>)

## 二、方向 A 三个核心模块的接口需求

### 模块 A1：估计可识别的完成概率，先声明信息前提

模块定义要求已知邀请概率 q、历史完成比例估计 r、预测只用本轮之前的信息，并在注册阶段取得训练标签计数。[RESEARCH_INNOVATIONS_v1.md L83–89](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:83>)

|状态/字段（建议接口）|放置层|与现有训练接口的对接|复用分类|
|---|---|---|---|
|client_id、class_ids、n_ic、N_c、a_ic、registration_ok、train_split_hash、registration_bytes|Server 实例持有不可变注册表；客户端提供本地训练计数|[推断] 最终 train_data 确定后单独注册，或用独立 message type；ID 从 FLGO 注册关系取得。现有 datavol 仅是总量[fedbase.py L748–759](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:748>)[fedbase.py L117–132](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:117>)|[推断] 索引/数据对象**可复用**；全类注册和预算**需新增**。|
|attempt_id、round_id、version_id、invite_plan、q_i、dispatch_ids、deadline、finish_ids、drop_ids、overdue_ids、finish_valid、reason|独立事件记录模块；Server 保存本轮不可变事件快照|[推断] 在 availability 过滤前保存邀请，communicate 返回后保存有效完成；不覆盖 A2 已使用的概率预测。现有过滤及截止时间对象可复用[base.py L480–496](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:480>)[base.py L643–665](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:643>)|[推断] 时钟/事件骨架**可复用**；持久日志和语义对齐**需改造/新增**。|
|invited_count、completed_count、smoothing_prior、r_hat_before、p_hat_before、p_min、p_tilde、history_cutoff|独立 ProbabilityEstimator；Server 持有其实例和逐端小状态|[推断] 轮前预测，轮后更新；邀请未完成记失败，未邀请不进入 r 分母；允许按已声明缓变窗口估计，但只用历史。|[推断] **需新增**；不复用“返回频率=完成概率”的简化统计。|
|speed_assignment、work_units、jitter_law、online_law、sim_seed、r_true、p_true、support_reason|自定义 Simulator 与诊断记录；真实概率禁止进入实际 Server 策略|[推断] 通过 flgo.init 的 Simulator 参数接入；为 q 与 r 使用独立可追溯随机流，并支持同事件计划回放[fflow.py L697–707](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/utils/fflow.py:697>)|[推断] Simulator 注入口**可复用**；符合 A 场景的机制**需新增**。|

[推断] A1 量级约 **400–650 行、4–7 日**（注册、完成机制、日志、概率预测；不含新任务构建）。若只做冻结离线关口，可缩到约 200–350 行。模型包可复用；A1 不应放入普通 tensor aggregator 的 __call__，因为聚合器收到更新时，未返回端信息和原邀请计划已可能丢失。[algorithm.py L223–229](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/algorithm.py:223>)[RESEARCH_INNOVATIONS_v1.md L85–89](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:85>)

### 模块 A2：用缓存预测值构造类梯度的校正估计

模块要求未见端类对零初始化、轮前固定旧缓存、先计算 (A3) 再刷新，并记录未覆盖状态。[RESEARCH_INNOVATIONS_v1.md L91–143](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:91>)

|状态/字段（建议接口）|放置层|与客户端的对接|复用分类|
|---|---|---|---|
|reference_version、reference_model_hash、backbone_state、head_state、head_param_names/shapes、C、d、loss/transform_spec|Server 的冻结参考快照；独立 ModelAdapter 提供 encode/head|[推断] pack 发普通模型与参考标识/头；普通骨干和参考骨干一致时可共享一次下行骨干，字节按实际载荷计。普通训练不可改变参考副本。[fedbase.py L456–470](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:456>)[ResNet.py L78–110](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/models/ResNet.py:78>)|[推断] 模型参数和打包**可复用**；encode/head、版本和缓冲冻结**需改造/新增**。|
|class_gradient[c]、class_sample_count[c]、gradient_sampling_spec、reference_hash、feature_norm_stats、gradient_compute_time|客户端 reply 的附加消息；完整 C×d 权重梯度及可选偏置梯度|[推断] 在普通 train 前用参考模型计算；骨干 eval 且无梯度，头仍允许求导；无本地优化器 step、动量、weight decay。缺类端不伪造梯度。softmax 类损失影响头的所有输出行，不能只传目标类别一行。目标依据 (A1)[RESEARCH_INNOVATIONS_v1.md L58–65](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:58>)|[推断] DataLoader/CE **可复用**；类梯度上传**需新增**。现有 reply/pack 仅返回 model[fedbase.py L983–1001](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:983>)。|
|h[(i,c)]、seen[(i,c)]、last_observed_version、last_attempt、age、cache_dtype、weighted_cache_sum[c]|Server 持有独立稀疏 CacheEstimator；缓存建议驻 CPU，按需送设备|[推断] 仅为 n_ic>0 的端类对建条目；保存旧值快照，估计后更新。本轮 g 必须同参考；h 可以旧，但记录年龄和参考版本。|[推断] **需新增**。CA2FL 只有逐端整体模型差缓存，可借生命周期思路，不能直接作为端类梯度缓存[ca2fl.py L8–30](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/resources/algorithm/ca2fl.py:8>)。|
|G_hat[c]、coverage_seen、current_return_count、effective_weight_stats、truncation_ratio、cache_residual_norm|估计器输出给 A3；诊断独立保存|[推断] 用注册 a_ic 和预测 p_tilde 做缓存均值加校正；全端真 G 只送诊断，禁止送实际估计器。|[推断] **需新增**。|

[推断] A2 的客户端与缓存核心约 **350–520 行、3–6 日**（类梯度 200–300、服务器缓存/估计 150–220）；模型适配和误差诊断另外共享计费。现有 D1 的按批加权求导可参考约 20–40 行的结构，但它使用可信根数据且对全部模型参数求导，必须更换数据来源和参数集合，不能把 D1 类梯度当作 A1 目标。[d1_category_coverage.py L213–261](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/d1_category_coverage.py:213>)

[推断] 缓存内存应先按实际持有关系核算：带偏置线性头的单个类梯度有 C(d+1) 个元素；K_pair 个条目的 float32 主载荷为 4 K_pair C(d+1) 字节。现有 ResNet-8 的 d=128；若 C=100 且 20 端均持有全部类，主缓存约 98.4 MiB；100 端约 492 MiB，未计副本、日志与优化器。稀疏持有关系可降低此上界。[model_registry.py L36](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/model_registry.py:36>)[ResNet.py L82–89](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/models/ResNet.py:82>)[DIRECTION_SELECTION_v1.md L104](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:104>)

### 模块 A3：把校正梯度转化为同一表征版本下的均衡分类器

模块要求受半径约束的合成特征均方梯度匹配、近端均衡重训、真实观测支持集合、同版本评估及空集合跳过。[RESEARCH_INNOVATIONS_v1.md L145–177](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:145>)

|状态/字段（建议接口）|放置层/注入位置|复用分类与必要语义|
|---|---|---|
|S_c、synthetic_labels、C_plus、features_per_class、feature_version、R_t、feature_optimizer_state|独立 ServerCalibrator；Server 持有其实例|[推断] **需新增** A7：对合成特征求高阶梯度，固定参考头；梯度目标 detach；投影/约束特征范数，记录匹配残差。|
|reference_head、calibrated_head、mu_t、head_optimizer_state、retrain_steps、head_init_seed、calibration_step_limit|ServerCalibrator 的 A8 阶段|[推断] CE/优化器构件**可复用**，均衡采样、近端参考、头部重训**需新增**；验证集选择 μ，真实未见类不造知识。[__init__.py L290–302](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/benchmark/toolkits/cv/classification/__init__.py:290>)[RESEARCH_INNOVATIONS_v1.md L160–177](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:160>)|
|calibrated_model_version、next_backbone_version、final_calibration_done、checkpoint_calibration_cost|Server.iterate/评估及最终输出编排|[推断] **需改造**调用语义；保存 (u_t,v̂_t) 的评估快照，普通骨干聚合形成下一版本。最终检查点也不能免除重新匹配成本。|
|direct_head_result、cosine_matching_result、linear_probe_result、residual_to_estimate、residual_to_truth、head/mid/tail/client_metrics|独立诊断与评估模块|[推断] 逐类正确/总数**可复用**；对照和残差**需新增**，全端真目标只用于探针。|
|time_matching、time_retraining、time_evaluation、uploaded_gradient_bytes、downloaded_reference_bytes、search_budget|独立预算账本，聚合到 Server 日志|[推断] 原有总时间字段**部分可复用**；A 的分阶段成本**需新增**。|

**CReFF 接口现状。** 本次在 aggregators、flgo_byzantine、easyFL/flgo/algorithm、easyFL/resources/algorithm 的 Python 源码中定向检索 CReFF/creff、gradient matching、synthetic feature、classifier 等词，未定位到 CReFF 的两阶段服务器接口；不据此宣称所有未审计文件均不可能含相关功能。方向裁决文档也仅记录相关算法目录未定位到 CReFF。[DIRECTION_SELECTION_v1.md L94–98](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:94>)

**类似部件的实际复用边界：**

|已有部件|事实与可复用部分|不能直接复用为 A3 的原因|
|---|---|---|
|CIFAR CNN encoder/head|分开的 encoder、线性 head 和 forward[cnn.py L4–24](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/benchmark/cifar10_classification/model/cnn.py:4>)|[推断] 可参考模型拆分；是小 CNN，不能替代指定 ResNet-8。|
|FedRep|客户端先更新头再更新编码器；Server 仅设置 uniform 聚合[fedrep.py L38–65](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/resources/algorithm/fedrep.py:38>)|[推断] 可参考头部优化；没有服务器合成特征匹配与 A7/A8 版本链。|
|D1 根证据/审计|Server 上有按类求导、可靠性与候选审计[d1_category_coverage.py L226–287](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/d1_category_coverage.py:226>)[d1_category_coverage.py L370–430](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/d1_category_coverage.py:370>)|[推断] 可复用求导、计数、记录模式；使用可信原始根数据和全参数更新，与 A 的允许信息及目标不同。|
|通用 FLGO 模型转换|convert_model 可把 nn.Module 包成可用于 flgo.init 的模型[fflow.py L2091–2143](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/utils/fflow.py:2091>)|[推断] 可复用包装入口；encode/head 和参数/BN 版本一致性仍需显式适配。|

[推断] A3 核心校准约 **350–550 行、4–7 日**；模型适配、版本编排、直接对照与基础评估接入后约 **550–900 行、6–10 日**。CReFF 的原文机制可作为实现规格，不能作为本地已有可运行代码。PDF 物理第 3 页式(3)、第 4 页式(4)–(7)已核对：真实类梯度、返回持有端等权均值、同参考头上的合成梯度、逐行余弦距离、随后重训新分类器。

## 三、必需的新基础设施

[推断] 下表为独立职责的工作拆分；“改造”可以在新 subclass/adapter 内改变现有调用语义，并不必然编辑旧文件。表中开发工期不包含训练或未审计论文基线的复现时间。

|基础设施|已有部分与证据|必须补的内容|量级/工期（推断）|
|---|---|---|---|
|A 专用入口与配置清单|flgo.init 支持算法、Model、Logger、Simulator 注入；现有 CLI 无 A 校准/截止时间字段[fflow.py L697–707](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/utils/fflow.py:697>)[run_flgo_byzantine.py L59–99](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/run_flgo_byzantine.py:59>)|[推断] **需新增**独立入口/配置：20/100 端、IF、α 口径、邀请计划、截止时间、种子、校准预算、无攻击设置、版本标识。|[推断] 120–220 行，1–2 日。|
|长尾任务与训练/验证/客户端测试隔离|LT 构造、索引保存、拆分可复用；D1 强制根样本和 IF=50[common.py L30–78](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_cifar_lt/common.py:30>)[__init__.py L32–62](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/benchmark/toolkits/cv/classification/__init__.py:32>)|[推断] **需改造/新增** A TaskGenerator/Pipe：定义客户端总体、IF=10/100、分区口径，冻结各 split 与哈希；训练计数只统计最终 train；验收守恒、互斥、缺类与多来源。|[推断] 250–400 行，2–4 日。|
|ResNet-8 特征/分类头适配|已有 128 维末层与模型转换[ResNet.py L78–110](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/models/ResNet.py:78>)[fflow.py L2091–2143](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/utils/fflow.py:2091>)|[推断] **需新增适配** encode、head、logit/loss 约定与 C=10/100 包装；冻结 BN 缓冲。无需重新编写骨干。|[推断] 80–150 行，1–2 日。|
|计划邀请、完成事件、真实概率诊断|可用性过滤、dropout、时钟截止时间骨架[base.py L466–665](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:466>)|[推断] **需改造/新增**速度边际保持的标签排序场景、独立抖动、固定工作量、真实条件概率、过滤前邀请日志、attempt 预算、全失败事件。|[推断] 300–450 行，3–5 日。|
|冻结参考类梯度上传与注册|客户端数据、CE、任意包字段可复用[fedbase.py L456–486](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:456>)[fedbase.py L957–1001](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:957>)[__init__.py L290–302](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/benchmark/toolkits/cv/classification/__init__.py:290>)|[推断] **需新增**本地 train 计数注册和参考头类梯度；追加形状/版本/计数检查及计算成本。|[推断] 200–300 行，2–3 日。|
|概率预测与端类缓存校正|只有 CA2FL 的整体模型差缓存模式[ca2fl.py L8–30](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/resources/algorithm/ca2fl.py:8>)|[推断] **需新增**轮前平滑预测、截断、零/已见状态、先估计后刷新、CPU 稀疏缓存、年龄统计。|[推断] 200–320 行，2–3 日。|
|来源偏差与估计误差回放|已有哈希及尾类持有数诊断脚本[run_phase_a_learnability.py L72–108](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/scripts/run_phase_a_learnability.py:72>)|[推断] **需新增**固定 G 探针、三种速度配对、真实/估计概率、无校正/IPW/仅缓存对照、均方误差和协方差诊断；隔离真实概率通道。|[推断] 200–350 行，2–4 日。|
|服务器合成匹配、重训与版本编排|D1 服务器类求导仅能参考；无已定位 CReFF 接口[d1_category_coverage.py L226–261](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/d1_category_coverage.py:226>)[DIRECTION_SELECTION_v1.md L94–98](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:94>)|[推断] **需新增**A7/A8、约束、支持集合、直接梯度/余弦对照、评估快照、跨版本重匹配与终点校准。|[推断] 350–550 行，4–7 日。|
|全局及固定客户端评价|通用 D1 _evaluate、global_test 可复用；默认本地 test 为空[d1_full_experiment.py L174–188](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_full_experiment.py:174>)[fedbase.py L624–644](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:624>)[__init__.py L54–62](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/benchmark/toolkits/cv/classification/__init__.py:54>)|[推断] **需改造/新增**全 C 逐类分母、头中尾、已覆盖/全类、最低/最差 10%/尾类持有端测试、配对汇总和缺失值规则。|[推断] 180–300 行，2–3 日。|
|载荷/时间/调参预算账本|现有包尺寸仅用 __sizeof__；D1 有总时间记录[base.py L48–62](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:48>)[d1_full_experiment.py L247–271](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_full_experiment.py:247>)|[推断] **需新增**注册、普通模型、参考头、类梯度、元数据上下行编码长度；计算/模拟/传输时间分列；共用搜索预算。没有实际编码时标“理论载荷估计”。|[推断] 120–200 行，1–2 日。|
|状态 checkpoint 与可重复回放|基础 checkpoint 保存模型/日志/时间/模拟器，模拟器保存变量及状态计数[fedbase.py L804–842](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:804>)[base.py L405–414](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:405>)|[推断] **需新增覆盖**概率统计、h/seen/age、S/优化器、模型版本、attempt、所有 RNG 与事件计划，验证恢复后下一次事件和估计一致。最小离线关口可暂用固定完整轨迹，不要求中途恢复。|[推断] 100–180 行，1–2 日。|

[推断] 上表量级合计约 **2100–3400 行、21–37 个工作日**，可理解为约 4–8 周的基础工程范围；不是性能验证或论文完成时间。这与第四节较小的关口诊断量级不同：完整表包括通用配置、双数据集、训练闭环、成本和恢复，早期否定无需把它们全部完成。

**基线负担单列。** FedAvg 源码直接复用 BasicServer/BasicClient；FedProx、q-FedAvg 文件标注非官方实现，FedProx 初始化会改为 md（部分参与）或 full 抽样。[fedavg.py L1–2](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedavg.py:1>)[fedprox.py L1–18](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/resources/algorithm/fedprox.py:1>)[qfedavg.py L1–31](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/resources/algorithm/qfedavg.py:1>)

[推断] 基线需要统一邀请/完成/模型/评价接口，不能让 FedProx 初始化改变配对实验的邀请机制。CReFF 原版与目标匹配变体需新建；这些变体共享类梯度与校准基础，不应按多套独立系统重复估计。[RESEARCH_INNOVATIONS_v1.md L200–202](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:200>)[DIRECTION_SELECTION_v1.md L94](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:94>)

[推断] 本次未定位到可直接用的 Fed-LTNF；其完整复现的改动量**我不确定**。若要求完成文档的全部论文基线，需要定向读取基座 T6 指定的“面向非独立同分布数据的联邦学习方法研究_李卫超.pdf”方法相关物理第 39、56–64 页及其本地实现入口，才能另估工程量。它不是前三关口最小否定路径的前置条件，不能因此把决定性目标匹配对照删掉。[RESEARCH_CONTEXT_NONATTACK.md L89–96](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_CONTEXT_NONATTACK.md:89>)[DIRECTION_SELECTION_v1.md L118](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:118>)

### 不修改现有算法文件与必须改变现有行为的分界

[推断] **不修改任何现有算法文件也能实现的部分：**读取现有配置作静态支持否定；在独立诊断脚本中统计最终训练计数、载入合格冻结快照、做全端探针和事件回放；通过新 TaskPipe、ModelAdapter、Server/Client 子类、Simulator、Logger 实现 A。FLGO 已暴露这些注入口和消息接口，因此从结构上没有证据要求必须改其核心源码。这里仍然需要编写新代码，本轮没有实施。[fflow.py L697–707](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/utils/fflow.py:697>)[fedbase.py L456–486](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:456>)[fedbase.py L970–1001](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:970>)

[推断] **必须改变的现有训练行为：**模型仅上传 → 追加类梯度与版本；过滤后的参与列表 → 保留计划邀请与完成；收到模型立即替换 → 同版本校准/评估再推进骨干；只测全局/本地 val → 固定客户端 test；模型 checkpoint → 全状态 checkpoint。这些变化无法仅靠 CLI 参数或旧 aggregator.__call__ 完成，但可以在新模块中覆盖，保持旧算法文件不动。[algorithm.py L213–229](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/algorithm.py:213>)[simple_logger.py L13–26](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/experiment/logger/simple_logger.py:13>)[fedbase.py L804–842](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:804>)

[推断] **若限定沿用旧入口/工具不允许扩展，则必须编辑旧代码：**原生 FL.aggregate 的零攻击者索引、原生不等类数分区切片；D1 入口固定根数据/IF/100 端；现有 collect_class_stats 写死 10 类。推荐扩展路径可以绕开这些文件，不能用“未编辑旧文件”掩盖已经改变了协议/评估语义。[fl.py L264–265](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/fl.py:264>)[data_loader.py L148–155](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/data_loader.py:148>)[d1_full_experiment.py L103–132](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_full_experiment.py:103>)[__init__.py L321–350](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/benchmark/toolkits/cv/classification/__init__.py:321>)

## 四、三个关口的执行顺序与依赖关系

[推断] **建议顺序：基础口径验收 → 第一行 → 第二行 → 第三行；在第一行建立冻结快照后，提前做第三行所需的轻量可分性诊断。** 这是本报告的工程建议，三行原文并未规定强制顺序或跳转规则。推荐依赖来自 A1→A2→A3 的目标链以及同版本要求。[DIRECTION_SELECTION_v1.md L134–138](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:134>)[RESEARCH_INNOVATIONS_v1.md L179–183](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:179>)

|阶段|最少改动与输入|为何先做|失败后的最小路径|
|---|---|---|---|
|基础口径验收|[推断] 独立 A 任务/模型适配、冻结 split/count/version；可复用原数据和 ResNet-8。约 250–450 行、2–4 日，包含在第一行累计量内。|[推断] 计数、参考或评价错，后续收益/失败均无法归因。[RESEARCH_INNOVATIONS_v1.md L58–70](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:58>)[RESEARCH_INNOVATIONS_v1.md L682–688](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:682>)|[推断] 修共同基础，停止本轮机制评价；不据工程错误换方向。[DIRECTION_SELECTION_v1.md L146](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:146>)|
|第一行|[推断] 默认 IDL+uniform 的静态否定零代码；检验拟议场景需计数、固定类梯度、支持与事件回放。最小累计约 550–900 行、5–8 日。|[推断] 先确认实际有待校正偏差，且目标来源可识别，避免先开发 A7。|[推断] 机制已证明 p=0 且 n_ic>0：立即否定原总体目标；均匀 p 的默认场景：立即否定该场景需求。对拟议三种速度场景，若多检查点/配对重复均无稳定来源偏差，停止该场景的主创新投入；只保留覆盖/方差观察。[DIRECTION_SELECTION_v1.md L30–32](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:30>)|
|提前的可分性探针|[推断] 在第一行模型/训练划分上新增冻结特征线性探针与独立验证，约 80–150 行、1–2 日；包含在第三行对照工作中。|[推断] 可提前发现表征瓶颈，但不跳过第二行。现有历史报告曾记录另一小 CNN 设置尾类门槛未通过，这不能证明 A 的 ResNet-8 不可分。[report.md L5–7](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d1_3b/phase_a_diag_20261002/report.md:5>)[report.md L25](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d1_3b/phase_a_diag_20261002/report.md:25>)|[推断] 探针无信息时先检查数据/参考与训练是否合格；收窄该表征场景。不可用它替代 A 的估计检验。[RESEARCH_INNOVATIONS_v1.md L228–235](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:228>)|
|第二行|[推断] 第一行冻结数组与事件轨迹上新增实际概率、缓存和目标匹配对照；增量 300–500 行、3–5 日。|[推断] 能在 A7 不存在时否定实际估计优势，成本远低于完整训练。|[推断] 真实版有效、实际版无效：有限预定预算内排查日志/估计后仍失败则暂停 A；真实版也失败：核查目标与缓存方差后收窄/暂停估计主张。保留实际版失败结果，不把真实版换成最终成果。[DIRECTION_SELECTION_v1.md L34–36](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:34>)[DIRECTION_SELECTION_v1.md L137](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:137>)|
|第三行|[推断] 加同版本 A7/A8、直接头部对照、固定测试与预算；增量 700–1100 行、7–12 日。已有合格冻结表征时，可先做约 150–250 行、2–3 日的直接头部收益诊断，但它不能验收完整 A3。|[推断] 前两关支持“估计更好”，仍需逐段确认最终效用。|[推断] 直接对照有效、合成无效：停止扩大合成链，评估冻结/直接版本。可分表征下两者仍无同预算收益：停止扩大 A；不能继续无止境加骨干修复模块。[DIRECTION_SELECTION_v1.md L138–146](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:138>)|

[推断] **是否允许跳关：**可以提前做便宜的可分性、直接头部和合成目标可实现性诊断，用于提早定位风险；这些诊断不等于取得下一关口的“通过”。第一行失败时不应把第三行的类均衡收益归因于参与校正；第二行仅真实概率成功时不应推进实际版本的成功主张。若冻结/直接版本形成受支持的独立贡献，可按文档允许范围收窄 A，不自动转到 B。[RESEARCH_INNOVATIONS_v1.md L235](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:235>)[DIRECTION_SELECTION_v1.md L137–144](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:137>)

[推断] **快速否定的实际限度：**当前就能否定默认理想设备场景的来源偏差需求，也能指出 p=0 的不可识别边界；但不能在零新增工具、零实验下否定拟议标签相关场景的实际估计或尾类收益。后两项需要合格快照、配对事件和评价数据。已有其他任务的 final_model.pt 不能仅凭文件存在就认证为 A 的冻结参考，须核对模型、训练划分、IF/α、版本与验证可分性。历史小 CNN 诊断的 IR=5/α=1.0/100 端配置与 A 主点不同。[report.md L5–7](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d1_3b/phase_a_diag_20261002/report.md:5>)[model_registry.py L36](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/model_registry.py:36>)[RESEARCH_INNOVATIONS_v1.md L191–196](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:191>)

[推断] 一次预算失败只裁决已声明的场景、协议与范围；决定暂停或收窄后，不自动开始新方向、不自行训练或修改算法。本报告完成后等待用户确认。

## 五、风险与未知

### 1. 代码可判断的结论

|结论|证据与含义|
|---|---|
|两个核心入口都已定位，FLGO 有可注入的同步/截止时间骨架|[main.py L13–46](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/main.py:13>)[run_flgo_byzantine.py L160–162](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/run_flgo_byzantine.py:160>)[fflow.py L697–707](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/utils/fflow.py:697>)[base.py L643–665](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:643>)。[推断] 不存在“必须重写整个联邦框架”的静态证据。|
|当前客户端返回对象不满足 (A1)|[client.py L159–173](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/client.py:159>)[fedbase.py L983–1001](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:983>)。[推断] 动量、训练后模型差都不能替代同一冻结参考的类梯度。|
|有 LT 数据构造、逐类评估与训练计数审计的部分基础|[common.py L42–78](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_cifar_lt/common.py:42>)[d1_full_experiment.py L174–188](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_full_experiment.py:174>)[run_phase_a_learnability.py L72–95](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/scripts/run_phase_a_learnability.py:72>)。[推断] 不应把这些已有工具全部估为从零实现。|
|已有 D1/CA2FL/FedRep 部件不构成完整 A 模块|[d1_category_coverage.py L249–261](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/aggregators/d1_category_coverage.py:249>)[ca2fl.py L8–30](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/resources/algorithm/ca2fl.py:8>)[fedrep.py L38–65](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/resources/algorithm/fedrep.py:38>)。[推断] 只能复用构件或模式，不是零适配基线。|
|默认 local_test 不能满足 A 的客户端测试要求|[__init__.py L54–62](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/benchmark/toolkits/cv/classification/__init__.py:54>)[simple_logger.py L19–26](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/experiment/logger/simple_logger.py:19>)。[推断] 本地 val 平均不能替代固定独立 test 的最低/低分位精度。|
|零返回不推进当前轮号|BasicServer.run 仅在 updated 为 True/None 时增加 current_round；桥接没有模型则返回 False[fedbase.py L304–323](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:304>)[algorithm.py L213–221](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/algorithm.py:213>)。[推断] 按更新轮数设“200 轮”可能掩盖更多邀请尝试，甚至无法形成有界失败预算；需独立 attempt_id，并保证空完成轮仍更新完成日志。|
|模拟时间不是实际设备计算时间|实际 communicate 先执行客户端计算，随后 delayed_communicate_with 产生到达时间，clock 再丢弃超时包[fedbase.py L384–391](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:384>)[base.py L544–570](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:544>)[base.py L643–659](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:643>)。[推断] 这条路径会计算一些最终丢弃的结果；成本必须分列，不能声称真实截止时间部署已停止慢端计算。|
|概率与多种 RNG 的保存不完整|模拟器 random_module 初始化为 RandomState(0)，checkpoint 仅保存 variables/client_states/state_counter；Server 保存模型等基础状态[base.py L215–219](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:215>)[base.py L405–414](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:405>)[fedbase.py L804–842](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:804>)。[推断] 改训练 seed 不自动等于所有事件流有不同种子；A 需要显式配对及恢复状态。|
|静态时延模式不是 A 的独立抖动过程|LN/UNI responsiveness 在初始化生成每端 latency，update 的动态机制未在这些函数中建立[default_simulator.py L264–275](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/default_simulator.py:264>)[default_simulator.py L329–335](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/default_simulator.py:329>)。[推断] 固定时延加固定截止时间会把一些来源变成永久超时，不能直接冒称“低但正”的完成概率。|
|可选逐类统计写死为 10 类，字节函数是对象尺寸|[__init__.py L321–350](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/benchmark/toolkits/cv/classification/__init__.py:321>)[base.py L48–62](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:48>)。[推断] CIFAR-100 必须用通用逐类评估或改造；现有尺寸不能作为真实通信字节。|
|BN/参考头/训练变换必须进入版本契约|ResNet 含 BN，forward 末端是 log_softmax；FLGO 模型平均按 state_dict 处理，而桥接仅 parameters[ResNet.py L79–110](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/models/ResNet.py:79>)[fmodule.py L638–649](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/utils/fmodule.py:638>)[algorithm.py L115–130](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/algorithm.py:115>)。[推断] 冻结 requires_grad 不能独自冻结 BN；头部 logits 与损失链也需保持一致。|

### 2. 需要额外验证的事项与最小确认路径

|未知|明确的不确定性|需要读的文件或最小实验（仅建议，本轮未执行）|
|---|---|---|
|α=0.1、IF=100 是否有足够多的尾类来源|[推断] **我不确定。** 分区代码给出算法，不能给出未构建 A 任务的端类持有表。单一尾类持有端不足以展示类内来源差异。|读取最终 A task 的 info/data.json、训练标签映射/拆分清单；只做样本守恒、每类持有数、权重集中度和尾端占比审计。可参考现有 SCRIPT L72–95 的审计结构。|
|所选冻结骨干是否可分、是否有类内可用性相关差异|[推断] **我不确定。** 历史报告是另一配置的整体/逐类精度；不能据此判断表征可分性，也不能证明有来源偏差。[report.md L5–25](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d1_3b/phase_a_diag_20261002/report.md:5>)|读取候选 checkpoint 的生成配置和任务哈希；同版本全端训练梯度探针加冻结线性验证；至少检查预先选定的多个参考点。|
|低概率下实际估计能否优于目标匹配对照|[推断] **我不确定。** 文档 (A4) 不保证均方误差优势。[DIRECTION_SELECTION_v1.md L34–36](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:34>)|第一/第二关口的固定数组与事件回放；公布每端邀请/完成数、r 预测误差、截断、缓存残差、逐类均方误差和配对差值。|
|截止时间是否包括新增类梯度计算与注册|[推断] **我不确定实际配置将采用何种工作量口径。** 文档要求固定工作量且登记成本；现有模拟器没有 A 消息的专用工作量。[RESEARCH_INNOVATIONS_v1.md L85–89](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:85>)[RESEARCH_INNOVATIONS_v1.md L195](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:195>)[base.py L544–570](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/simulator/base.py:544>)|A 配置清单须明确普通训练、类梯度扫描、特征范数统计的 work_units；验收所有校准对照采用相同消息获取成本。不能额外计算梯度却沿用不含这部分的完成概率。|
|A7 目标是否可实现、幅值匹配是否稳定|[推断] **我不确定。** 方向裁决已经给出截断前大幅校正目标可能超出受约束合成梯度范围的反例。[DIRECTION_SELECTION_v1.md L34](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:34>)|同版本小预算 A7：先匹配真 G 的正对照，再匹配真实/估计概率的 Ĝ；画相对真目标与估计目标残差；比较同校正器余弦匹配和直接头部更新。|
|当前硬件是否足以完成完整实验|[推断] **我不确定。** 本次没量时或量显存；缓存上界只说明主载荷，A7 求导图和双模型可增加峰值。[DIRECTION_SELECTION_v1.md L104](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:104>)|在后续授权阶段做一次 C=100、20 端的单轮梯度/匹配/重训资源测量，然后按实际 K_pair 估 100 端扩展；不从 CUDA 可用推导总预算足够。|
|训练/验证/客户端测试如何公平固定|[推断] **我不确定将采用现有 local_test 切分还是自定义官方测试分配。** 两者需显式选定，不能混报。现有 D1 train_holdout=0 没有本地 val/test。[d1_full_experiment.py L155–161](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/d1_full_experiment.py:155>)[__init__.py L54–62](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/benchmark/toolkits/cv/classification/__init__.py:54>)|读取最终 A split 清单，验收训练/验证/测试互斥、每端测试样本量、全类别测试覆盖、尾类及尾类持有端定义；在种子间固定评价规则。|
|概率支持能否证明而非由返回频次猜测|[推断] **我不确定尚未实现的速度/在线机制。** 有限零返回与真正零概率不同。[DIRECTION_SELECTION_v1.md L32](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:32>)|读取 A Simulator 与对应配置；计算声明分布下按时完成的支持，必要时独立模拟估概率并给误差界；生产估计器禁止读取这些真值。|
|版本与恢复是否正确|[推断] **我不确定新扩展接入后的实际行为。** 基础框架允许注入，但类装饰器和状态恢复需要验收。[fflow.py L885–894](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/utils/fflow.py:885>)[fedbase.py L804–842](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/algorithm/fedbase.py:804>)|只做很短的接口核验：过滤前后 ID 对齐、空返回日志、迟到包不入本轮、缓存先估计后刷新、恢复后下一事件/概率/估计一致。未核验前不宣称基线稳定。|

[推断] **框架内无法实现的环节：**目前没有发现 A1/A2/A3 的软件接口在 FLGO 中不可表达；它们需要新增模块和覆盖生命周期。真正不能实现的是在允许信息不变时恢复永久缺席来源的当前知识，或保证任何 Ĝ 都可由有限半径合成特征精确匹配。这是文档明确的信息/可实现性边界，增加截断调参或框架代码无法消除。[DIRECTION_SELECTION_v1.md L32–36](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:32>)[RESEARCH_INNOVATIONS_v1.md L224–229](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_INNOVATIONS_v1.md:224>)

[推断] **未获经验结论：**本报告只能支持“结构可承载、哪些基础可复用、最小验证与否定的工程路径”。来源偏差大小、实际概率优势、A7 收敛、尾类收益、头类/客户端代价、总资源足够与否，均留待上述最小验证；不能把静态可实现写成已经有效。[DIRECTION_SELECTION_v1.md L156–160](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_SELECTION_v1.md:156>)

PDF 来源：[R05_Shang2022_CReFF.pdf](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/refs/R05_Shang2022_CReFF.pdf>)，本次仅使用物理第 3–4 页，具体公式见第二节。基座相关内容只按本地卡片引用，没有把卡片里的文献成绩当本次实测。长尾/尾类保留背景与参与边界见[RESEARCH_CONTEXT_NONATTACK.md L89–96](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_CONTEXT_NONATTACK.md:89>)[RESEARCH_CONTEXT_NONATTACK.md L159–167](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_CONTEXT_NONATTACK.md:159>)[RESEARCH_CONTEXT_NONATTACK.md L262–268](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/RESEARCH_CONTEXT_NONATTACK.md:262>)。

