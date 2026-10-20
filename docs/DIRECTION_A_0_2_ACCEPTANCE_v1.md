# 0.2 基础口径验收交付 v1

日期：2026-10-12（Asia/Shanghai）。解释器：`E:\anaconda3\python.exe`。执行范围仅为 0.2。

**结论：0.2 可执行部分通过。** 两数据集的 smoke 与独立构建的 20 端完整规模候选任务均通过数据验收；ResNet-8 适配、数值重复与独立参照通过。`ε_num=1e-6` 是 logits 口径的**候选值**，尚未冻结；0.2 正式封版及依赖该数值的后续验收等待审查采纳。本交付不放行 G1.1/G1.2，不认证参考 checkpoint，不构成研究关口成功证据。未发现设计与实现冲突。

## 现场预检与输入

根目录：`E:\Federated Machine Learning\FL-Byzantine-Library-astra`。

|项目|本次实际结果|
|---|---|
|当前分支|`feature/direction-a`，符合期望|
|初始工作区|无已跟踪文件改动；3 个未跟踪输入文档：检查点、可行性、冻结协议|
|最近 commit 1|`902af7e docs: add non-attack research base and direction selection`|
|最近 commit 2|`9d0cfa8 Merge remote-tracking branch 'origin/master'`|
|最近 commit 3|`0cc8aa3 update papers`|
|解释器|`E:\anaconda3\python.exe` 存在；实测 PyTorch 2.5.1、CUDA 12.1、cuDNN 90100，RTX 4060 Laptop GPU|

以下五项存在、可读，且运行前 SHA-256 写入 `summary.json`，交付前再次核对输入未变：

- `E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_PROTOCOL_FREEZE_v1.md`
- `E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_CHECKPOINTS_v1.md`
- `E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_A_FEASIBILITY_v1.md`
- `E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\RESEARCH_INNOVATIONS_v1.md`
- `E:\Federated Machine Learning\FL-Byzantine-Library-astra\docs\DIRECTION_SELECTION_v1.md`

必读范围已核对：检查点 0.2 七项全文；合同 §2.2 R01–R07、§4 W01–W07/E01–E05、§6 ε_num、§7.2 0.2 行；创新文档方向 A §2/§3；可行性 §三任务、模型、评价、成本相关内容。源码复用只涉及现有 ResNet 骨干；easyFL 和其他原有源码无改动。

## Smoke 额度与累计实耗

所有前向/扫描前已写入 `DIRECTION_A_0_2_RUN_RECORD_v1.md`。初始登记的精确原文封存在 `artifacts/direction_a/phase0_2_v1/preregistration.md`，SHA-256 与 `summary.json` 的运行前记录一致。追加只读加载核验开始前另记 60 秒上限，累计原额度，不重置、不重建任务、不重选容差。

|字段|预登记额度|实际/状态|
|---|---|---|
|数据集、端数、类别数|真实 CIFAR-10-LT / CIFAR-100-LT；smoke N=4，C=10/100|两份 smoke 均通过|
|smoke 数据量|两者每类头类最终训练 H=100；每类 validation=2，test=8|train=242/2131，validation=20/200，test=80/800|
|相对主设置缩小|N=20→4；每类最多 100；单数据种子；不执行邀请/200 更新轮/3 种速度/3 个研究配对种子|保持完整 C、IF 参数 100、α=0.1 和同构 ResNet-8；只工程核验|
|完整规模候选任务|另建 N=20、C=10/100；H=4500/450，validation 每类 100/10，官方 test 10000|独立生成、独立验收；未由 smoke 改名升级|
|前向/路径求值|共 128 上限；完整、拼接、旧接口、标量 head 参照分别计|73；无 backward|
|统计扫描|共 4096 上限；按登记的有名源/类别选择/整表审计/独立参照遍历计|484；含追加 11 次；不是训练批次数或逐条样本数量|
|单机工作负载经过时间|共 900 秒；数据 600、模型 240、追加只读核验 60 秒|以封存 run.json 为准，累计 15.906 秒：startup 1.047、data 1.562、model 9.797、verification 3.500；两段工作负载相加，写实现/文档的间隔不计作计算实耗|
|证据写入|32 MiB 本地证据上限|运行账本累计写入 3,348,021 byte；含重复写入，不等于真实网络字节；文档另列，整个交付仍低于 32 MiB|
|替代物身份|数据/骨干无替代；随机初始化模型作数值参照；手写标签/标量公式和零输入作独立 oracle|两个模型初始化 seed=20261012/20261013；无训练 checkpoint|
|attempt/训练/匹配/重训|均 0；本关不执行|均 0；没有模拟/通信/注册事件|
|搜索/修订|固定 4 个任务配置；候选搜索 0；最多 1 次修正后重跑，累计原额度|搜索 0、失败 0、重跑 0；只读追加验证不是重跑|
|触顶动作|任一额度到达立即停，保存字段与已有证据，报“证据不足/预算耗尽”，不扩大额度、不提交通过 commit|未触顶；计数、分段时间、总时间保护的独立边界测试通过|

## A 专用任务清单、索引与计数

文件根：`E:\Federated Machine Learning\FL-Byzantine-Library-astra\artifacts\direction_a\phase0_2_v1\tasks`。每份独立身份目录都有 `info.json`、`data.json`、`counts.json`、`acceptance.json`；保存后重读并再次独立验收。

|任务目录身份|N×C|最终 train|validation|test|舍弃 official train|未使用 official test|实测 IF|
|---|---:|---:|---:|---:|---:|---:|---:|
|FedPCC-0.2-smoke-CIFAR10-v1|4×10|242|20|80|49738|9920|100|
|FedPCC-0.2-smoke-CIFAR100-v1|4×100|2131|200|800|47669|9200|100|
|FedPCC-0.2-candidate-CIFAR10-N20-v1|20×10|11165|1000|10000|37835|0|100|
|FedPCC-0.2-candidate-CIFAR100-N20-v1|20×100|9754|1000|10000|39246|0|112.5|

**切分选择及理由：**A 专用 NumPy PCG64 索引生成器，离线读已存在官方 CIFAR pickle；不下载数据，不使用旧 D1 的根数据/IF=50 或旧 FLGO 的分区定义。这样可以明示最终训练池、整数化和独立客户端测试，完整保存索引。每数据集每任务均独立以 seed=20261012 构建，不通过挑种子纠正缺类或端样本量。

**IF 统计定义：**先从官方训练集每类预留固定 validation，再对剩余池选最终 train。类 c 目标数 `N_c=max(1,floor(H*100^(-c/(C-1))))`，按类 ID 递减；其余 official train 全部保存为舍弃索引，没有服务器 root。实测 IF 为 `max(N_c)/min(N_c)`。C100 完整候选任务的尾类为 4 图、头类 450 图，因 floor 得 112.5；这是预登记整数规则的结果，不把它伪称实测恰为 100。完整逐类向量和逐端矩阵在 counts 中。

**α 统计定义：**每类独立抽 `Dirichlet([0.1]*N)`，α 不按全局类频率缩放；按最大余数法分配该类 `N_c`，余数并列按端 ID。类内索引随机后按分配数切分，不强制最小持有类数、端容量或重抽。实际每类概率向量保存在 info。C10 完整候选最终逐类训练数是 `[4500,2697,1617,969,581,348,208,125,75,45]`，逐端训练数范围 2–3508；C100 完整候选逐端范围 214–845。这些不均衡原样记录，不在本关作来源支持裁决。

**独立客户端测试：**official test 逐类打乱、按客户端轮转均分，独立于 train 划分，不按各端训练占比再分。完整候选每端 500 图且均覆盖完整 C；smoke 每端每类 2 图，C10 每端 20、C100 每端 200。它是固定类均衡客户端测试，不宣称是客户端自然训练分布。validation 是固定全局类均衡验证集，不复制到每个客户端。全局 test 是客户端 test 的联合评价视图，该重叠已约定。

**数据验收不依赖 ε_num：**训练/验证同属 `official_train` 命名空间，测试属 `official_test`；同号索引跨源不能误判为同一条记录。逐端 train 互斥、逐端 test 互斥、train/validation/舍弃互斥且加和覆盖 50000；选中 test/未使用 test 互斥且覆盖 10000；global test 等于逐端 test 联合。每项无重复、无越界。生成路径采用 bincount，独立验收采用标量逐标签计数/Counter、集合恒等式和 exp/log 独立 LT 公式；包含故意泄漏 validation 的负例，确认其被拒绝。

|任务|全局缺类（零来源）|单来源类别数|多来源类别数|逐端缺类对数量|每类来源数范围|
|---|---:|---:|---:|---:|---:|
|C10 smoke|0|6|4|23|1–3|
|C100 smoke|0|55|45|238|1–3|
|C10 N20 候选|0|0|10|115|6–12|
|C100 N20 候选|0|0|100|1407|2–12|

四任务空训练端均为 0。缺类列表、单/多/零来源类别 ID、尾类持有端集合、`n_ic`、`N_c` 和 `a_ic=n_ic/N_c` 均显式保存。逐端矩阵列和等于独立总体计数，维度分别 10/100。只读 `TaskReader` 验证封存文件哈希，返回固定索引 tuple 和数据视图，不重新划分或重新登记一份计数；后续改变计数/分组必须回 0.2 重验并作废旧依赖结论。

## 模型适配验收与 ε_num 实测

复用 `models/ResNet.py` 中 `ResNet_3Layer(BasicBlock,[1,1,1])`：32/64/128 通道、option-B 投影 shortcut、128 维 encode、有偏置的线性 head。A 完整 forward 返回原始 logits，head 与原 linear 是同一模块，state_dict 不重复注册参数；旧接口的 log-probabilities 单独与 `log_softmax(A logits)` 比较。CE 对原始 logits，mean reduction，无类权重。

|对象|C10|C100|
|---|---:|---:|
|参数量（独立按层标量算式核对）|308650|320260|
|head weight|10×128|100×128|
|BN 层数|9|9|
|encode 维度|128|128|

BN：`eps=1e-5, momentum=0.1, affine=True`。本次 eval，全部参数禁止求导；参数、running_mean/var、num_batches_tracked 逐项前后不变，包含在模型状态 SHA-256。训练模式下的 BN 或训练精度未在本关数值结论中认证。

变换完全确定：uint8 NCHW RGB 转 float32 `/255`，无随机增强，train/validation/test 相同。C10 mean `(0.4914,0.4822,0.4465)`、std `(0.247,0.243,0.262)`；C100 mean `(0.5071,0.4867,0.4408)`、std `(0.2675,0.2565,0.2761)`；常量及实现指纹在 verification 中。0/255 像素及只读任务样本的变换通过独立标量公式核对。改变这些口径需新版本并重验。

精度：float32，CPU 与 CUDA；禁用 TF32，确定性算法，cuDNN benchmark 关闭。参考对象：pre-softmax logits。比较范数：L∞ 绝对差和 Frobenius 差；归一化尺度 `s=max(1,||reference||∞)`。两个初始化种子，C=10/100，实际官方 test 前 4 图与全零规范化输入 2 图，各在 CPU/CUDA 比较；逐次参考 logits、最小/最大范围、尺度、参数/BN 状态哈希保存在 `model_acceptance.json`。GPU peak allocated 14,661,632 byte，只是本次 PyTorch CUDA 分配峰值，不代表服务器/端完整内存预算。

|比较|最大绝对 L∞|最大 Frobenius|最大归一化 L∞|
|---|---:|---:|---:|
|完整 forward vs encode/head|0|0|0|
|重复完整 forward|0|0|0|
|旧接口 vs log_softmax(A logits)|0|0|0|
|独立零输入→head bias|0|0|0|
|独立 float64 标量 fsum head|5.22945e-8|1.69455e-7|5.22945e-8|
|CPU float32 vs CUDA float32|8.94070e-8|3.18510e-7|8.94070e-8|

独立参照另外包括：手设 head 的 `2*4+(-3)*(-2)+5=19`；均匀 logits 的交叉熵 `ln(10)`；零输入在默认无卷积 bias、BN mean=0 条件下 encode=0、logits 等于 head bias。未计算类梯度、没有优化器/训练/匹配/重训。

**候选 ε_num：1e-6，无量纲归一化 logits L∞ 口径。** float32 machine epsilon `u=1.1920928955078125e-7`；按运行前程序取 `max(8u,4*实测最大归一化差)`，再向上取 1 位十进制有效数字：`max(9.5367431640625e-7,3.576278686523438e-7)` 向上得 `1e-6`。等价绝对判定式是 `||Δlogits||∞ <= 1e-6*max(1,||reference logits||∞)`。

这提供有限精度舍入和重复测量的选择依据，没有用容差掩盖接口或系统性偏移：完整/拼接、重复、旧接口兼容均另行要求精确一致，且手算/独立公式均通过。该候选不覆盖梯度、恢复、其他精度、训练态或未测平台；是否采纳为合同 §6 冻结值由审查裁决。不存在已合格训练快照：本次数值对象来自记录种子的 PyTorch 默认初始化，训练预算 0，不保存 checkpoint，不进行 G1.2 参考认证。

## 评价分母与成本字段

头/中/尾依据最终 `N_c` 降序排序，同计数按类 ID 升序；切点 `floor(C/3)`、`floor(2C/3)`。本次 C10：head=0–2、middle=3–5、tail=6–9；C100：head=0–32、middle=33–65、tail=66–99。分组不使用 test 表现，固定表在 counts 中。

- 全局样本精度分母为固定选中 test 图数；macro recall 分母为完整 C，头/中/尾为固定各组类数；已覆盖类另报其 ID/分母，不能删除未覆盖类来替代全类结果。零测试类记 missing，相关完整分母 macro 记不可计算，不默填 0 或剔除。
- 客户端等权平均按固定 N；最差 10% 取 `max(1,ceil(0.1*N))` 个客户端，精度并列按端 ID；单端最低直接取 minimum。尾类持有端为 train 尾类计数 >0 的固定集合，子群分母为该集合端数。无测试客户端显式 missing；相应完整汇总不可计算。客户端类别数、测试量及端量齐报。
- 成本分别登记实际单机数据核验/模型核验/追加核验秒数、累计文件写入 byte、搜索/重跑次数和 GPU 分配峰值；累计时长与程序各段经过时间一致。未模拟实际端计算、系统墙钟、传输时间，不填成效率实验结果。
- W01 普通训练、W02 类梯度/特征统计、W04/W05/W06 匹配/重训/直接更新、W07 版本调度均未执行；E01–E05 邀请、速度、截止/支持、attempt 和概率预测均未实现。W03 仅交付计数矩阵，不发送注册：int64 计数的理论载荷分别 320/3200/1600/16000 byte，真实注册/上下行发送量不适用。独立测试 oracle 的 confusion 矩阵只是分母算术，不是模型精度或研究结果。

## 文件清单与 Git 交付

以下为本次新增文件，根目录均为 `E:\Federated Machine Learning\FL-Byzantine-Library-astra`；没有修改原有源码、输入文档或 easyFL。完整证据文件内容 SHA-256 在 artifact_hashes 中，任务 info 也保存独立 data/counts/acceptance 哈希；运行前五输入版本在 summary，最终实现指纹在 verification。

|路径/目录|具体文件|
|---|---|
|项目根|`.gitattributes`（本次证据保留精确字节；新增源码固定 LF，防止 Git 自动换行转换使 SHA-256 失效）|
|`direction_a/`|`__init__.py`, `budget.py`, `evaluation.py`, `model.py`, `task.py`|
|`scripts/`|`accept_direction_a_baseline.py`（接受默认 bounded 验收与 `--verify-saved` 累计只读核验）|
|`tests/`|`test_direction_a_baseline.py`（被额度受控入口调用的独立参照断言）|
|`docs/`|`DIRECTION_A_0_2_RUN_RECORD_v1.md`, `DIRECTION_A_0_2_ACCEPTANCE_v1.md`|
|`artifacts/direction_a/phase0_2_v1/`|`preregistration.md`, `run.json`, `summary.json`, `model_acceptance.json`, `verification.json`, `artifact_hashes.json`|
|`…/tasks/FedPCC-0.2-smoke-CIFAR10-v1/`|`info.json`, `data.json`, `counts.json`, `acceptance.json`|
|`…/tasks/FedPCC-0.2-smoke-CIFAR100-v1/`|`info.json`, `data.json`, `counts.json`, `acceptance.json`|
|`…/tasks/FedPCC-0.2-candidate-CIFAR10-N20-v1/`|`info.json`, `data.json`, `counts.json`, `acceptance.json`|
|`…/tasks/FedPCC-0.2-candidate-CIFAR100-N20-v1/`|`info.json`, `data.json`, `counts.json`, `acceptance.json`|

提交前逐项核对 Git 待提交文件，仅显式添加上表文件（32 个）；不加入初始三个未跟踪输入，不添加 outputs、.idea、临时脚本或 __pycache__。暂存文件逐字节核对，确认 Git 中的证据与工作区验收对象相同。提交消息按用户约定为 `phase0.2: baseline protocol and model acceptance`，commit hash 在最终答复给出，避免在自身提交中写自引用 hash。无中间提交、无 push。完成后停在本关，等待确认。
