# 合格骨干准备候选交付说明 v1

日期：2026-10-13（Asia/Shanghai）。`parent_checkpoint=G1.2`，`work_item=合格骨干准备`。准备身份 `FedPCC-backbone-preparation-v1`。**交付状态：候选包完整、来源可核对；不签 G1.2 通过，不认证合格冻结参考或 P 可分性。** 本说明按归属裁决 §3.2 的八个逻辑文件逐项交接，不新增检查点编号或成功门槛。

## 现场与运行身份

项目根：`E:\Federated Machine Learning\FL-Byzantine-Library-astra`。解释器：`E:\anaconda3\python.exe`，全部执行显式 `-B`。分支 `feature/direction-a`；初始工作区干净、与 origin 同步。最近五个 commit：`54eb6e0 docs: G1.1 adjudication and protocol sync`、`e3c3528 docs: record direction A adjudications and sync backbone preparation`、`6ea9bd1 phaseG1.1: invitation and completion event support`、`e3ca623 phase0.2: baseline protocol and model acceptance`、`902af7e docs: add non-attack research base and direction selection`。

预检六项均存在、可读，实际绝对路径如下：

- `E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_BACKBONE_PREPARATION_ADJUDICATION_v1.md`
- `E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_PROTOCOL_FREEZE_v1.md`
- `E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_CHECKPOINTS_v1.md`
- `E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_G1_1_ADJUDICATION_v1.md`
- `E:\Federated Machine Learning\FL-Byzantine-Library-astra\artifacts\direction_a\phase0_2_v1\tasks\FedPCC-0.2-candidate-CIFAR10-N20-v1\`
- `E:\Federated Machine Learning\FL-Byzantine-Library-astra\artifacts\direction_a\phase0_2_v1\tasks\FedPCC-0.2-candidate-CIFAR100-N20-v1\`

骨干准备裁决已全文读取；合同 R01–R07、W01/W07、§7.2，K G1.2 七项及 G1.1 裁决 §2.2 已核对。G1.1 正式状态仍为“证据不足/预算耗尽”（证据不足，未耗尽）；裁决允许本输入生产工作独立开展，本次理想参与普通训练不替代正式事件支持审计。

证据包根：`E:\Federated Machine Learning\FL-Byzantine-Library-astra\artifacts\direction_a\backbone_preparation_v1\`。下文相对证据路径均从这里解析；原 0.2 任务引用另从项目根解析。

## 1. manifest.json：交接索引与归档

`manifest.json` 登记 parent/work_item/准备身份、基准 commit、开始/交付时间、输入文档版本与原始 SHA-256、四个参考点及其文件/状态哈希、生成运行与训练进度、验证文件/key、生成配置与任务绑定哈希、缺失项和未认证范围。输入版本覆盖 K、合同、0.2 裁决/验收、骨干准备裁决、G1.1 裁决；使用本次预检工作区版本，不覆盖历史裁决哈希。

基准 commit 为 `54eb6e02f4630df82cfdeb1c352fd5e4520ea5be`；manifest 开始时间 `2026-10-13T17:04:02.429826+08:00`，交付时间 `2026-10-13T17:05:20.745411+08:00`。预登记原文 SHA-256 为 `78d52e8ccd9706b02e0c85dc970339716e76045b3fe84c285023c50910eb405d`；生成配置 `720ecb999bea965af09162f5282716eb1c7e1703a1af50b7194521c214daff48`；任务绑定 `194f1ef65a13caf66a64c74a77585c4a932dc5f72c909a21cc5b9290a7649408`；验证记录 `aa5cca1923400486f87a6c1f53e89a6f648a69bb1b9cab2e2a0ec1b9fd7e66a8`。

|输入文档（均 v1，本次预检原始字节）|SHA-256|
|---|---|
|DIRECTION_A_CHECKPOINTS_v1.md|8fe09ca87e9cdb5dd053a22e8ee3ba02a37d64f72dcc96e8987c338b8c09e98a|
|DIRECTION_A_PROTOCOL_FREEZE_v1.md|63aa379b5ed68b0bb1f05e9215fcff0ced638c24486522e2d7a4386902a87898|
|DIRECTION_A_0_2_ADJUDICATION_v1.md|a61ad0275f92375f3f667761dcc9cec9891bb5abce3dee2fbca3a31dc1dc9f7d|
|DIRECTION_A_0_2_ACCEPTANCE_v1.md|8907e7a21e6bdf1e205dcc61f41164a5ae77a9a7ec44e2fc06d3eb71ba41aedf|
|DIRECTION_A_BACKBONE_PREPARATION_ADJUDICATION_v1.md|c863529137063c5cd9e39485b0445844cd3a837aa07512bf1c76f877d86ffd28|
|DIRECTION_A_G1_1_ADJUDICATION_v1.md|cd65b23b8ed3e18e37186048a694031df92c2495af0432a30c7ff5ac21b951a4|

|reference_id（也是参考版本身份）|生成运行|更新轮/attempt/SGD steps|真实快照|
|---|---|---|---|
|A-backbone-CIFAR10-s2026101321-r0040-v1|FedPCC-backbone-prep-CIFAR10-v1|40 / 40 / 1600|checkpoints/A-backbone-CIFAR10-s2026101321-r0040-v1.pt|
|A-backbone-CIFAR10-s2026101321-r0080-v1|同一 C10 运行|80 / 80 / 3200|checkpoints/A-backbone-CIFAR10-s2026101321-r0080-v1.pt|
|A-backbone-CIFAR100-s2026101322-r0040-v1|FedPCC-backbone-prep-CIFAR100-v1|40 / 40 / 1600|checkpoints/A-backbone-CIFAR100-s2026101322-r0040-v1.pt|
|A-backbone-CIFAR100-s2026101322-r0080-v1|同一 C100 运行|80 / 80 / 3200|checkpoints/A-backbone-CIFAR100-s2026101322-r0080-v1.pt|

四点都预先登记并全部保留；`missing_items=[]`。每点对应 `validation_record.json` 的 `records/reference_id=<该 ID>`；该文件整体字节哈希在 artifact_hashes 的同名条目中。准备归 G1.2 的候选来源分项，不给整个 G1.2 盖“通过”。生成、验证/预选点、保存/读回成本归现有 G1.1/G1.2/G1.3 合并预算行的 G1.2 分项；两点共享一个运行，其训练成本各记一次。原 G1.1 历史账本保留，未清零、未并作本次训练成本；本次也不支付或冒称已完成后续类梯度测量。

## 2. task_binding.json：任务、统计与种子绑定

两任务各自列明原目录和 `info.json/data.json/counts.json/acceptance.json` 四路径/原始 SHA-256；该八文件运行前匹配 0.2 清单及 info 内层哈希，运行后原始字节不变。没有重算 n_ic/N_c/a_ic、替换分组/尾类持有端或重新切分。

每个文件的完整项目相对路径为 `artifacts/direction_a/phase0_2_v1/tasks/<下表任务身份>/<文件名>`；原始 SHA-256 如下：

|文件名|CIFAR10-N20 原字节 SHA-256|CIFAR100-N20 原字节 SHA-256|
|---|---|---|
|info.json|ef7f9c35430157b29f7700809e77ed32d0ecf9ed51de54abc4ff7df91f36ed05|cbafbbf5afcd0513b618b4d8b868c89f10821a85de03f22c925368971fa6d1af|
|data.json|be2130d1cc5f0ec943c1572bf5137ee423f9664e3ec28414dcaf8d24ba061882|b3061f6797dc29c394e448c23cef076393844cacec8196fb9634463e5d73e012|
|counts.json|2a45b196365c480b58bd85c8305d85ee3fc2fa194bbb0d984784ff7ccc78a5fc|5d51e654174b961bc4ea8f47958ff979f0ab087e44acee448feaf9eb8d61463a|
|acceptance.json|48d4e5b241afd4d8dee9453ef9a8d8fd9884ca219498307a4a9cb83babdfc541|3c812fe7beb07ff3475647b50cee941bfd247306d6b57aa85881af2377b703a9|

|字段|C10|C100|
|---|---|---|
|任务身份|FedPCC-0.2-candidate-CIFAR10-N20-v1|FedPCC-0.2-candidate-CIFAR100-N20-v1|
|N / C / 标签映射|20 / 10 / 类 ID 0–9 静态同号|20 / 100 / 类 ID 0–99 静态同号|
|最终 train / validation / test|11165 / 1000 / 10000|9754 / 1000 / 10000|
|名义 IF / 实测 IF|100 / 100|100 / 112.5|
|数据划分 seed / 本次训练 seed|20261012 / 2026101321|20261012 / 2026101322|
|冻结 head/middle/tail 分组|0–2 / 3–5 / 6–9|0–32 / 33–65 / 66–99|

split 身份：train/validation 属 official_train，test 属 official_test；validation 是封存的全局固定类均衡 holdout，客户端 test 是固定按类均衡子集，global test 为其联合视图。训练只从每端封存 train 抽样；验证只用固定 validation；本次不读测试图像，也不按测试表现选参考。原始官方训练文件先按 info 的 SHA-256 核对，再按封存索引取图像/标签；没有用重新统计原始训练标签来替换计数。

α 沿用 0.2 裁决：每类独立对称 Dirichlet([0.1]×20)，不按全局类频率缩放；最大余数整数化、并列按端 ID，不做容量平衡或重抽。标签映射、组表、尾类持有端 ID 表原值以及各自 counts.json 来源路径/哈希均在 task_binding 中；尾类持有端不从测试类别覆盖反推。候选目录仍保留历史名称，正式采用身份同时引用 0.2 裁决。

尾类持有端的冻结端序号：C10 为 `[0,1,2,3,4,7,8,9,10,11,12,14,15,16,17,18,19]`，C100 为全部 `[0..19]`；端 ID 按 `client_<三位序号>` 定位，各表直接复制上述 counts 来源，不新定义另一套持有端。

## 3. checkpoints：完整真实快照、版本与读取

四份 `.pt` 均包含完整 backbone、linear head 与全部 BN affine/running_mean/running_var/num_batches_tracked state，以及绑定 reference/run/task/config/seed/进度的 metadata。骨干和头不拆开，reference_id 唯一绑定同版本全状态；没有用随机种子代替真实文件。

模型配置：现有 ResNet8Adapter，ResNet_3Layer(BasicBlock,[1,1,1])、32/64/128 通道、option-B shortcut；d=128；head 名 `linear.weight/linear.bias`，C10 形状 `[10,128]/[10]`，C100 `[100,128]/[100]`，bias=True。参数及 BN 浮点缓冲为 float32，num_batches_tracked 为 int64。9 个 BN 的 eps=1e-5、momentum=0.1、affine=True。各点 metadata 的 C/d/形状/bias/dtype 和来源完整；实际 tensor 内容以 state_dict 为准。

文件 SHA-256（序列化容器含 metadata）与状态 SHA-256（逐 key 的 name/dtype/shape/tensor 原始字节，含全部 BN）分开记录：

|点|文件 SHA-256|状态 SHA-256|
|---|---|---|
|C10 r40|4824d4a52a3aa46df594e7600d72cb64eab082a33b376dbebe17057d3081f26c|48466c475471fe8a05392a54fbca7fa9eee2d9189b2ca7041e9a72244b6d5fb3|
|C10 r80|d8e137b9feeda74bb3bf401b64569e0075f3ec52914eb0ccf72d56040965a5ed|c2a11303f977029a840946f1703047288365ec4b6bbb7136db3ad3eb65ad4b44|
|C100 r40|e778839c234857195c4e00d286b6210d8898d4e1405f504ca2b2a5f0c75a8764|3b4e3a4b03982c4b3bf1c6be16a46999ffc3987934443b59b25370ada831408f|
|C100 r80|7b6faf5b0a4be006133c72140d60e9d5918d52f8aa953f800b87efab268dccae|5a84b86e6d66a21ea5ea2ebf2e72b41a37db86402e2063cdc5a9b2d34018597a|

每文件已 `torch.load(weights_only=True)` 从实际落盘字节读回，逐参数/缓冲 bitwise equality，重建适配器 strict load 后状态 hash 相同；状态也区别于初始随机模型及该轮聚合前状态。此为准备包保存完整性自检，不是新训练对象的数值误差/梯度接收验收，不套用 0.2 ε_num。

恢复读取来源：`direction_a.backbone_preparation.restore_candidate(path, device='cpu')` 返回 eval、requires_grad(False) 的 ResNet8Adapter 和来源 metadata；源码/适配器/旧骨干文件指纹在 generation_config 中。训练没有断点续训；这些文件是冻结参考输入，不是 E1 全状态恢复包，不含用于续训认证的全生命周期状态。

## 4. generation_config.json：普通生成配置

来源是本次新训练，未采用任何历史模型快照。每任务先 manual_seed，再创建 PyTorch 默认初始化模型；训练 seed 与数据划分 seed 已分列。初始状态哈希在运行账本与每个快照 metadata 中，两个初始普通头验证仅记基线，不列候选。

普通 FedAvg 配置是运行前预选的单一工程配置，无超参数搜索：每任务 80 更新轮，每轮独立均匀无放回邀请 8/20，全部受邀端完成/返回；不用 G1.1 的代理截止/在线/掉线/速度，不声称它已变成正式完成机制。每次受邀从自己的封存 train 均匀有放回取满 batch=64，固定 5 个 SGD steps；小端亦保持固定步数/批量。SGD momentum=0.9、weight_decay=5e-4、Nesterov=False，优化器每次邀请重置；lr 1–40 为 0.05、41–80 为 0.01。原始 logits 的 mean CE，无类权重、无合成/校准/概率修正。

浮点参数和 BN running_mean/var 以返回端已封存训练样本量归一化加权；num_batches_tracked 取 max。每轮日志保存计划/返回 ID、封存样本量和实际聚合权重。BN 训练态在本地更新，验证/参考读出为 eval、缓冲不变；不将训练态 BN 说成已由 0.2 认证。

变换完全沿用 0.2，无随机增强：RGB uint8 NCHW /255；C10 mean `(0.4914,0.4822,0.4465)`、std `(0.247,0.243,0.262)`；C100 mean `(0.5071,0.4867,0.4408)`、std `(0.2675,0.2565,0.2761)`。模型/适配器、损失、变换、BN、客户端参与、初始化、优化器、学习率、batch/steps、RNG 及环境/实现指纹均在配置中；参考规则为第 40/80 轮全留，无事后最佳点。

环境为本次实际 E:\anaconda3\python.exe 的 PyTorch 2.5.1+CUDA、float32；确定性算法、TF32 关闭、cuDNN benchmark 关闭、CPU threads=2。邀请用 PCG64(training_seed+1000)，每端 batch 采样用 PCG64(training_seed+2000+端序号)，独立于验证/后续收益。

## 5. run_record：额度、实际训练、资源与成本归属

预登记在本说明同名 RUN_RECORD 文档和包内精确 `preregistration.md`，manifest 绑定其 SHA-256。全局 `run_record.json` 为累计额度/实耗；`runs/CIFAR10_run_record.json`、`runs/CIFAR100_run_record.json` 为生成来源账本，保存实际开始/结束、每轮邀请/返回、每次端工作量/训练 CE/计时/采样指纹、更新进度、参考点位置和资源对象。

|额度项|运行前上限|实际|
|---|---|---|
|每任务/累计 attempt|90 / 180|80 / 160；每任务真实更新 80；无空完成|
|每任务/累计 SGD/backward|3600 / 7200|3200 / 6400；各 640 次端参与，共处理 409600 个有放回训练样本|
|模型前向/统计遍历|7500 / 1024|6448（6400 训练+48 验证）/18；不做类梯度或探针|
|总工作负载|1200 秒|84.172 秒|
|每任务训练|480 秒|C10 41.437、C100 35.405 秒（含普通聚合/状态复制等阶段开销）|
|输入/验证/保存核对|90 / 90 / 90 秒|0.891 / 0.392 / 0.156 秒；另有 startup 5.891 秒|
|证据文件写入|256 MiB，含 128 KiB 应急槽|额度记账 12304020 byte，含未动用的 131072 byte 预留；运行证据实写 12172948 byte，另列本说明文本|
|逻辑上下行参数/缓冲复制|合计 4 GiB|3233966080 byte 理论 state 载荷；非网络实测|
|CUDA 分配/CPU 张量代理|6 GiB / 2 GiB|CUDA allocated 峰 C10 320941056、C100 304121344 byte；CPU 常驻张量代理 303483520/286145152 byte|
|搜索/修正重跑|0 / 最多 1|0 / 0，无失败、中断或续训|

所有上限触顶动作均为停止、保留已有点/缺失项和命中字段，不扩额、不凑精度，不将不完整四点集合收窄为通过；本次 `hit=null`。CPU 代理仅为缓存/张量已知占用，不冒称完整进程峰值；另实际记录 Windows PROCESS_MEMORY_COUNTERS working set/peak working set，运行末 C10/C100 对应峰为 1258766336/1899732992 byte。CUDA allocator allocated/reserved 峰分列，不冒称全部驱动/设备内存。

C10 运行时间为 2026-10-13 17:04:03.005036–17:04:44.801521（+08:00）；C100 为 17:04:45.167084–17:05:20.724411。每个运行拥有两个点，共享训练成本一次；不是四次独立训练，也不是三个研究配对种子。单机顺序训练没有实际网络/设备注册、传输带宽/事件模拟墙钟，这些不适用项附原因，不以 null 冒充实测 0。每任务理论上/下行各为 C10 793630720、C100 823352320 byte。G1.2 准备成本分项保留；类梯度测量未执行，不登记为免费诊断。

## 6. validation_record.json：固定验证、指标分母与选用理由

每点记录 reference_id、文件/状态 SHA-256、固定 validation 身份/数据文件哈希、模型模式、变换、batch=128、记录时间、训练进度及选用理由。验证只有官方训练源中的固定 validation；每任务 1000 图，C10 每类 100、C100 每类 10；全类/组类分母为 10 与 3/3/4、100 与 33/33/34。逐类 recall、完整 confusion 矩阵、每类样本分母、缺失类清单也完整保存；本次缺失类为空，零 recall 不删除。

|预选候选|mean CE（nat）|样本精度|全 C macro recall|head / middle / tail recall（fraction）|
|---|---:|---:|---:|---|
|C10 r40|3.2900222473|10.0%|0.100|0.333333 / 0 / 0|
|C10 r80|3.0904185791|12.1%|0.121|0.403333 / 0 / 0|
|C100 r40|4.9823510742|6.0%|0.060|0.148485 / 0.033333 / 0|
|C100 r80|4.8815247192|7.8%|0.078|0.236364 / 0 / 0|

初始随机模型基线另列：C10 accuracy=11.5%、CE=2.302680542；C100 accuracy=0.9%、CE=4.606916534；均 selected=False，明确不是训练候选。r40 是按计划完整保存的中间进度，r80 是计划终点；两生成运行最终均完成 80 更新，不把 r40 的部分进度冒称另一轮独立完整训练。

四个点 selected=True，理由只有“预定进度点全保留”；没有不交付点，没有引用新增资格阈值。**普通头验证较低、四点 tail recall 均为 0，是必须随包保留的限制。** 按裁决 §3.3/§四，没有适用的最低精度门槛时不能事后设一条线判合格或不合格；本次不增加轮数/调整参数凑精度，不将普通头结果等同于特征可分性，最终参考资格未签定。

## 7. handoff.md：完整性自检、限制与接收责任

包内 `handoff.md` 与本说明共同定位八个逻辑交付。独立手算自检覆盖样本权重聚合、浮点 BN/整数计数规则、验证分母/missing 处理及额度边界；训练 loss 与快照状态均有限；四点真实文件可读且同版本 backbone/head/BN 完整，文件/状态哈希有对应，预选点齐备，缺失项为空。当前未发现需要按裁决 §四拒收的文件缺失、任务错绑或保存/读取状态不一致；“最终参考合格”仍没有代签。

§3.3 边界：保持两 CIFAR-LT、20 端、ResNet-8、完整标签、冻结 split/count/变换及 IF/α 区分；执行者只补录允许的工程参数/来源/种子/进度与有限预算。没有研究范围改写、正式最低精度门槛、τ_probe 迁移、测试/方法收益选点。0.2 logits ε_num 不覆盖新训练对象、梯度或恢复；本次精确状态读取自检不承担这些数值验收。

接收方仍需完成 K G1.2 全部原判据：核对正式参考与模型/split/IF/α/训练/变换及多个点匹配；完整输出维度和 bias 的头梯度；单端类均值与逐样本平均；a_ic 汇总 G_c；重复读取参数/缓冲不变；缺类不伪造梯度；完整数据/小批量噪声口径和适用数值容差。之后由 P 处理可分性/校准空间。G1.1 正式证据不足仍须实际 W01/W02/事件资源绑定补齐，本包不提升原代理 smoke 身份；G1.3、A1/A2/A3、E1 全训练生命周期/恢复均未完成或实现。

## 8. artifact_hashes.json 与文件清单

哈希算法为 SHA-256，对象为实际文件原始字节；清单绑定生成配置、任务绑定、验证、运行细账、四快照及交接文本。状态 hash 单独按 name/dtype/shape/tensor bytes 算；不是 checkpoint 文件 hash。清单不包含自身及最终累计 run_record（避免自引用），后两者单独通过 Git 暂存字节核对。每个 reference 与其验证 key/config/run/task 都可由 manifest 定位。

本次提交对象共 20 个：3 个实现/入口/测试文件、2 个文档、14 个候选包文件，另 `.gitattributes` 只追加本次精确路径/证据目录的换行保留规则。具体清单如下（项目根相对路径）：

|位置|具体文件|
|---|---|
|项目根|`.gitattributes`|
|direction_a|`backbone_preparation.py`|
|scripts|`prepare_direction_a_backbones.py`|
|tests|`test_direction_a_backbone_preparation.py`|
|docs|`DIRECTION_A_BACKBONE_PREPARATION_RUN_RECORD_v1.md`、`DIRECTION_A_BACKBONE_PREPARATION_HANDOFF_v1.md`|
|artifacts/direction_a/backbone_preparation_v1|`manifest.json`、`task_binding.json`、`generation_config.json`、`run_record.json`、`validation_record.json`、`handoff.md`、`preregistration.md`、`artifact_hashes.json`|
|同包 runs|`CIFAR10_run_record.json`、`CIFAR100_run_record.json`|
|同包 checkpoints|`A-backbone-CIFAR10-s2026101321-r0040-v1.pt`、`A-backbone-CIFAR10-s2026101321-r0080-v1.pt`、`A-backbone-CIFAR100-s2026101322-r0040-v1.pt`、`A-backbone-CIFAR100-s2026101322-r0080-v1.pt`|

所有输入与既有源码/easyFL/0.2 证据原样保留。提交前确认没有 outputs、.idea、临时脚本、__pycache__ 非预期改动；显式 git add 上表路径，一次最终 commit：`phaseG1.2-prep: qualified backbone preparation`。hash 在最终答复给出，不在自身提交中自引用。无 push，完成后停在候选准备交付等待确认。
