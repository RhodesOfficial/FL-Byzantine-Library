# 交付单：G1.3 D5有界恢复与完整合成首验

- 对应任务单的基准 commit：451476e68a77481ce8307dc67d51b665a65f1795
- 开工及授权 commit：0af98abd746a71530efc1eb644ac963183c66b60；基准祖先检查退出0。
- 本次交付 commit：见本提交。

## 做了什么（≤5 条）
- 修复独立E_I包含/32q验收；保留radius及其他S3独立预期，不改科学内核。
- 严格BigInteger→Int64账户解析及先判剩余的正常/末端加法，D20仅为输出快照。
- 落实D5新账、旧2290秒整块隔离、完整周期与失败尾额；只运行V1及自身S1。
- 首验完整92调用、原保护接口、固定15输入/220行表回归及独立封存回读通过；首次成功即停。
- 原V1/V2及缺口保留，追加实现规范，不推进B/C或下一节点。

## 产出文件
- tests/test_direction_a_g1_3_preparation.py：独立整数/有理平方夹逼、J_T及固定32q双端断言。
- scripts/prepare_direction_a_g1_3_outer.ps1、scripts/prepare_direction_a_g1_3.py：账户/入口、保护、独立验收及封存适配。
- artifacts/direction_a/phaseG1_3_A_d5_v1/V1/：本次全部机器证据；下表路径均相对此目录。
- docs/DIRECTION_A_G1_3_IMPLEMENTATION_SPEC_v1.md：旧段之后追加D5实现、动作界、成本和运行定位。

## 判据自评
| 判据编号 | 结果 PASS/FAIL | 证据位置 / 关键数字 |
|---|---|---|
| 1 授权与承接 | PASS | plan/authorization/carry/ledger：精确0af98ab，5/2/3/3→6/3/4/4，旧块隔离一次；旧null不转新实耗。 |
| 2 独立数值与完整套件 | PASS | bundle/independent_acceptance：两维各46、14组共92 PASS；独立J宽≤2^-262、Q192半格半径、J_T包含与32q双端界、原精度见证齐全。 |
| 3 类型与算术接口 | PASS | receipt.changed_interfaces.account_types：零串→214680、17串→214697、合法JSON整数；23种预期拒绝零访问，运行Int64，重复预留/结算只扣一次。 |
| 4 前置保护与回归 | PASS | plan.d5_action_bounds、receipt：先装900秒/Job/完整失败预留；两子继承、预算/IPC/租额拒绝和小字节finally实际验证；模拟拒绝非故障。 |
| 5 封存与计量 | PASS | ledger/receipt/manifest及terminal_observation：独立回读核对账户、总额、来源及SHA256；failure为空，checkpoint齐全；末端观察与null余耗边界分明。 |
| 6 范围保全 | PASS | independent_acceptance.fixed_input_regression、bundle.counters、carry.inventory：旧15输入/绑定/220行语义相等，真实入口与新增科学结果计数均0；旧证据未改。 |

## 实际资源消耗
- 新V1：31.0033934秒、1505477 B读/822408 B写/20657扫描扣账。
- 新S1：325823 B读/40937 B写/4450扫描扣账；ledger末端前0.1788721秒，末端观察0.3757451秒。
- 新合计：1831300 B读/863345 B写/25107扫描；最后观察31.3796794秒，观察自身写读及退出余耗null；120秒S硬限保持。
- 新增证据磁盘：11文件共330331 B（最终逻辑大小，独立于累计写入）；plan.bootstrap_scans=12为旧A00基线，D5实际引导5130扫描由新增16384分配承担，见规范及ledger.actions。
- Windows树工作集观测峰271511552 B；kernel已知CPU代理59973632 B，CUDA0；108 IPC帧/双端1066024 B，kernel操作上界扣账452551866。
- 旧账单列：2290秒/46661632读/25165824写/177420扫描整块隔离；旧读下界2403093、已记写1535965/扫描13042，旧S2全量/尾耗/峰null，原FAIL保持。
- 计次：本单增工程/修订/语法/CPU=1/1/1/1，现6/3/4/4；上限8/6/6/6、本单分配3/2/2/2；未启V2/S2/I/S3，无独立预检/额外套件。
- 本次实际失败签名为空；23种拒绝及INJECTED_SMALL_BYTE_FAULT为预期路径；旧E_I/S2签名保留，本轮未复现。
- 真实概率/模型/梯度二进制/拟合/指标/事件/费用均0；只使用人工合成及旧固定元数据，非正式偏差结果。
- 精确总扫描/基本操作、物理/隐式I/O仍null；观察文件SHA256由原脚本stdout生成：c6eee16a3091c6bd771543de312d9f52a396508bb3f54f98fba0dcc4244749da。
- 准备另账：九条有限读取/Git/交接命令观测6.4134694秒，源码已知读下界56269 B；完整准备读写/人工/隐式I/O及后续编辑/Git尾耗null，记账缺口登记一次，不判实际超限或保护失效。

## 阻塞
无。本单局部FAIL=0；原完整A仍1–5 FAIL、6 PASS，真实R_i/v_i、连续投影/真实ε及平台/二进制资格仍缺，不宣称完整A/G1.3通过。

## 异议
无。

## 需要审查者裁决的问题（≤3 条，没有写“无”）
无；按本单六项局部验收复核，后续任务另行派发。
