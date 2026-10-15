# G1.1 正式工作量与事件绑定候选 v1

2026-10-15；状态：文档候选，待审查冻结；本文件不授权补测、正式事件或下游实验。
依据：G1.1裁决v1 §2.2/§三、检查点§G1.1、合同§四W01–W03/W07/E01–E04；合同以任务输入HEAD `15c0b3e182c107504359a72339de256a7480859f` 定位。

## 1. 输入身份及复用边界

以下均以 `commit:路径#字段` 定位；A=`artifacts/direction_a/`；只读既有元数据，不重算计数、样本指标或逐文件哈希。
|输入|锁定commit与路径/字段|沿用范围|
|---|---|---|
|0.2正式任务及裁决|`e3c3528722cd4c4f55f96b37182255a4ade961b8`；`docs/DIRECTION_A_0_2_ADJUDICATION_v1.md`；A下`phase0_2_v1/tasks/FedPCC-0.2-candidate-{CIFAR10,CIFAR100}-N20-v1/{info,data,counts,acceptance}.json`|两数据集、各20端；`counts.n_ic/N_c/a_ic/class_groups/tail_holding_clients`及原split、标签映射；不重新划分|
|G1.1 smoke及裁决|`54eb6e02f4630df82cfdeb1c352fd5e4520ea5be`；`docs/DIRECTION_A_G1_1_ADJUDICATION_v1.md`；A下`phaseG1_1_v1/`|注册ACK/身份、支持证明结构、外生计划/速度对应关系、事件token/覆盖与隔离结构可复用；旧5/2代理、8秒截止及旧r/p不升级正式值|
|G1.2完整交付|`d3a3bd712d6bb28283b59faff16e17e099debcb4`；A下`phaseG1_2_full_v1/{preregistration,measurements,W02_measurement,run_record,reference_acceptance}.json`|80消息、1356主梯度、220个G_c；资格采用输入HEAD中的`docs/DIRECTION_A_G1_2_ADJUDICATION_v2.md`，不误用旧pending字段|
|参考及普通训练来源|同一`d3a3bd7`；A下`backbone_preparation_v1/{manifest,task_binding,generation_config}.json`|模型/BN/head/变换及任务身份随manifest；`task_binding.{dataset}.groups_tail_source`与source_files定位原分组/计数|
四参考固定为 `A-backbone-CIFAR10-s2026101321-r0040-v1`、`A-backbone-CIFAR10-s2026101321-r0080-v1`、`A-backbone-CIFAR100-s2026101322-r0040-v1`、`A-backbone-CIFAR100-s2026101322-r0080-v1`；每点client_000–019。
原头/中/尾组：C10类ID 0–2/3–5/6–9；C100为0–32/33–65/66–99；每点正来源85/593，来源集合从原n_ic>0位置继承。
新增绑定须逐条记录task/reference/state/BN/transform身份、旧消息定位及工作量版本；不得用event-slot或相同client_id跨任务拼接。

## 2. W01–W03/W07单一候选

|字段|候选协议与频率|已测/缺测、来源及最小请求|
|---|---|---|
|W01|每个已派发端执行固定5步、batch64；sealed train内有放回均匀抽样；SGD momentum=.9、wd=.0005、nesterov=false，每邀请重置优化器；float32纯均值CE，train BN，原归一化无增强；r40阶段lr=.05、r80阶段lr=.01|协议来源`generation_config.training/model/BN/transforms`；原6400步仅为理想全返回准备，不能当正式端级计时；缺四点×20端同边界计时，申请M一次|
|W02扫描/类梯度|每次已派发尝试均在其冻结参考上完整本端train一次，不按完成与否减账；encode/head chunk128、eval float32纯sum CE，CPU float64类内累加/n_ic再转float32；不抽样|已测`W02_measurement.client_scans=80, encoded_positions=41838`（每点C10 11165、C100 9754）；`measurements.references[].clients[].cost_seconds.encode/main_head`逐端可复用|
|W02特征统计|与上述完整扫描同次、同参考/同train特征的L2范数统计；每次派发计一次；不额外冻结encoder|已测`clients[].feature_statistics`和`cost_seconds.statistics`；不把诊断统计解释为合成特征半径|
|W02消息准备|每次派发准备本端完整类梯度消息（含缺类/身份），超时/掉线也登记准备成本；实际有效上传与尝试准备分开|既有`clients[].message.bytes/payload_bytes/metadata_and_container_bytes`可复用；`message_save_read`混合I/O且可为计时分辨率下的0，独立准备耗时缺测，M只对旧80消息序列化计时|
|W03|两任务各20端bootstrap注册；ACK完成先于所有attempt，不受单次截止过滤；同任务原计数与ACK可引用，新增正式绑定另列|已测`registration_{dataset}.json`：C10上/下17100/3900 B、C100 45837/3920 B；合计70757 B；本地回环子计时约.0014552/.0019969秒；物理网络时延未测，不填0|
|W07|本次固定四参考分别做静态事件绑定；每个attempt绑定唯一reference；非空完成推进逻辑round，空完成只推进attempt；不更新参考|参考r40/r80是同一骨干run两位置，不是独立重复；本节点无校准点产出/重匹配/终点训练；后续候选校准仍取这四点各一次，G3另冻结与计费；200更新轮上限保留，不据此开放81–200轮训练|
端级b_ir候选（秒）=M测得的W01耗时 + 旧encode + 旧main_head + 旧statistics + M独立消息准备耗时；不含auxiliary_checks/independent_numpy/目标汇总/诊断存储，也不重复加message_save_read。
原参考下行、普通模型返回、梯度上传分栏登记字节；单机状态复制不是物理网络。当前候选不引入未测带宽时延，通信字节不丢弃；如需网络时长模型须另审机制。
旧W02整体encode/main_head/statistics/message_save_read约2.7171/4.3260/.08158/.8600秒；总30.499秒包含输入、独立核验、归档，不能摊成端工作量。

## 3. E01–E04及概率绑定

|字段|唯一候选（均待冻结）|
|---|---|
|E01邀请|每attempt从原20端均匀无放回抽8，计划先于在线过滤保存；q=8/20=2/5；不补邀、不因空返回多生成预定attempt|
|E02速度|逐任务原`phaseG1_1_v1/speed_assignments.json`：同一10×1、10×4无量纲速度乘子集合；random复用seed2026101305对应关系；tail_slow把原尾占比最高10端置4，tail_fast置1，并列按端ID；只改端与乘子对应，不重排原计数|
|E03时长|令B=max四点80个b_ir，L_ir=b_ir/B，D_ir=s_i L_ir J，J=1/4+(3/2)U；截止δ=16/5模拟单位，恰等于截止可返回；1模拟单位对应B秒的基准服务量，非程序墙钟|
|E03在线/掉线|各端各attempt独立U网格{0,…,2^53−1}/2^53；online当U_o<9/10，派发后dropout当U_d<1/20；U_j独立；在线且未掉线且D≤δ才有效返回|
|E04次数/版本|正式结构候选每参考×三场景固定32 attempts，共384生成；同数回放384；覆盖4生成+4回放、边界2，总778，硬上限800；每轨迹逻辑round≤32，实际模型更新0；未来动态训练仍最多200更新，attempt候选400/单run，未申请执行|
|外生种子|G1.1结构记录使用主种子S1；正式主比较候选S1=2026102300、S2=2026102400、S3=2026102500；每S的邀请/在线/掉线/抖动流分别PCG64(S+1/+2/+3/+4)，顺序client_000–019，按attempt先生成全20端值|
三主种子相互独立；同一种子跨方法、三场景、两数据集与两参考复用邀请及逐端外生U，映射独立于数据/得分；固定速度映射不再重抽。六个数据集×场景组合、四参考、20端均不能冒充三次研究重复。
冻结b用保存的正整数纳秒及既有计时数值的精确十进制有理数；任何缺失、负值、非有限值、B≤0或零分辨率无法界定时停止，不补零。只做一次成本采集，不按完成率、G1.3或G2收益选择B、δ或样本。
该映射假设串行单机基准服务量可乘独立设备因子/抖动，忽略排队与真实网络；已有W02计时含平台噪声，b仅是冻结模拟参数，不是物理完成率估计。B取全局最大只为预先保证支持，不按标签/收益调整速度边际。
定义q_i=P(计划邀请i)，r_ir=P(有效返回i|计划邀请i,task/reference/工作量/速度场景)，p_ir=q_i r_ir；r含未在线、掉线和超时失败，不使用仅派发后的成功率替代。
连续理想r=(9/10)(19/20) clip(((δ/(s_i L_ir))−1/4)/(3/2),0,1)；b>0时L≤1、s≤4，所以δ/(sL)≥4/5，r≥627/2000>0，p≥627/5000>0，覆盖原全部n_ic>0来源。
实际r用三个独立网格满足严格online/dropout边界、含等号deadline的基数乘积/M^3（M=2^53）；p再乘2/5，精确有理数为权威；连续差界|Δr|≤3/M、|Δp|≤(2/5)3/M，另报float64展示误差。
未来输出支持表须逐(task,reference,scenario,client,class)引用原n_ic位置和对应q/r/p，不复用旧代理r/p数值；有限零返回标观测不足，不判永久缺席。
验收键=(task,mechanism,seed,reference,attempt,round,client,token)：每返回唯一匹配原计划/派发、身份/载荷与deadline；拒绝错参考、未注册、重复token、迟到及篡改；计划数与有效返回分别做分母。
空返回仍写attempt终态、模拟δ及墙钟/成本账；round不增、下一attempt使用不同ID/token；不得丢弃重试历史。模拟各轨迹时间32δ与程序累计墙钟各报，不把模拟成本伪称实际执行的训练。
q可进邀请日志；真实r/p及未观测外生U仅在模拟/离线诊断侧，策略侧只取此前可观测历史；未来E05仍需G2.1独立审计。正式概率表不得进入派发/返回消息或预测特征。

## 4. 对照全部G1.1判据的验收清单

|判据|复用证据|新增证据及通过条件|
|---|---|---|
|全部目标端注册|旧registration.messages/registered_ids/ACK及source_file_sha256|正式binding索引覆盖两任务各20端，引用原计数及train_split_hash；bootstrap独立成本齐|
|全部正来源支持|旧support.nonzero_sources与计数位置、精确基数证明方法|四点×三场景全正来源无遗漏，b/B/δ及q/r/p分数可定位，解析正下界成立；不以经验率验支持|
|计划与有效完成对应|旧trace的身份/token与载荷检查结构|新绑定轨迹逐返回唯一链接且拒绝非法输入，task/reference/版本一致；生成与回放完全一致|
|空返回计日志与预算|旧coverage_trace两次空完成、重复round不同attempt|正式绑定覆盖夹具保留空终态、attempt收费及round不增；fixture单列，不当随机研究样本|
|同一速度集合|旧speed_assignments及尾占比排序|新绑定按原端映射核验三场景各10×1+10×4，边际相同，不按下游收益重排|
|固定工作量含新增计算|G1.2逐端encode/main_head/statistics与消息字节、普通训练协议|M补齐W01/消息准备；b逐项含量/频率/来源/成本，失败派发不免账，审查冻结后才可正式事件|
|真实概率可审计隔离|旧diagnostic_channel_audit及payload隔离结构|新binding与消费路径审计，实际策略无r/p/未来U；支持诊断与预测器输入边界单独留证|
|六类短轨迹|旧coverage_plan/trace及scalar_oracles|正式绑定下按时（含等号）、未派发、掉线、超时、全失败、重复round不同attempt均覆盖，回放一致|
|预登记与范围|旧mechanism/preregistration与裁决§2.2|新机制、工作量、外生计划和预算先登记；G1.1仅机制资格，后续3配对种子比较另授权/计账，不能用6场景抵3重复|

## 5. 最小补测M申请与停止规则

成本缺口：原准备没有四参考×20端统一计时边界的5步训练记录；旧message_save_read不能辨认纯准备成本。一次M即可补这两项；当前不需要新增类梯度、冻结编码或验证分数。
M候选为1程序/1次入口/失败重跑0：固定四点各20端，从各冻结state独立复制做5步后丢弃，不产生新参考/指标；训练采样PCG64(2026102600+100*参考序号+client)，参考序号0–3沿第1节；每端仅计一次，含冷启动不择优。
每端同步CUDA前后计W01（含模型复制/优化器初始化、5步及普通state返回序列化），记录纳秒/字节；另从旧梯度消息读入后独立序列化一次计准备（不混文件读写），记录分辨率。只保存最小计时/身份JSON，不保存新权重、特征或预测。
M额度候选：累计程序120秒（输入/准备≤30、W01≤60、序列化/保存/核验≤30），CUDA allocated峰1 GiB、Windows进程峰6 GiB、CPU数组张量代理2 GiB；累计写入16 MiB（含重复写与1 MiB失败状态预留），逻辑本机复制/消息准备512 MiB，真实网络不适用。
M操作上限：W01调用80、优化/反向各400、训练全网络前向400、训练样本使用25600（5×64×80，重复照计，含训练encoder）；新增冻结encoder编码0、类梯度请求0、W02全train扫描0、attempt0；元数据/消息/归档有名扫描≤512，初始化核验前向0；读取原train仅限上述抽样。
M依据：旧两任务训练6400步用41.437+35.405秒，本次400步按比例约4.803秒仅作粗估；原G1.2 80消息读写约.860秒、旧GPU训练峰≤320941056 B；当前跨参考重置、启动/CPU/进程峰未实测，上述120秒/内存/字节为工程预留，不伪称已测，也不从P余额转账。
M新增信息只用于成本，采得后封存，不凭耗时好坏重采。实现修订/语法/CPU套件各≤2（含首次，全部时间/写入累计）；真实入口≤1；有新增测量后异常立即封存，交下一单，不自动恢复；无结果修复亦不增加入口或资源。
正式事件F仅列后续候选、与M不同时启动：M验收和机制冻结后1入口、无训练/编码/梯度；程序300秒、CUDA0、进程2 GiB/CPU代理512 MiB、累计写入32 MiB、逻辑元数据8 MiB、含引用载荷总逻辑通信32 GiB、扫描≤2048、attempt≤800（计划778）；修订/语法/CPU各≤2，真实入口≤1。
F依据旧394 attempts用1.688秒、事件1098062 B、证据记账5262413 B按778放大；新绑定/概率记录额外预留；旧元数据中参考最大1304494 B、消息最大1929208 B，按≤800×8×(2×1304494+1929208)加元数据/注册低于32 GiB；普通state返回大小待M确认，超包络先交审。
F逐派发引用原消息/参考字节收费，不复制大包；完整逻辑账含参考下行/普通模型返回准备/梯度准备与有效上传，掉线/超时仍计计算和已发生复制，离线未派发不计端计算；回放/夹具/失败重复全部收费，物理发送量null。M/F合计候选420秒、48 MiB写入，历史G1.1/G1.2/P成本各原账保留；三研究种子运行不含本申请。
所有上限含失败、检查、归档和重复写；下一动作预估会超限即停；来源缺失/冲突、保护失效、非有限量、数据泄漏或需改总体/参考/机制均封存交审，不修门槛、不扩预算。大文件依ROLE进artifacts_local并由将来脚本自动生成索引/哈希。
当前正式冻结门禁：M尚无实测且未获运行授权，b/B不能填数；本草案已形成明确补测请求，可交审，不以此宣布正式G1.1通过。P双数据集全范围FAIL保留，不据此删C100或重选参考。
