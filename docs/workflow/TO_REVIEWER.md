# 交付单：G1.3 A扫描守卫定点修复与人工回归

- 对应任务单的基准 commit：eaecc95a6fd0e096dd2ccfd3928c676dc6aa2a54（当前HEAD祖先）。
- 本次交付 commit：见本提交；派单授权审查6ae5cfafec16d719a33d86a7a2b6527075692009。

## 做了什么（≤5 条）
- 删除schema完整物化再截断入口；label_mapping和嵌套类/来源遍历、列表副本均事前reserve。
- 外层唯一累计账本通过RPC批准显式动作；语法、CPU、第二解释器及封存共用，Budget拒绝previous重置。
- 实际运行五类字面人工对象回归，独立访问计数证明拒绝发生在集合访问之前，手算1/3扫描与实际一致。
- 自动生成证据/哈希；末端固定点预留后写三文件，再独立逐字节/解析核对最终账与回执。
- 首验通过即停；原14组算术NOT_RUN，B/C关闭；本单通过不等于A或G1.3通过。

## 产出文件
- direction_a/g1_3_preparation.py：共用账本代理及受控提取接口，原科学函数公式不变。
- scripts/prepare_direction_a_g1_3.py：受监督语法/CPU和第二解释器探针。
- scripts/prepare_direction_a_g1_3_outer.ps1、scripts/prepare_direction_a_g1_3_seal.ps1：共享监督/封存，无同前缀新辅助文件。
- tests/test_direction_a_g1_3_preparation.py：五类人工守卫回归，仅由受限入口执行。
- docs/DIRECTION_A_G1_3_IMPLEMENTATION_SPEC_v1.md：守卫契约、操作表、计次及完整A缺项。
- artifacts/direction_a/phaseG1_3_A_guard_v1/{plan,selfchecks,resource_ledger,receipt,artifact_hashes,state_checkpoint,failure_fixture}.json：自动证据；fixture是预期注入，不是工程故障。

## 判据自评
| 判据编号 | 结果 PASS/FAIL | 证据位置 / 关键数字 |
|---|---|---|
|1|PASS|selfchecks：label访问1；拒绝label/类/嵌套来源访问均0；嵌套成功访问[1,1,1]，真实计算/梯度/事件/费用/注册seed均0。|
|2|PASS|selfchecks五类全PASS、syntax_status=PASS；第二解释器接续扫描11→12；原14组NOT_RUN。|
|3|PASS|plan冻结两轮+共享封存；resource_ledger各阶段未超额；receipt最终三文件独立回读及账目一致，外层成功输出。|
|4|PASS|resource_ledger.event_comparison及规范事件表：原3/3/0/0→更正2/0/0/0；修故障+0/1/0/0、首验+1/0/1/1，累计3/1/1/1；旧占额一次、原FAIL/null保留。|
|5|PASS|仅授权四既有代码、测试、新证据、规范和本交接；旧包/合同/候选/ROLE/STATE/任务单不改；A缺项及余额如下。|

## 实际资源消耗
- 新受限读46589 B、写15184 B、扫描27；round1=34337/1921 B/12，seal=12252/13263 B/15；round2未启动。
- 外层观测0.6431456秒；账本累计时间上界2.6099713秒含末端2秒风险占额，不当实际时间；Windows峰120815616 B、CPU已知代理67108864 B，CUDA初始化0。
- 旧80秒/各3145728 B/192扫描风险仅结转一次，旧首轮/封存已知成本和schema扫描null、guard FAIL单列，不追认历史合规。
- 启动准备有限阅读已知下界348173 B，已知命令时间见resource_ledger.preparation；后续编辑/交接/Git尾耗单列未知，总墙钟/总读写/物理及隐式I/O保持null；当前新增文件约58 KiB。
- 准备中一次路径通配符错误、一次未落地patch格式错误均无受限运行/科学结果，不计工程尝试或实现修订；启动记账未知登记一次，未当守卫再现。
- 全局上限6/6/6/6，当前工程/修订/语法/CPU=3/1/1/1，余额3/5/5/5；本单分配4/2/2/2，已用1/1/1/1，余3/1/1/1；无新增非预期异常。
- 新额度读/写/扫描尚余1001987/1033392 B/37；若后续获同单续接，round2仍15秒/各393216 B/24，所有封存共享余约7.981秒/249892 B读/248881 B写/1扫描，不能重领尾耗；本次不追加运行。

## 阻塞（没有写“无”）
无（本单范围内）。完整A仍缺元数据计数/尾类/四参考及二进制身份、14组数值/有理对照、真实误差及配对统计规范、可执行B操作/时间/副本/峰包络，交审决定下一步。

## 异议（没有写“无”）
无。

## 需要审查者裁决的问题（≤3 条，没有写“无”）
- 是否接受本次守卫局部修复；后续A须在未完成清单及现存余额下另派，不自动开放B/C。
- 中途外层被外部终止且仅剩未闭合checkpoint时，入口拒绝重新领尾耗；不能从缺损状态声称成本可恢复。
