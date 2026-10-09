# D2′ 裁剪版2.2＋2.3执行报告

日期：2026-10-09。权威依据：`D2_PRIME_PHASE2_2_RULING.md`（审查基线a3cda3f6），SHA256 `71108e861bf8321b01a6c8bcc3719ed7317fd247e99aa6acdf0bbe01724d58f9`。三个验收项分别报告如下。**本轮失败分类为机制FAIL，完整可学性未通过，不放行后续攻击比较，不提交。** 机制启用证据达标不解除性能门。

## 迁移复核：PASS

环境预检逐条通过：分支`feature/d2-prime-async`；初始只有允许的裁决文档未跟踪；最近三提交依次为`a3cda3f6 phase2.1: async baseline`、`728c0bdb phase1: sync calibration`、`feeeb41 phase1-pre: RFA contribution interface`；20个必需文件全部存在。所有Python均显式使用`E:\anaconda3\python.exe -B`。

新建正式入口`formal_d2_prime_algorithm.py`，复用原生AsyncServer对象、with_clock/with_latency、ElemClock及2.1客户端完整本地epoch。每tick到期先处理，再接收排序包，FIFO最多20候选；满20、最老候选等8 tick或原尾部条件才尝试`commit_event`。预算等待者保留原位置和槽位，零余额者只从评分/冷统计输入排除。无新终态的尝试结束同tick重试循环。Server从提交完成后的后端读取版本和活任务，waiting诊断不会复活过期任务。

`TaskProtocol`只新增受保护的数值/存储适配钩子，旧公开签名和CPU/float64默认结果不变。`Float32TaskProtocol`保留GPU/float32实际模型和源快照；由实际float32源/回复的精确数值在CPU/double构造并仅一次全范数裁剪规范候选。该候选同时用于模型贡献和原`features`纯函数。临时double位移求和后一次转float32并在GPU写回，每个新源模型逐元素等于实际载体；没有持续演化的隐藏double模型。参考/账本继续原CPU/double规则，直接复用prepare_event、write_reference和RollingBudget。不乘RFA权重、不按小批人数改分母、不增加事后参考投影。

88项自动测试零失败/错误，包括新正式GPU入口10项及旧协议/参考/联合提交/恢复/基线回归。原生ElemClock＋实际797,962参数CNN固定张量用例消费40条、产生2版本，训练0次，载体/新快照逐元素一致。关键独立参照：

| 验收族 | 实测/参照 |
|---|---|
| 正式K20、40同刻到达 | 两批后的标量模型9.25；第二批h=1/2；混合源手算9.125 |
| 触发/协议边界 | 7 tick不开、8 tick开；尾批3端；到期32优先；陈旧64合法/65过期；错身份、未来版本、重复不能消费 |
| 源快照因果性 | 真实付费ready源z=1.1708025545914993，改动当前参考的对照z=15.33392900496485；原源g不变；签发cold不能改绑后来ready；公开快照无张量别名污染 |
| 冷启动/参考 | 少于3个可评分身份等待且不预留；真实收费轨迹cold→ready；零余额者在冷统计前排除；旧独立方向/凸域/零创新收费锚点回归通过 |
| 共享预算 | H33/beta0.4125真实部分缩放、耗尽、左端点释放和重试；最后部分a≈0.025、b≈0.0025、q≈0.0275；模型额度beta/1.1等价性锚点通过 |
| H大于期限损失 | 耗尽后立即重签的20个任务在t32过期，旧费到t33才释放；没有提前退费或改期限。t2签发的等待者可在t33重算余额/源/方向并消费 |
| 原子/负例 | 注入参考或账本写入失败不发布新模型/参考/账本/终态/版本；漏参考费、漏receipt、重复消费审计拒绝；相消/零模型更新仍付费推进版本；waiting诊断最终过期不复活 |
| 进度/数值 | 固定评价目标10/25在事件边界20/40落点，偏移10/15；Q5独立常量A12/N120/P0.10；全范数/特征同候选、两层写回与参考重构通过 |

smoke前已保存实际桶号/符号、参数展开顺序和哈希；`sigma_0=0.25`显式登记，初始mu全0、sigma全0.25、e0、U1、未ready。配置哈希`fa5da28390100180ecab036930a3c43dc78f15d0c76a16f71955c5c9ad35f927`，实际映射文件SHA256`8e6e355e94d081523549152f75fdb04eab1103d43a2a9e72f9f80a17a9e027cc`。有效参考参数32桶/33维、种子0、sigma_min0.05、e_ready0.5、kappa_U0.1、z_cut3、B_R1、eta_R0.1、n_boot3，eta_M1；均沿用原值。

200任务GPU smoke完成：196消费/4拒绝，10次联合提交，模拟t32；800 minibatch、40,670次样本访问，耗时40.750秒。无根读取、无遗留活任务或运输包、无死锁，模型/参考/账本一致。末点10%只作接线记录，smoke不承担可学性或ready覆盖门。迁移和smoke通过后才运行唯一完整单元。

## 完整可学性：FAIL

固定seed101、IR5/Dirichlet alpha1、100客户端、原CIFAR10 CNN、SGD lr0.1、batch64、1 epoch，momentum/weight_decay0，无AMP。K20/40槽/32期限/64陈旧上限/8 tick触发，H33/beta0.4125/B_M0.9701598816245317未变。外生seed1801/801/(2801+c)、快慢名单及各身份延迟随机源沿用2.1。

客户端池20,342、隔离根池2,000，原任务/训练与测试标签哈希、逐客户端索引均核验；无标签包装、根加载0次。开发评价沿用每类前500，共5,000；每类后500未前向。D1曾查看完整测试集，保留部分不能声称从未查看。没有使用IR50/alpha0.1工程检查任务。

12,000实际训练任务全部终结：11,996消费、4拒绝，过期/丢失0；600尝试/600版本，结束t1637，候选与原生运输排空。原后端到期堆仍有180条终态任务的未来到期空操作条目，均无活引用，不计在途训练；没有把它们称为物理空堆。所有commit尝试后审计、每tick任务/槽位/候选队列/模型/版本核验通过，单元结束用持久账目独立重算全部历史窗口。

| 目标任务 | 实际终结 | 偏移 | tick | 版本 | 宏准确率 |
|---|---|---|---|---|---|
| 10400 | 10400 | 0 | 1415 | 520 | 44.04% |
| 10800 | 10800 | 0 | 1469 | 540 | 45.68% |
| 11200 | 11200 | 0 | 1524 | 560 | 43.46% |
| 11600 | 11600 | 0 | 1579 | 580 | 47.44% |
| 12000 | 12000 | 0 | 1637 | 600 | 45.78% |

固定末五点**M=45.280%（精确283/625）**，末点45.78%。较好基线为缓冲平均50.876%，下降**5.596pp**，超出2pp；通过下限48.876%，不得用RFA49.024%或旧3pp规则放宽。

| 段 | 实际A | 到达名义N | P=A/N | 实际写回V | 平均基线V |
|---|---|---|---|---|---|
| S1 | 48.797369 | 85.387500 | 0.571481 | 7.946311 | 13.890132 |
| S2 | 52.790122 | 85.050000 | 0.620695 | 8.350644 | 13.182003 |
| S3 | 52.506369 | 84.666667 | 0.620154 | 8.133830 | 13.071908 |
| S4 | 52.428149 | 85.179167 | 0.615504 | 8.134040 | 13.268713 |
| S5 | 52.261661 | 85.020833 | 0.614692 | 8.038163 | 13.404123 |

后4段P均高于0.10，V均非零且同进度平均基线仍有已核验写回；本次无定义中的持续停滞。快端r=0.600552864、慢端r=0.637039405，**R_slow=1.060754918≥0.80**。分母包含全部已训练任务，以首次合法到达版本差计，不包含g、预算lambda或裁剪比例。完整可学性仍因M门失败。

独立离线事件公式重构（未调用被测prepare_event/write_reference/budget/Server）通过：601源参考快照，11,996 receipt，终态顺序、所有身份延迟和整数派发/FIFO门匹配；最大标量/参考公式误差4.440892098500626e-16。运行时最大E_alg=4.9718247921048259e-09、E_model=4.2519328459518185e-07、参考逐元素重构误差5.5472875929953773e-17；600次写回均通过原两层界和独立float32舍入参照，无NaN/Inf/OOM/死锁。

完整耗时2390.429秒（39.84分钟，含训练/评价/诊断/日志，不含初始化），CUDA峰值已分配92,529,152字节。48,000 minibatch、2,441,323次样本访问，与2.1两基线完全相同；派发/延迟序列哈希同为`adc3e90841bc85590f9494c69fc5a5e66d4adf3d89a37473743f41e93b00a1ac`。评价点的同时已训练工作量由正延迟、每tick评价在新派发之前的固定顺序离线重建，单独原始JSON保留；未伪装成现场额外测量。

## 机制启用：PASS（启用覆盖与路径证据）

首次ready在终结400任务/t54/k20，e=0.5139555873929738，随后有实际新签任务绑定ready源；未靠预充证据。全程cold420条/source11,580条。后半程6,000个已评分task_id中，源路径6,000，覆盖**100%**，未评分0，重复尝试不重复计数。冷源/旧ready源因果边界及源/当前评分区别由上述新入口固定用例验证。 五段任务进度与到达/提交陈旧度的ready、已评分路径、g分位数、预算lambda、终态及快慢端实际系数/名义保留交叉诊断，完整保存在清单与mechanism_progress_staleness_groups.json；空组指标为null。

干净轨迹预算缩放0、等待0，历史最大同身份窗口费0.38197617745809626<beta0.4125，所有q=a+b及b=0.1a、无重复receipt均核验。预算在该轨迹中没有截断，迁移用例已真实触发部分缩放、耗尽、等待与释放。原有费用未在过期时提前退款。

**机制启用PASS描述覆盖和实际运算；本轮性能失败按用户约束10归类为机制FAIL，不放行下游。** 平均g=0.675961444；实际模型系数总量258.783670870/提交前无筛选名义量380.291666667=68.0487%。预算lambda全1；评分使实际系数降低是本轨迹可观察事实。没有运行消融，不能将性能差精确归因于评分或裁剪，也没有足够隔离证据支持直接替换B_M或参考阈值。本轮诊断修订次数0，保留最多一次规则，不自动搜索或重跑。

**B_M在同步干净FedAvg校准后固定迁移到异步场景；它是预先确定的尺度，不保证异步更新恰有5%被裁剪，不是异步最优阈值，也不证明快慢端截断概率相同。**

| 分组 | 合法可观测上传 | 实际裁剪比例 | 平均裁剪系数 |
|---|---|---|---|
| all | 12000 | 6.7333% | 0.988101 |
| consumed | 11996 | 6.7272% | 0.988122 |
| fast | 6931 | 5.2085% | 0.990587 |
| slow | 5069 | 8.8183% | 0.984702 |
| rejected | 4 | 25.0000% | 0.925327 |

全部上传808/12,000被裁剪；实际消费807/11,996。每任务原始范数、裁剪系数、裁剪后范数保存一次，按到达/提交陈旧度与终态分组见清单。空组保留null，不填0；g/h/lambda的缩放未记成B_M裁剪。H33>期限32的机制损失已用真实收费迁移用例报告，干净完整单元未出现该损失。

## 文件、证据与停止位置

实际改动10文件（1个既有核心文件数值钩子＋9个新文件，包括本关裁决）：

- [d2_prime/protocol.py](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/protocol.py>)
- [d2_prime/float32_protocol.py](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/d2_prime/float32_protocol.py>)
- [flgo_byzantine/formal_d2_prime_algorithm.py](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/formal_d2_prime_algorithm.py>)
- [scripts/run_d2_prime_formal.py](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/scripts/run_d2_prime_formal.py>)
- [scripts/summarize_d2_prime_formal.py](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/scripts/summarize_d2_prime_formal.py>)
- [scripts/verify_d2_prime_formal.py](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/scripts/verify_d2_prime_formal.py>)
- [tests/test_d2_prime_formal.py](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/tests/test_d2_prime_formal.py>)
- [docs/D2_PRIME_PHASE2_2_RULING.md](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_2_RULING.md>)
- [docs/D2_PRIME_PHASE2_2_3_REPORT.md](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_2_3_REPORT.md>)
- [docs/D2_PRIME_PHASE2_2_3_MANIFEST.json](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE2_2_3_MANIFEST.json>)

原始证据留在`outputs/d2_prime_phase2_2_3_20261009/`，配置/实际映射、88项测试日志与迁移证据、200任务smoke和唯一12,000任务full的任务/账目/事件/逐类曲线/延迟/最终模型，以及独立复核与评价工作量重建。各文件SHA256索引在清单，outputs不纳入提交。

源代码/配置没有训练中修订。测试启动前校正了固定混合源用例的到达时刻和proposal字典访问；无测试失败、smoke失败或完整训练重跑。旧0.7 seam、两条2.1入口、reference/budget、RFA相关实现与easyFL均未改动。登记沿用的`B_M_used_for_baseline_clipping`字段在当前D2单元中表示启用裁剪，不表示改动旧基线；清单明确披露该字段来源。

正式GPU中途恢复仍不支持，`final_model_only.pt`为最终模型产物。未做攻击、消融、Q/2Q、3.x或参数搜索。可学性硬门失败后停止；**没有git add、commit或push，commit hash：无（当前HEAD仍a3cda3f6）**。保留完整失败轨迹和未提交改动，等待确认。
