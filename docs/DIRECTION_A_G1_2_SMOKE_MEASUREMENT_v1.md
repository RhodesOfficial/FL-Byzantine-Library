# G1.2 第一段 smoke 与 W02 测量交付 v1

日期：2026-10-13（Asia/Shanghai）。`parent_checkpoint=G1.2`，工作项为“候选参考 smoke 与测量（第一段）”。**smoke 在本次候选数值口径内通过；G1.2 状态为“证据不足/预算耗尽”（正式验收证据不足，本次新额度未耗尽，原64 MiB触顶历史保留）。四点不判“合格参考”、不判“不合格”。** 本轮不冻结 ε_num/W02，不进入第二段，不 commit/push。

依据 K §一的现有“smoke 通过另记，不能替代正式通过”，及用户将 G1.2 分两段的直接授权。不是新增节点或新增研究判据。此次用户另授权提高自设工程额度，并明确回复“允许仅补算 C100 r80 缺失诊断”。具体授权和原文件22项哈希见 `resume_config.json`；原计划见 `preregistration.md`，修订计划见 `resume_preregistration.md`。合同及 K 未改。

## 1. 现场、接收身份与未判定资格

项目根 `E:\Federated Machine Learning\FL-Byzantine-Library-astra`；分支 feature/direction-a，基准 HEAD abcfded（完整 SHA 在 resume_config.json）。本任务起始工作区干净，随后仅产生本轮实现和证据。最近五个 commit：abcfded、92b4948、54eb6e0、e3c3528、6ea9bd1。最初要求的四文档、候选目录及两个0.2任务目录全部存在，指定文档和相关合同/K段落已读取。

运行均显式使用 E:\anaconda3\python.exe -B，PyTorch2.5.1 + CUDA、float32；CPU threads=2、确定性算法、TF32关闭、cuDNN benchmark关闭。环境分别见 environment.json/resume_environment.json。本轮没有训练或优化器更新。

证据包根为 `E:\Federated Machine Learning\FL-Byzantine-Library-astra\artifacts\direction_a\phaseG1_2_smoke_v1\`，以下包内路径从这里定位。旧候选根为 `...\artifacts\direction_a\backbone_preparation_v1\`；0.2任务根为 `...\artifacts\direction_a\phase0_2_v1\tasks\`。所有短路径须与上述实际绝对根合用。

候选接收身份核对满足候选裁决§三输入条件：14份候选包文件与原hash/Git字节相同，八份0.2任务文件与封存来源相同，旧五项生成实现指纹匹配。四个参考与生成run、r40/r80位置、task、验证记录一一对应；实际装载保留完整骨干、head、9组BN参数/缓冲，eval且全部参数冻结。验证只引用旧记录，没有重跑验证或用测试数据。`reception_identity_check.json`记录输入路径/哈希和无缺失项；恢复时再次核对。正式资格和第二段完整测量仍未签定。

任务身份为 FedPCC-0.2-candidate-CIFAR10-N20-v1、FedPCC-0.2-candidate-CIFAR100-N20-v1；N=20，C=10/100，d=128，head为linear.weight[C,128]及linear.bias[C]，bias=True。IF名义均100，实测分别100/112.5；α采用已裁决每类对称Dirichlet([0.1]×20)、最大余数、并列按端ID、不重抽。数据seed20261012与旧训练seed2026101321/2026101322分列；split/count/变换/分组均未重选或重算。

## 2. 新额度、触顶历史与累计成本

原上限64 MiB，旧已记账45306965 byte，下一次写入拟累计78479043 byte，在落盘前拦截。原 run_record.json 原样保留，其SHA为 `23e746068ce594b3a09aeeb82e7b11457272343a13c9a2584cc9cd6726ae28b0`。累计额度修订不清零计数；追加的恢复账本把旧耗用、旧限额和触顶字段一并引用。

保守估算：原45306965 + 缺失C100包33172078 + 25 MiB后处理余量 + 128 KiB续跑应急槽 =104824515 byte。新累计上限256 MiB=268435456 byte，是该估算的2倍以上。每份C100包约33.17 MB；旧78.48 MB是累计拟写入，不是单包大小。任一新额度触顶仍立即停止、不自行扩额。

|对象|新累计上限|原耗用|本次追加|累计实耗|
|---|---:|---:|---:|---:|
|实际程序经过时间（秒）|600|6.016|4.828|10.844|
|前向|3000|466|59|525|
|求导 / 梯度请求|2000 / 1000|414 / 414|40 / 40|454 / 454|
|编码样本位置|12000|5968|2205|8173|
|统计扫描|2000，原1000修订|937|394|1331|
|累计证据记账（byte）|268435456|45306965|34123091|79430056|
|逻辑上下行载荷（byte）|67108864|24949440|0|24949440|
|训练attempt / 优化器 / 搜索|0|0|0|0|

证据记账包含覆盖写入和两个128 KiB应急预留，并不等于目录体积；目录实际32文件共79011715 byte。最终只读归档/输入/实现哈希审阅另测0.5149918秒，与程序计时分列，合计11.3589918秒，仍远低于600秒；不再触发任何模型计算。本文等工作区文档正文另列，不混为梯度载荷。

输入、各参考和恢复/保存阶段限额均90秒，原自检60秒；原程序startup3.219秒，原input1.063秒，原四点阶段0.485/0.187/0.578/0.469秒。续跑startup3.094秒、追加输入审计0.657秒、续跑数据读取/检查阶段0.296秒、缺失诊断恢复阶段0.641秒、汇总/保存0.140秒。阶段时间与累计时间对象见两个账本。

CUDA allocator allocated峰上限6 GiB、Windows进程working-set峰上限6 GiB、已知CPU原始数组/张量代理上限2 GiB。封存的原前三点GPU分配峰最大136179712 byte、保留的进程峰最大1371525120 byte；续跑分别136179200/1007386624 byte。后者属于新进程，不把两进程峰相加。续跑CPU已知代理334712680 byte；allocated/reserved、进程working-set和代理分别登记，不冒称完整整机资源。原第四点末端资源和逐端时间未落盘，其丢失限制保留。

本次成本归现有 G1.1/G1.2/G1.3 行中 G1.2 smoke/W02分项；旧骨干生成和G1.1事件成本不清零、不升级，也不重复计入本次。单机无真实网络、注册、模拟设备截止或带宽墙钟，这些注明不适用而不是实测零。

## 3. 四点与梯度 smoke 结果

|reference_id|比较条数|max normalized L∞|原完整记录/恢复|
|---|---:|---:|---|
|A-backbone-CIFAR10-s2026101321-r0040-v1|44|9.2779124161e-8|复用旧完整记录|
|A-backbone-CIFAR10-s2026101321-r0080-v1|44|8.9406967163e-8|复用旧完整记录|
|A-backbone-CIFAR100-s2026101322-r0040-v1|208|2.6788080965e-7|复用旧完整记录|
|A-backbone-CIFAR100-s2026101322-r0080-v1|208|2.2415218363e-7|复用旧完整主梯度，补算缺失诊断|

四点共504条比較；完整新视图是 smoke_measurements_complete.json，旧 smoke_measurements.json保持原三点/缺失第四点历史视图，不覆盖它。每点诊断张量位置为diagnostics/<reference_id>.pt，内含逐端原始特征/标签/索引、独立解析梯度、辅助样本对照及子集目标。四个文件真实存在，没有把其他点的特征冒充第四点。

- 完整输出与bias：实际两种C均保留C×128和C维偏置，不只保留真实类一行。独立零logits手算C=3,d=2夹具同时覆盖含bias/无bias；无bias夹具不冒称四点实际配置。
- 类均值/逐样本平均：每端存在类最小/最大ID各最多前8样本，比较batch mean、逐样本平均、CPU float32、NumPy float64稳定softmax解析式；不把辅助8样本当全类均值。
- 类目标汇总：手写两源n=[1,3]夹具独立验证全源G_c算术。真实数据仅验证Σ_selected n_ic/N_c g_ic与选定来源逐样本解析和/N_c；17端未测，明确不是正式全端G_c。
- 状态不变：前三点原测量前后/重复读回SHA精确相同；第四点恢复阶段同样严格保持参数/全部BN缓冲与重复读回一致，模型无参数grad或更新。第四点旧消息state身份与对应真实checkpoint一致。
- 缺类：消息按封存n_ic=0列missing IDs，无该类梯度请求或伪零梯度。部分目标对没有选定来源的类为数学上的已知零贡献，不把它当某端的类梯度。
- 采样/噪声：W02主梯度采用所选端完整训练类样本；端内没有抽样噪声。全总体仍只覆盖3/20端。辅助smoke使用预定至多8样本，范围单列。

独立参照不是同代码输出自证：NumPy float64对冻结float32特征/头值计算e=p-onehot(y)，∂W=mean(e⊗z)，∂b=mean(e)；原独立手算完整C/bias、n=[1,3]及非零logits标量有限差分全部通过。有限差分h=1e-5，最大绝对误差8.8261897790e-12。没有重跑已封存的独立夹具。

## 4. ε_num 梯度对象候选依据（不冻结）

候选为 **2e-6**，保存于 epsilon_candidate.json。主测量float32 CUDA完整CE头梯度；独立float64解析式在同版本eval float32特征与头值上计算；另报告CPU/CUDA及逐样本对照。第四点是对已存主梯度与经授权恢复的特征参照比较，消失的旧feature cache/hash无法核对，不宣称与旧cache逐字节相等。

规范为weight+bias联合展平后的L∞差，scale=max(1,L∞(reference))，normalized L∞=absolute L∞/scale；另报告Frobenius/L2及每块误差，不为它另设容差。

实测最大normalized L∞=2.678808096483167e-7，来自C100 r40/client_000/class_0 CUDA-vs-CPU。其absolute L∞=4.76837158203125e-7、reference L∞/scale=1.7800347805023193、Frobenius/L2差1.6870604292120139e-6；weight块差4.76837158203125e-7，bias块差1.1920928955078125e-7。

预登记选择式max(8×float32 machine epsilon,4×最大normalized差)，再向上取1位十进制有效数字。machine epsilon=1.1920928955078125e-7；8倍=9.5367431640625e-7；4倍实测=1.0715232385932668e-6，故候选向上为2e-6。旧0.2 logits的1e-6没有被借用。运行前排错界1e-4没有触及，且状态/维度/缺类恒等检查独立于容差。

适用依据仅限本次四点、平台、eval特征、CE完整头和分块累加协议；不覆盖encoder梯度、训练态、其他平台/精度、估计器、状态恢复资格或正式验收。是否采纳/冻结由后续审查决定。

## 5. W02 实测与载荷

频率为每参考每选定端一次完整train扫描；原12次，第四点恢复另3次。C10每点选端0/9/19样本233/128/418，合计779；C100为710/650/845，合计2205。四点原5968编码位置，恢复追加2205，累计8173；不是8173个不同训练样本。encode/head chunk=128；sum-gradient按完整类样本量归一，CPU float64累加、主消息float32；损失纯CE无正则。

|每个参考的端序号0/9/19|C10|C100|
|---|---|---|
|存在类 / 缺类数|4/6、4/6、8/2|30/70、28/72、32/68|
|完整梯度记录数|16|90|
|纯梯度tensor字节|20640、20640、41280|1548000、1444800、1651200|
|实际本地消息编码字节|23680、23680、46054|1564578、1460270、1668886|

四点212条完整主类梯度在12消息中，实际消息编码9574296 byte，纯tensor9453120 byte；元数据/容器开销另计121176 byte。参考文件理论下行按每端每点完整文件估计15375144 byte，与消息合计24949440 byte。没有真实上传/下行；续跑复用消息，没有再发载荷。

每端特征L2范数的样本分母、min/max/mean/rms/median/p95及线性分位数规则都在W02_measurement.json和各点客户端记录中。作为便于审阅的mean值，端顺序0/9/19如下：

|点|各端mean L2 feature norm|
|---|---|
|C10 r40|2.821524 / 2.727448 / 2.930899|
|C10 r80|2.842884 / 2.763068 / 3.433806|
|C100 r40|11.835145 / 10.790726 / 10.852979|
|C100 r80（恢复）|11.598118 / 10.069033 / 10.109658|

这些统计没有进入A3半径/合成规则。前三点编码/完整类头求导总时间分别0.168814/0.072105、0.022583/0.025755、0.071187/0.120557秒，解析对照/辅助smoke/保存另列。原第四点逐端计时已丢失，保留原reference_3阶段0.469秒与明确null原因；不以恢复计时替代它。恢复编码0.197288秒、范数统计0.002336秒、独立参照/辅助smoke0.125665秒、部分目标0.036894秒，旧消息读取0.013841秒，另有序列化等阶段开销。这些是本次工程测量，不冻结下一阶段频率/预算或完成机制。

## 6. 保存核对、限制与下一段缺失项

全部22个旧归档文件，包括原三点诊断、12消息、旧触顶账本、旧smoke视图/来源，运行前后及最终独立读核SHA完全一致。没有重跑前三点或90条旧第四点完整类梯度。原实现指纹和上游任务/候选/合同均未变；续跑入口有独立版本指纹。

实际32文件，哈希索引覆盖30文件（包括旧触顶账本），排除自身及最终续跑账本避免自引用。两者单独定位：artifact_hashes.json SHA-256=`1394a1bcbb98f299a3c850f7c000f6b72484f8b9f2cad15edf2924674d42aeab`；resume_run_record.json SHA-256=`047e7b22a06b86bc6e98c31ecbe1d3eb706d490dd3ab00bbe75c19d081a92d60`。第四点诊断SHA=`ef91d985099fc849a4d5394c03d3e6987bfbf9fde9bd161e9a4d9e85251031df`；ε候选文件SHA=`d70c225952238ee97fa4ee3a1d984f2250f62d8422fa7d3d42dc6bef9c8daeb5`。所有索引文件均复核通过，工作区差异格式检查通过。

第一段计划的四点diagnostic和候选/W02汇总已齐；历史第四点逐端计时、输入细账丢失的限制仍明确记录，未补造。四点旧普通头验证tail recall均0，不能据此新增资格阈值或代判P。正式G1.1状态不升级；未执行P/G1.3/A1/A2/A3/A7/A8、正式全20端梯度/目标诊断或FedAvg训练，不修改easyFL。

第二段尚缺：梯度ε_num采纳/冻结记录、正式W02协议冻结、后续明确授权、K G1.2完整正式测量与全端目标诊断。仅完成第一段不能解除这些关闭项。

## 7. 文件清单与Git状态

本次工作区40个预期改动文件：32份归档、4份实现/入口/测试、3份文档及.gitattributes。全部在项目绝对根下定位，无outputs/.idea/临时脚本/__pycache__非预期文件，未暂存、未commit、未push，HEAD仍abcfded。

|实际目录（项目根下）|文件|
|---|---|
|direction_a|class_gradient_smoke.py|
|scripts|measure_direction_a_class_gradient_smoke.py、resume_direction_a_gradient_smoke.py|
|tests|test_direction_a_class_gradient_smoke.py|
|docs|DIRECTION_A_G1_2_SMOKE_RUN_RECORD_v1.md、DIRECTION_A_G1_2_SMOKE_RESUME_RUN_RECORD_v1.md、DIRECTION_A_G1_2_SMOKE_MEASUREMENT_v1.md|
|项目根|.gitattributes（仅新增本轮证据字节保存规则）|
|artifacts/direction_a/phaseG1_2_smoke_v1|environment.json、independent_oracles.json、measurement_config.json、preregistration.md、reception_identity_check.json、run_record.json、smoke_measurements.json、resume_config.json、resume_environment.json、resume_preregistration.md、resume_run_record.json、smoke_measurements_complete.json、epsilon_candidate.json、W02_measurement.json、decision.json、artifact_hashes.json|
|同包diagnostics|四个<reference_id>.pt（参考ID见§3）|
|同包messages/<reference_id>|每个参考各client_000.pt、client_009.pt、client_019.pt，共12文件|

完成后停止，等待确认，不自行进入第二段或提交。
