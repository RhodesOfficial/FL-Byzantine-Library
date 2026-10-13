# 方向 A 合格骨干候选包裁决记录 v1

日期：2026-10-13（Asia/Shanghai）。裁决对象：`FedPCC-backbone-preparation-v1`，归属 G1.2 输入准备工作项。

**这是本裁决记录的建议组织方式。** 文件名采用 `DIRECTION_A_BACKBONE_CANDIDATE_ADJUDICATION_v1.md`，用于区分既有的动作归属裁决 `DIRECTION_A_BACKBONE_PREPARATION_ADJUDICATION_v1.md` 与本次真实候选包裁决；不新增检查点编号，不覆盖前一份记录。

**[推断] 裁决：本次交付达到“候选包完整、来源可核对”，可以进入 G1.2 候选接收与既定验收流程。它尚不是“G1.2 通过”，也不是“P 通过”。四个候选全部保留；尾类 recall 全为 0 作为限制随包传递，不新增事后精度门槛，不据此立即要求重训。** 判据来源为 [B §3.1–3.3、§四][B-interface]；逐项证据见本记录第二至五节。正式梯度测量仍须先满足其适用的数值容差、工作量及有限额度登记要求，见第三节。

## 一、现场预检与核验范围

### 1.1 现场预检

以下为本轮开始时的实际结果；各 Git 命令均在项目根 `E:\Federated Machine Learning\FL-Byzantine-Library-astra` 执行，仓库目录及 `.git` 存在。本轮只读脚本显式使用 `E:\anaconda3\python.exe`。

|项目|实际路径或执行位置|结果|
|---|---|---|
|`git branch --show-current`|上述项目根|通过：`feature/direction-a`|
|`git status`|上述项目根|通过：工作区干净；领先 `origin/feature/direction-a` 1 个提交|
|`git log --oneline -5`|上述项目根|通过；最近五个提交逐条列在下表|
|交接说明|[HANDOFF 实际路径][H]|存在，全文已读|
|运行记录|[RUN_RECORD 实际路径][D]|存在，全文已读|
|骨干准备归属裁决|[BACKBONE_PREPARATION_ADJUDICATION 实际路径][B]|存在，指定节已读|
|G1.1 裁决|[G1_1_ADJUDICATION 实际路径][G11]|存在，相关状态与接口已核对|
|研究合同|[PROTOCOL_FREEZE 实际路径][C]|存在；R01–R07、W01/W07、§6、§7.2 已读|
|检查点结构|[CHECKPOINTS 实际路径][K]|存在；G1.2、P 及相关共用规则已读|

|提交|预检得到的提交说明|
|---|---|
|`92b4948`|`phaseG1.2-prep: qualified backbone preparation`|
|`54eb6e0`|`docs: G1.1 adjudication and protocol sync`|
|`e3c3528`|`docs: record direction A adjudications and sync backbone preparation`|
|`6ea9bd1`|`phaseG1.1: invitation and completion event support`|
|`e3ca623`|`phase0.2: baseline protocol and model acceptance`|

本轮核验基准 HEAD：`92b4948f2fed33cc4636f9df9e4ee457fb9c8168`。候选生成记录的基准为 `54eb6e02f4630df82cfdeb1c352fd5e4520ea5be`，见 [manifest L2][manifest]；两者分别是生成时输入基准与本轮已提交证据基准，不混用。

### 1.2 输入版本与核验办法

本轮开始时读取的原始文件字节 SHA-256 如下。路径见上表同名链接；此表是本轮只读核验记录。

|输入|SHA-256|
|---|---|
|HANDOFF|`f93bd4e3f461896e6a7b456d063086f049e0c7bcef1e659d0157360b71f08053`|
|RUN_RECORD|`48c5c4ee34301ac9be2be14295667148a521309145e618fc797a3a2b97618229`|
|B：骨干准备归属裁决|`c863529137063c5cd9e39485b0445844cd3a837aa07512bf1c76f877d86ffd28`|
|G1.1 裁决|`cd65b23b8ed3e18e37186048a694031df92c2495af0432a30c7ff5ac21b951a4`|
|C：本轮同步前合同|`63aa379b5ed68b0bb1f05e9215fcff0ced638c24486522e2d7a4386902a87898`|
|K：检查点结构|`8fe09ca87e9cdb5dd053a22e8ee3ba02a37d64f72dcc96e8987c338b8c09e98a`|

实际证据目录为 [backbone_preparation_v1][package]，共 14 个文件：8 个根目录文件（包括预登记）、2 个任务运行记录、4 份快照。精确清单为 `manifest.json`、`task_binding.json`、`generation_config.json`、`run_record.json`、`validation_record.json`、`handoff.md`、`preregistration.md`、`artifact_hashes.json`、`runs/CIFAR10_run_record.json`、`runs/CIFAR100_run_record.json` 及第二节列出的四份 `.pt`。本轮全部读取，没有以交接说明代替这些证据。

本轮只读核验包括：实际文件与哈希表及 Git 封存字节比较；任务绑定与原 0.2 八个任务文件交叉核对；解析两个完整训练账本和全部六条验证记录；CPU 读取四份快照的 `state_dict/metadata`，核对键、形状、dtype、有限值及状态哈希。验证指标只核对已封存混淆矩阵的算术与分母，**没有模型前向、重新验证、训练、抽样、重划分或重算训练计数**。没有调用候选恢复函数重建模型或重跑执行者测试。

## 二、事项 1：候选包完整性与来源裁决

### 2.1 对 B §3.2 八个逻辑文件逐项核验

以下“满足”只针对 B §3.2 的准备交付要求；是本轮核验结论，不替代 K §G1.2 正式测量。

|逻辑文件|实际文件与独立核验结果|定位与裁决|
|---|---|---|
|`manifest.json`|父节点 G1.2、工作项、准备身份、输入文档版本及哈希齐全；四个 reference 均能定位到快照、run、进度、task、验证记录；开始/交付时间存在，缺失项为空。输入版本与本轮同步前对应文档一致。|满足。[manifest L2–92、93–173][manifest]；B L101。|
|`task_binding.json`|两份 0.2 完整候选任务的 `info/data/counts/acceptance` 共八个文件路径和 SHA-256 均与现存原文件、0.2 封存哈希一致；标签映射、N/C、split、IF/α、固定分组/尾类持有端表及数据/训练种子均可定位。分组和分配元数据与封存来源一致，没有重新计数。|满足。[task_binding L2–128、129–439][binding]；B L102。|
|四份真实快照|逐份 CPU 读取成功，均含 `state_dict` 和 `metadata`；56 个状态键，含完整骨干、线性头及 9 组 BN 的参数/缓冲，浮点状态均为有限值。头形状为 C×128 与 C 维 bias，C=10/100；浮点 float32、BN 计数 int64。文件哈希、按名称/dtype/形状/张量字节计算的状态哈希、任务/config/run/reference/进度元数据相互一致；四份状态均不同于各自初始状态。|满足；见 §2.2。二进制来源为四份快照的 `state_dict/metadata`，对应 [manifest L93–165][refs]、[generation_config L93–119][config]；状态哈希定义见 [backbone_preparation.py L28–35][statehash]。没有据此签定梯度或完整续训恢复合格。B L103、110。|
|`generation_config`|新训练身份、初始化、模型/损失、训练及验证变换、训练态 BN 与冻结读出、普通 FedAvg 聚合、实际参与规则、训练种子、本地工作量/优化器/学习率、实现指纹和四点预选规则齐全。五个实现指纹与实际文件一致；执行路径与所记保存/验证和选点规则相符。|满足。[generation_config L2–228][config]；[脚本 L202–247、259–341][runner]；B L104、119。|
|`run_record`|预登记副本与文档运行记录前 37 行字节一致；两个完整 run 各有 80 个更新轮、640 条端更新、3200 SGD steps；每轮 8 端邀请及返回，进度、权重、学习率及保存位置与配置对应。实际 attempts/steps、时间、字节、资源口径、无重跑/无触顶和缺失项均可核对。共享运行未按两个参考点重复收费，详见 §2.3。|满足。[预登记 L7–37][pre]、[总账本 L2–76][ledger]、[C10/C100 run L2–13、8995–12879、文件末尾][run10] [run100]；B L105。|
|`validation_record`|六条记录均读取：四个候选加两个初始基线；候选 reference、快照/状态哈希与 manifest/快照一致，固定 validation 的 task/data 哈希与 0.2 对应。指标、单位、完整分母、分组、缺失项、模式/变换、训练完成位置、选用理由均齐全；四点门槛字段均为 null，并给出未设最低精度门槛的依据性说明。全部六个混淆矩阵支持所报 accuracy/recall；CE 为既有运行记录值，本轮未重新计算模型损失。|满足。[validation_record 六条 records][val]，候选定位分别为 L219–452、453–686、11343–22016、22017–32690；B L106。指标限制见第五节。|
|`handoff.md`|封存交接说明列明完整性、全部四点、未认证范围及接收者尚须完成的梯度/状态/采样核验；文档版另保留初始基线、低普通头表现与四点 tail=0。相关声明已与快照、账本、验证记录核对。|满足。[handoff L3–13][handoff]、[HANDOFF §6–7 L126–151][H-validation]；B L107。|
|`artifact_hashes.json` 或索引内哈希表|表内 12 个实际文件的原始字节 SHA-256 全部匹配。它明确排除自身和最终总账本，不是假称全包自包含校验；本轮另将全部 14 文件逐一与 HEAD 中同路径 Git blob 比较，全部字节相同。状态哈希与文件哈希独立登记，绑定范围涵盖配置、run、验证和快照。|满足；排除项补充核验见下文。[artifact_hashes L2–20][hashes]、[manifest L16–17、93–165、170–171][manifest]；B L108。|

两项哈希表排除文件的本轮原始字节 SHA-256：总账本 `run_record.json` 为 `b379dd3256eba1fbf0737348b2bab8cfbce7261de1ad3c03d3012b88c75e6370`；`artifact_hashes.json` 为 `bd288852158ccc45610bf8f0e70e2afd9cbbd2bb59c8ed92910b5ded88990b8c`。两者均与上述完整 HEAD 的 Git 内容一致；这补足其独立版本定位，不修改原证据表或让文件自含自身哈希。

任务绑定保留原 0.2 口径：N=20、C=10/100；名义 IF 均为 100，实测 IF 分别 100、112.5；α=0.1 的每类独立对称抽样、无类频率缩放、最大余数整数分配及不重抽规则继续沿用；数据 seed=20261012 与两份训练 seed 分开登记。[task_binding L2–128、129–439][binding]、[预登记 L7–8][pre]。本轮核验其身份一致性，不重新裁决已有数据定义。

### 2.2 四个候选与状态分级

|reference_id（点击读取对应快照）|更新轮 / SGD steps|文件 SHA-256 前 16 位|状态 SHA-256 前 16 位|对应索引|
|---|---|---|---|---|
|[A-backbone-CIFAR10-s2026101321-r0040-v1][pt10-40]|40 / 1600|`4824d4a52a3aa46d`|`48466c475471fe8a`|manifest L94–111|
|[A-backbone-CIFAR10-s2026101321-r0080-v1][pt10-80]|80 / 3200|`d8e137b9feeda74b`|`c2a11303f977029a`|manifest L112–129|
|[A-backbone-CIFAR100-s2026101322-r0040-v1][pt100-40]|40 / 1600|`e778839c23485719`|`3b4e3a4b03982c4b`|manifest L130–147|
|[A-backbone-CIFAR100-s2026101322-r0080-v1][pt100-80]|80 / 3200|`7b6faf5b0a4be006`|`5a84b86e6d66a21e`|manifest L148–165|

完整哈希均见 [manifest L93–165][refs]；表内短值只用于阅读定位。每个 r40/r80 是同一任务同一次训练的不同位置，不是独立研究重复，见 [manifest L18–47][manifest] 与 [预登记 L8、35][pre]。

**[推断] 采纳 B §3.1 第一种交付状态：候选包完整、来源可核对。** 第二种“G1.2 通过”尚缺该节点测量证据；第三种“P 通过”尚缺其探针证据与预定判据。没有为准备工作新造节点状态，也没有把 manifest 的候选完整标记升级成正式关口“通过”。依据：[B L85–93、126][B-interface]、[K G1.2 第 3–4 项、P 第 2–4 项][K-G12]。

### 2.3 有限额度与实际消耗核对

以下是已执行准备工作的工程登记及实耗，不是本轮新裁定的预算，也不延伸为类梯度测量或正式研究实验额度。

|对象|预登记额度|已封存实耗/完成情况|证据|
|---|---|---|---|
|attempt、有效更新|每任务 attempt 触顶点 90，累计 180；计划每任务 80 更新|每任务 80 attempts、80 更新；累计 160；无缺失参考|预登记 L23；总账本 L3、12–17、22、31、45、54–74；两个 run L2–4 及末尾|
|SGD / backward|每任务 3600、累计 7200|每任务 3200、累计 6400；640 条端更新/任务|预登记 L24；总账本 L4、8、23、29、32；两个 run L13–8974|
|前向 / 遍历|7500 / 1024|6448 / 18|预登记 L25；总账本 L6、10、26、42|
|总时间与分项|总 1200 s；各任务训练 480 s；输入、验证、保存分别 90 s|总 84.172 s；C10/C100 训练 41.437/35.405 s；输入 0.891 s、验证 0.392 s、保存 0.156 s；另有 startup 5.891 s|预登记 L26；总账本 L18、34–43、46–52|
|证据写入 / 逻辑复制|268435456 byte / 4294967296 byte|12304020 byte / 3233966080 byte；网络/注册在此单机准备不适用，未把逻辑复制说成实测网络流量|预登记 L27–28；总账本 L5、7、25、28；两个 run 的 `network_reason` 及上下行字段|
|内存对象|CUDA allocator 分配 6 GiB；CPU 常驻张量代理 2 GiB|CUDA 分配峰值 C10 320941056、C100 304121344 byte；CPU 张量代理分别 303483520、286145152 byte。另报 Windows 进程峰值工作集，未拿它冒充张量代理|预登记 L29；两个 run L7、8982–8993|
|搜索、重复、修订|每任务 1 个配置、搜索 0、研究配对重复 0；最多 1 次实现修正重跑|两个规定 run；实际 retries=0；`hit=null`；四点全部完成|预登记 L30–31；generation_config L92、129–173；总账本 L9、20、45、66–76|

表中路径统一定位：[预登记][pre]、[总账本][ledger]、[C10 run][run10]、[C100 run][run100]、[生成配置][config]。证据写入量是账本口径，不等于最终目录体积；内存测量对象也不等于整机峰值。

**[推断] 封存账本及逐轮记录未显示触顶、未完成计划或漏交参考，不触发 B §四的“预算耗尽尚未交齐”分支。** 这些成本仅关闭准备工作对应账目；梯度诊断尚未执行，G1.1 的正式事件资格不随之升级。依据：[B L105、135][B-failure]、[manifest L3–14][manifest]、[G1.1 裁决 §二、§四][G11]。

## 三、事项 2：进入 G1.2 的裁决与接收方责任

**[推断] 允许进入 G1.2 候选接收，并在该节点原定流程内先做梯度 smoke、再完成正式验收；本轮不允许把候选完整性替代其结果。** 未发现 B §四所列的缺包、任务哈希不匹配、状态不完整、参考点不齐或已登记训练计划未完成，因此无需先拒收、补训或回 0.2。[B L130–136][B-failure]。未设适用最低普通头精度线，不能据低精度事后套用“未满足已登记精度要求”分支；低结果保留为待诊断限制。

|G1.2 接收方必须完成的原判据|本次已提供的输入 / 尚需完成的内容|依据|
|---|---|---|
|正式参考匹配模型、split、IF/α、训练记录和变换；多个预选参考|四点包及身份核验已交。接收方按原计划固定并登记正式参考清单，保留每个预选点的对应关系；不得改成挑收益最佳点。实际装载后的模型/头/BN/变换匹配仍由接收方签定。|K L136、138、141；B L88、119|
|完整分类头与 bias 声明|候选明确含 bias、C×128 权重及 C 维偏置；仍须验证实际梯度包含声明的完整头和输出维度。|K L138；generation_config L93–119|
|单端类均值与逐样本平均一致|类梯度数组及比较结果尚未交；按该对象预登记的范数和数值容差做梯度 smoke。|K L138；合同 §6 L189|
|`G_c` 与按 `a_ic` 汇总一致|可复用原训练计数来源；全端目标诊断及一致性测量尚未交。|K L137–138；B L110|
|重复读取后参数/缓冲哈希不变|本轮验证了封存张量身份；实际测量路径的重复读取、梯度获取前后不变性仍须核验。|K L138；B L103、118|
|缺类不产生伪梯度；完整数据或小批量噪声口径明确|本包未做类梯度扫描，不能继承“已测量”；接收方需明确选择并给出缺类/噪声核验。|K L138；合同 W02|
|测量及诊断成本可追溯|已有准备分项实耗；梯度 smoke/正式测量的工作量、时间、字节、搜索/修订额度须另行运行前登记，不消耗或重置成“剩余训练额度”。|K L84–85、137；合同 §7.2–7.3；manifest L3–14|

表中判据直接定位 [K §G1.2][K-G12]；补充定位 [合同 §6][C-threshold]、[§7.2–7.3][C-budget]、[B §3.3][B-interface]。**[推断] 准入结论是输入可接收，不是对尚未登记的正式梯度工作负载自动放行。** 梯度 `ε_num` 仍须按对象确定，不能借用 0.2 的 float32 eval logits `1e-6`；本轮四份状态的精确哈希相等也不是梯度数值误差证据。

**[推断] 无需调整接口、检查点顺序或依赖。** G1.2 与 G1.1 仍可并行；G1.2 通过后才具备 P 的合格参考输入，不必等待 G1.3；G1.3 仍等待 G1.1 和 G1.2。当前理想全返回训练没有认证 G1.1 的实际 W01/W02 与完成机制绑定。[K 总览 L61–64、G1.2 L140、P L146–150][K]、[B §2.2][B]、[预登记 L37][pre]。

## 四、事项 3：选点、门槛与不利结果披露

|核查问题|对原始证据的核验|裁决|
|---|---|---|
|是否按后续方法收益或普通头指标挑点|预登记明确两任务各取 r40/r80、全部交付；generation_config 的四个 ID、manifest、总账本 planned/delivered、两个 run 的 snapshots、四份实际文件完全对应。脚本在规定轮数保存，全部 `selected=true`，无按指标排序/筛选分支。|**[推断] 在封存范围内未发现收益挑点或只交最优点。** 不把两个任务种子或同 run 两点当作配对重复。证据：[预登记 L8、14][pre]、[config L129–141][config]、[脚本 L202–247][runner]、[总账本 L12–17、54–74][ledger]。|
|是否事后增加或偷换精度门槛|四点验证均为 `qualification_threshold=null`，理由与 B §3.3 的“没有独立最低精度线”一致；没有移用 `τ_probe`，没有把已有 logits 容差用于训练后梯度资格。|**[推断] 未发现事后加线；null 在这里是有依据的“不设本动作最低普通头精度门槛”，不是省略 K 的正式测量判据。** 证据：[B L118–120][B-interface]、[validation 候选各记录][val]、[预登记 L15–16][pre]。|
|是否省略不利结果|四点逐类分母/召回/混淆矩阵和两个初始化基线均在 validation_record。C10 r40 精度 10.0% 低于初始 11.5%；C100 middle 从 r40 的 0.033333 降到 r80 的 0；四点 tail 均为 0，全部未删除。四点 mean CE 也均高于各自初始值，见第五节。|**[推断] 未发现此包省略上述不利结果。** 证据来自六条 validation 记录，非仅报告措辞；[HANDOFF L132–139][H-validation]与其一致。|
|是否把普通头或初始化冒充合格参考|两个初始化记录标为 `initialization_baseline_not_candidate`、`selected=false`，不在 manifest 四点清单中；四点状态与初始化不同；快照标明 `candidate_pending_G1.2_acceptance`、非完整续训包。|**[推断] 本轮未发现这种混淆。** 证据：[validation L3–218、687–11342][val]、[manifest L93–165][refs]、四份快照 `metadata`；未因此扩大到 E1 恢复验收。|

预登记、配置与实际执行保存路径一致；本轮结论以封存材料为范围，不声称能排除未提交、未记录的外部运行。后续不得将本轮“未发现不当”改写为训练充分、表征合格或方法收益成立。

## 五、两条协调者观察的处理

### 5.1 观察 1：四点 tail recall=0，middle 亦出现 0

**纳入本次裁决，作为候选的实测限制。** 本轮从封存混淆矩阵、逐类分母及分组字段核对数值；表中 recall 为 [0,1] 分数，CE 单位为 nat/验证样本，显示值作小数舍入。

|候选|样本精度|全类 macro recall|head / middle / tail macro recall|mean CE|原始记录定位|
|---|---|---|---|---|---|
|C10 r40|10.0%|0.100000|0.333333 / 0 / 0|3.290022|[validation L223–452][v10-40]|
|C10 r80|12.1%|0.121000|0.403333 / 0 / 0|3.090419|[validation L457–686][v10-80]|
|C100 r40|6.0%|0.060000|0.148485 / 0.033333 / 0|4.982351|[validation L11347–22016][v100-40]|
|C100 r80|7.8%|0.078000|0.236364 / 0 / 0|4.881525|[validation L22021–32690][v100-80]|

每点验证样本为 1000；C10 每类 100、head/middle/tail 类分母为 3/3/4；C100 每类 10、类分母为 33/33/34；缺失类别列表均为空。因此这里的 0 是有验证分母的 0，不是缺类后填充的 0。[validation 各记录的 `class_sample_denominators/group_macro_recall/missing_classes`][val]。初始基线 C10 精度 11.5%、CE 2.302681；C100 精度 0.9%、CE 4.606917，同样保存在原文件 L3–218、687–11342。本轮不把 CE 与召回互相替代为资格门槛。

**[推断] 对 G1.2：不因上述 0 阻止候选接收或已登记额度下的梯度验收。** G1.2 仍可检验这些固定对象上的梯度算术、版本及状态；但应明确测量来自普通头效果偏低的参考，不能称其已经满足 P 或代表充分训练的骨干。没有既定最低普通头精度线，本轮不据观测结果补设一条。[B L93、118–120、133][B-interface]、[K L137–141][K-G12]。

**[推断] 对 P：不新增“tail recall 必须先大于 0”的前置条件，也不宣告其可分性失败或有充分改善空间。** 当前仍缺 G1.2 合格参考结论，故不能直接跨入 P 正式裁决；G1.2 通过后，由 P 在冻结特征上按原规则比较参考头、均衡线性探针和无信息对照。低普通头结果既可能留下改善空间，也可能反映表征问题；现有记录不能区分。仍须预定 `τ_probe`、独立验证和完整尾类分母。[K P L146–151][K-P]、[合同 §6 L191][C-threshold]。

**[推断] 登记为后续诊断限制，而非本轮新增设计门槛。** P 若失败，按既有规则排查数据、参考与训练资格，必要时回 G1.2 提供新参考；不得自动推翻旧参考上的梯度结论，也不得将新旧参考拼接成一条收益证据链。[B §四 L134][B-failure]、[K P L149–151][K-P]。

### 5.2 观察 2：用户关于延长训练后尾类恢复的经验

**纳入考虑，但按“协调者转述的用户经验”登记，不列为本项目已核验实验事实。** 来源是本轮用户消息“观察 2”，不是仓库文件；原话为：

> 在同类长尾任务上，训练轮数增加后，尾类 recall 就不再为 0。

本次可核对的事实是：每任务固定 80 更新轮，r40/r80 两点 tail 都为 0；每次受邀仅 5 个 SGD steps、batch=64 且端内有放回抽样，不能把“80 更新轮”解释为每端完整遍历训练集 80 次。学习率在 41–80 轮也与前 40 轮不同。[generation_config L144–173][config]、[预登记 L11–14][pre]、第五节验证表。

**[推断] 这条经验与“训练进度可能影响尾类表现”相关，值得在诊断训练资格、是否延长训练或修订协议时考虑；它不足以证明本次 80 轮不合格，也不足以保证继续训练就能改善尾类或使 P 通过。** 同类任务不等于相同 split、模型、工作量、学习率、BN/变换和验证口径；当前材料没有该经验对应的运行记录、任务/配置身份、候选及验证结果可供配对核对。若未来要据此提出可迁移的实证判断，应补这些具体来源文件；本轮不猜它们的路径或参数。

**[推断] 本轮不要求重训，不更换四点，不另选训练轮数。** 这不影响事项 1 的完整性与事项 2 的接收结论。已有计划完成而无本动作精度门槛；不能为追求非零尾类召回临时延长已封存预算。若后续证据支持新参考或协议修订，应先登记理由、有限额度、选点与判据，保留此次所有结果及成本，再按参考变更回 G1.2/P；若需要新增资格门槛，先做设计裁决，不能看新结果后补线。[B L119–120、133–136][B-interface]、[K 共用规则 L88、P L149–151][K-rules]、[预登记 L30–31][pre]。这是一项有条件的后续处置，不是现在启动新训练的授权。

## 六、合同同步裁决与实际修改范围

**[推断] 需要同步候选已交付及准备成本已登记的事实，避免后续仍将它们理解成“完全未交付”。** 本轮输出明确包含“按裁决结果对合同的更新”，据此只在合同两处追加状态和引用，不改变研究定义或冻结新的研究参数：

|位置|本轮同步|保持的边界|
|---|---|---|
|§2.2 R07|补充引用本记录第二、三节：四个候选及来源资料已交付、可接收；最终参考资格和梯度验收仍由 G1.2 签定。|不把候选写成合格参考，不改训练范围、参考变更回退或 P 门槛。|
|§7.2 G1.1/G1.2/G1.3 行|登记 G1.2 本次准备分项额度/实耗已封存，引用本记录 §2.3；区分尚待登记/验收的 G1.2 梯度测量及 G1.3。|保持 G1.1 正式“证据不足/预算耗尽”（证据不足）及原有成本对象；本次准备额度不转为新运行或正式机制诊断额度。|

W01 的本次实际普通训练参数、W07 的本次四点计划已在 [generation_config L129–173][config]、[预登记 L7–16][pre] 和本记录中按 [合同 §7.3 L246][C-supplement] 定位；**[推断] 不将“每任务 80 轮”等本次工程选择冻结为所有后续正式事件、普通训练或终点校准的统一研究值。** W01/W07 行、§6、其他合同字段与 K 均保持不动。

本轮合同修改前的 SHA-256 见 §1.2，与候选生成 manifest 的输入版本一致。**[推断] 修改后的合同是本次裁决的后继版本；封存包继续引用生成时的合同哈希，不回写旧 manifest/config 或快照元数据去冒充它们曾使用新合同。** 依据：[合同 §7.3][C-supplement]、[manifest L55–80][manifest]。

## 七、本轮未裁决及后续事项

|事项|当前状态与下一步|所属既有节点 / 依据|
|---|---|---|
|正式参考资格、类梯度 smoke 与正式测量|输入包可接收；逐项完成第三节原有判据，报告全部预选参考的核验与成本。|G1.2；K L136–141|
|梯度适用数值容差、W02 采样/工作量与测量额度|尚无本轮新测量；运行前登记该次有限额度，正式验收前完成适用判据冻结。|G1.2 及合同 §6、§7.2–7.3；不能借用 0.2 logits 容差|
|冻结特征可分性、尾类信息与改善空间|普通头结果不能代判；先 G1.2，再按预定 `τ_probe` 和完整对照做 P。|P；K L146–151|
|是否增加训练、修订训练协议或新增资格门槛|本轮不决定新轮数/优化器/门槛；保留用户经验线索及四点低结果。只有提出后续变更时，补对应证据和预算/判据并走既有回退。|B §3.3、§四；K L88、149–151|
|G1.1 实际 W01/W02 与完成机制资格绑定|本次理想全返回训练不替代该绑定；原正式状态不变。|G1.1；[G1.1 裁决][G11]及预登记 L37|
|G1.3、后续收益和完整训练生命周期|本轮无来源偏差/估计优势/校准收益/完整续训恢复结论；按原依赖进入。|K 总览；B L110；manifest 的 `not_certified`|

本轮产物为本裁决记录和合同两行事实同步。没有改动候选证据、算法代码、检查点结构；没有启动训练、重新验证、重新划分数据或计数；没有 commit、push。完成后等待确认。

## 引用定位

下列均为实际绝对路径；正文的文件行号以本轮读取版本为准。二进制快照以文件路径、SHA-256 和内部 `state_dict/metadata` 字段定位；Git 预检与本轮只读核验结果由本记录自身封存，不冒称执行报告原文。

[H]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_BACKBONE_PREPARATION_HANDOFF_v1.md>
[H-validation]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_BACKBONE_PREPARATION_HANDOFF_v1.md:126>
[D]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_BACKBONE_PREPARATION_RUN_RECORD_v1.md>
[B]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_BACKBONE_PREPARATION_ADJUDICATION_v1.md>
[B-interface]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_BACKBONE_PREPARATION_ADJUDICATION_v1.md:83>
[B-failure]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_BACKBONE_PREPARATION_ADJUDICATION_v1.md:124>
[G11]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_G1_1_ADJUDICATION_v1.md>
[K]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_CHECKPOINTS_v1.md>
[K-rules]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_CHECKPOINTS_v1.md:80>
[K-G12]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_CHECKPOINTS_v1.md:133>
[K-P]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_CHECKPOINTS_v1.md:143>
[C]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md>
[C-threshold]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md:179>
[C-budget]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md:223>
[C-supplement]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md:244>
[package]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1>
[manifest]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/manifest.json:1>
[refs]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/manifest.json:93>
[binding]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/task_binding.json:1>
[config]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/generation_config.json:1>
[pre]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/preregistration.md:1>
[ledger]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/run_record.json:1>
[run10]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/runs/CIFAR10_run_record.json:1>
[run100]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/runs/CIFAR100_run_record.json:1>
[val]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/validation_record.json:1>
[v10-40]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/validation_record.json:223>
[v10-80]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/validation_record.json:457>
[v100-40]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/validation_record.json:11347>
[v100-80]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/validation_record.json:22021>
[handoff]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/handoff.md:1>
[hashes]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/artifact_hashes.json:1>
[statehash]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/direction_a/backbone_preparation.py:28>
[runner]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/scripts/prepare_direction_a_backbones.py:202>
[pt10-40]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/checkpoints/A-backbone-CIFAR10-s2026101321-r0040-v1.pt>
[pt10-80]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/checkpoints/A-backbone-CIFAR10-s2026101321-r0080-v1.pt>
[pt100-40]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/checkpoints/A-backbone-CIFAR100-s2026101322-r0040-v1.pt>
[pt100-80]: <E:/Federated Machine Learning/FL-Byzantine-Library-astra/artifacts/direction_a/backbone_preparation_v1/checkpoints/A-backbone-CIFAR100-s2026101322-r0080-v1.pt>

