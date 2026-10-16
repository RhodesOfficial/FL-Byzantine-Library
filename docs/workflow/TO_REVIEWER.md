# 交付单：G1.3 A段部分封存（工程守卫缺口）

- 对应任务单的基准 commit：88b302a2c780c4482664610205ee5d7ff92f8580（当前HEAD的祖先，返回码0）。
- 本次交付 commit：见本提交；开工HEAD：ff31cff30713c50953656bf4ec9cbb79ea5b4d42。

## 做了什么（≤5 条）
- 初稿实现A专用算术、显式I/O预留及外层累计限时/峰监控；尚未经语法专项或CPU套件验证，不作为可用计算包交付。
- 先stat冻结15份元数据白名单，首次正文327534 B；受限入口只作schema定位，未加载二进制或计算真实p。
- 首次检查后发现schema对字典完整物化没有事先预留扫描，含D的label_mapping类集合；按停止条件封存，没有修复重跑。
- 失败封存脚本产出缺项、B阻塞包络和新文件哈希；独立落盘回读账本一致，不能据此证明原执行合规。
- B/C仍关闭；本轮没有新增科学结果，不能据此判来源偏差假设失败。

## 产出文件
- direction_a/g1_3_preparation.py、scripts/prepare_direction_a_g1_3.py：未验收初稿，默认拒绝未监督启动及B/C。
- scripts/prepare_direction_a_g1_3_outer.ps1：解释器启动前外层计时与进程树终止；prepare_direction_a_g1_3_seal.ps1：失败封存。
- artifacts/direction_a/phaseG1_3_A_v1/：六项指定JSON及failure、outer_receipt、seal_receipt、workflow_adjustment。
- tests/test_direction_a_g1_3_preparation.py、docs/DIRECTION_A_G1_3_IMPLEMENTATION_SPEC_v1.md未产生，停止后没有补造完成记录。

## 判据自评
| 判据编号 | 结果 PASS/FAIL | 证据位置 / 关键数字 |
|---|---|---|
|1|FAIL|input_index.json有15份路径/commit/schema；M定位measurements.json#rows[].b_seconds/L、B_seconds；计数/尾类与四参考逐项身份核对未完成，未重验二进制；真实p/梯度/事件/费用计算均0。|
|2|FAIL|算术初稿未验证，唯一实现规范及真实数据误差闭合需求未完整落实。|
|3|FAIL|selfchecks.json=NOT_RUN；所有14类预定边界及独立有理对照均未执行；正式注册seed轨迹0。|
|4|FAIL|failure.json记MetadataTraversalGuardGap，首次出现1次；schema扫描未预留，实际扫描总数null，不能主张未超限；封存回读成功不抵销此FAIL。|
|5|FAIL|next_stage_envelope.json仅保留最小盲测量提案及明确缺项，分阶段读写/操作/临时副本/时间/峰包络均未完成，null不替代上界。|
|6|PASS|仅新增本单A文件和本交接；旧证据/原候选/合同/ROLE/STATE/任务单未改，B/C及真实入口0。|

## 实际资源消耗
- 首次Python显式读327534 B、写42032 B、文件读取扫描15；完整schema遍历缺账null；Python内测约0.015秒、外层累计0.4005749秒，非全工作流墙钟。
- 首次Windows进程峰24158208 B，CUDA初始化0；内存代理为预留而非实测峰，物理/解释器隐式I/O/历史峰均null。
- 失败封存实测0.2895423秒、显式读86427 B、读扫描15；写20969 B含末端8192 B预留，非全部实写值；seal_receipt.json列逐动作及新峰。
- 正向实现计次保守更正为工程/修订/语法/CPU=3/3/0/0：初稿、封存辅助初稿、封存运行前更正各1；原resource_ledger写2/2，workflow_adjustment.json追加差额，原账保留。
- 全局上限各6，余额3/3/6/6；本单6/3/2/2，余3/0/2/2；真实入口0，旧D3/F/P成本/FAIL/null在resource_ledger.historical_once原样一次引用。
- 有限启动准备和交接/Git另账，已知命令耗时列resource_ledger.preparation；全墙钟及完整逻辑读写null；新产物大小由文件系统可查，非累计写入实耗。

## 阻塞（没有写“无”）
- 已发生受限扫描守卫缺口，触发本轮封存；A未完成，B/C不可开启。本单修订分配已耗尽，未自行借用全局余额或扩额。

## 异议（没有写“无”）
无。

## 需要审查者裁决的问题（≤3 条，没有写“无”）
- 接收部分封存并裁定下一单范围；若继续同一工程任务，保留3/3/0/0及全部历史成本，先覆盖schema遍历与首次验证完整修复周期，再重新分配现有余额。
