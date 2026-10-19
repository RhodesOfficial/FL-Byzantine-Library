# 交付单：G1.3 D6 受限解码与真实梯度盲校准

- 对应任务单的基准 commit：`b14ee2b29db32e5cdfbd0e349359f25df7a9fc62`。
- 开工 HEAD / 本授权提交：`182e5e60556a020c52effb2e7eccfa071b45b980`；基准祖先核对退出0，开工工作区干净。
- 本次交付 commit：见本提交；未push，ROLE/合同/旧证据未改。

## 做了什么（≤5 条）
- 实现B专用owner、惰性描述符pickle VM、受限ZIP/storage解码；没有torch.load、模型读取或CUDA初始化。
- 在同一V1内完成37项新B自检、九份D/G身份绑定、80消息首遍解码及第二遍重新读/SHA。
- 四参考220类完成Q192盲测量；保留完整weight+bias、S、逐对距离/max/RMS/τ、固定全类/尾类分母与盲对照。
- 完成V1/S1落盘、哈希及回读；程序状态PASS只表示这些程序动作完成，不代表下表七条全通过。
- 交接核对发现前置通信界与分阶段计量缺口；已有新增指标，保全结果，不修改冻结源码或启动V2/独封补证。

## 产出文件
- `scripts/measure_direction_a_g1_3_blind.py`、`scripts/measure_direction_a_g1_3_blind_outer.ps1`：B实现及Windows Job owner。
- `tests/test_direction_a_g1_3_blind.py`：37项同周期自检，未重跑旧92套件。
- `artifacts/direction_a/phaseG1_3_B_d6_v1/V1/`：以下证据路径均相对此目录。
- `plan.json` / `blind_input.json`：六子账/动作图/寿命/源码SHA与白名单投影；整个A bundle未进入测量进程。
- `qualification.json` / `synthetic_acceptance.json`：实物身份与同周期合成；`blind_results.json`：盲区间和候选。
- `state_checkpoint.json` / `failure.json` / `resource_ledger.json` / `receipt.json` / `artifact_hashes.json` / `terminal_observation.json`：状态、原账、回读和退出观察。

## 判据自评
| 判据编号 | 结果 PASS/FAIL | 证据位置 / 关键数字 |
|---|---|---|
|1|FAIL|授权/历史隔离、Job继承及小型账户拒绝已核；但outer的ReadLineAsync/ReadToEndAsync先分配后检查帧长，尚非完整的事前通信allocator保护，不能以本次输出小追认全路径资格。|
|2|PASS|qualification：9元数据、四参考80消息两遍均PASS；FloatStorage/完整形状/来源类与分母/有限性检查，storage先核≤8MiB；checkpoint只核索引。|
|3|PASS|synthetic_acceptance：37/37；1290/12900两维Q192对独立Q256整数平方夹逼，含零/同源/单源/正负与最大对、近零不可辨、固定分母及非法/位宽拒绝。|
|4|PASS|blind_results：四参考220类完整；replacement用精确平方序与最大对恒等、共同正N*S及距离外包证明两符号关系；结构零逐坐标确认，macro分母10/100、4/34。|
|5|PASS|blind_input schema及ledger访问记录仅D/G、白名单消息/源码/投影；mean_tau及epsilon_bias_candidate供审查，epsilon_num区分p无关区间与z_*/p_*符号项，真实Ri/vi/η/连续投影保持null。|
|6|FAIL|逐输出双序列化/SHA/独立回读通过；但outer在V预扣8192B双端通信上界，覆盖了实际发生于S的通信，S未独立逐端计费；完整分阶段通信实耗仍null，原账不得调相或当完整计量。|
|7|PASS|首次完成即停，真实入口1；已完成B00–B05及S1，部分记录无；V2/S2/I/S3未启动。没有异常后重算、主事件/拟合/费用入口，完整G1.3未通过。|

## 实际资源消耗
- 工程/修订/语法/CPU：承接6/3/4/4，本轮增1/0/1/1，累计7/3/5/5；现上限9/6/6/6，余额2/3/1/1，本单未用分配2/2/1/1；没有运行后修订。
- B真实入口累计1/2；首个新指标：2026-10-19 15:28:11（北京时间），C10 r40 c0 source_norm，见checkpoint.first_result。
- scientific_results=1356按source_norm回调计数，表示新增结果已发生；不是τ/距离/所有科学对象的总数。
- owner最终输出观察15.5278977秒；terminal落盘前观察15.5224754秒；Windows Job观测峰266096640B，树硬限2147483648B。
- CPU寿命代理上界360489848B≤536870912B；代理实测峰、完整进程峰、物理/隐式I/O和最终退出尾耗均null；CUDA初始化0。
- V命名上界扣账：读126849193B/写164349B/扫描396386/操作8175536640；worker显式读观察126122608B（不含完整owner观察）。
- worker S最终扣账读写各927564B/扫描136/操作71108864，见terminal.worker.S；owner随后另预扣读32768B/写16384B/扫描16/操作100000及terminal双序列化/回读，不能把worker快照当整个S实耗。
- V/S均未观察到硬限触顶；上界扣账不冒充精确实耗；通信分阶段归属缺口按判据1/6保留，不宣称全部保护已合格。
- 当前证据文件合计758975B；源码76957B；本交接与Git开销另计，完整新增物理磁盘与峰null。
- 原4460秒块、D5已用1020秒风险及专属未用1150秒保留且不转给B；新970秒六子账不退款、不重领，历史FAIL/null不追认。
- 启动准备记账缺口登记一次：定向阅读命令观测见plan.preparation；交接核对两次命令另观测0.6998697/0.6445108秒，完整准备读写/墙钟/峰及Git尾耗null；此缺口不是第二次受限故障。
- 异常签名：运行failure.signature=null；交接发现静态缺口`IPC_PREALLOCATION_BOUND`、`IPC_PHASE_ATTRIBUTION`，没有第二次运行复现，不算同签名连续两次。

## 阻塞
- 判据1/6未齐，B交付不能声明七项全通过；已有真实指标后不自动重试，原程序PASS不覆盖这两个FAIL。
- ε候选：`blind_results.refs[*].mean_tau.{all,tail}`是精确Q192[lower_hex,width_hex]，上端=(lower+width)/2^192；candidate中的十进制仅展示，建议采用精确上端，等待审查冻结。
- 完整G1.3仍缺有限η、同seed事件耦合、连续投影及相关正分母/方向条件；真实Ri/vi与理想目标资格仍null，2e−6不是总误差。

## 异议
无。

## 需要审查者裁决的问题（≤3 条）
- 裁决通信事前界和S分阶段计量缺口的后续处理；保留本轮原账/身份与盲结果，不重新读取或重算。
- 独立审查本轮盲区间/精确平方对照证据及ε候选；不据此自动开放C/G2或裁决完整G1.3通过。
