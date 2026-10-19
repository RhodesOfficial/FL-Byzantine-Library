# 交付单：G1.3 D4原周期V2复验未完成

- 对应任务单基准：1055174751001e99c5ab6cb02bb62a6113d44a44。
- 开工HEAD：ba35578c9813009f3299734534be75496a5e1461；基准为其祖先（Git检查退出0）。
- 本次交付commit：见本提交；不push。

## 做了什么（≤5条）
- 针对V1的POST_RUN_AUDIT进行一次修订：独立端点oracle、四误差/传播、逐调用事件记录。
- 修正V2独立900秒截止、owner冻结租额/结算、精确授权的V1 PASS续接及小字节注入finally。
- 运行唯一预留V2（指定E:\anaconda3\python.exe）；语法通过，CPU在第37调用失败。
- 保留V2四文件及同次运行源码；S2封存再遇计数字符串拼接，未伪补缺失文件。
- 保留V1九文件、旧账/真实头与220行B工作表；覆盖本交接并更新实现规范。

## 产出文件
- artifacts/direction_a/phaseG1_3_A_d4_v1/V2/：plan、authorization、carry、bundle，共218558 B。
- direction_a/g1_3_preparation.py、scripts/prepare_direction_a_g1_3.py：内核/误差和受限运行器。
- scripts/prepare_direction_a_g1_3_outer.ps1、prepare_direction_a_g1_3_seal.ps1及tests/test_direction_a_g1_3_preparation.py：保护、封存、独立oracle。
- docs/DIRECTION_A_G1_3_IMPLEMENTATION_SPEC_v1.md：保留V1历史，逐缺口映射、独立依据、部分/未开始、原A与B缺项。

## 判据自评
|编号|PASS/FAIL|证据/关键数字|
|---|---|---|
|1|FAIL|plan.counts_before=4/1/2/2，精确V1授权/4引导Git身份、carry_once=1已承接；V2最终累计ledger/receipt未闭合。|
|2|PASS|bundle：15白名单327534 B、4绑定、20端/标签/split/尾4和34/80消息索引；真实路径已改正，binary_qualification=NOT_RUN。|
|3|FAIL|37调用=36 PASS+1 NOT_COMPLETED；其余55未运行（含12900全46）；末尾位宽见证未执行，不能称92条通过。|
|4|FAIL|第13组有理误差传播已测；首个S3的E_I独立界断言失败，后续配对/八项未验证；连续/真实ε仍null。|
|5|FAIL|独立截止、租额拒绝、小字节finally路径已执行；主子失败使第二子未启，S2/receipt不完整，保护全判据证据不足。|
|6|FAIL|owner冻结租额及单次结算已实现；总实际扫描仍null；S2继承字符串计数发生拼接并拒绝封存，缺5个必需证据文件。|
|7|PASS|旧包/真实头保持，220行B表，科学计数全0；本交接明确动作与验收，A/B/C门禁保持，不启动V3/I/S3。|

## 异常签名与计次
- 触发本轮修订：1055174的V1/bundle、旧源码及本任务逐条裁决中的POST_RUN_AUDIT，合一轮问题。
- V2首次异常：AssertionError / 1290/14/S3/E_I_independent_endpoint_budget / False vs True，见bundle.failures。
- 同轮finally异常：outer/S2 / quota before access S2/read；前驱未用S2的字符串计数被+=拼接。
- 静态分析：E_I的Q192向外下端直接与2^-256 oracle下界比较，未容纳向外舍入；未经复验，不声称已证修复。
- 上述两个签名发生于同一轮；没有第二次同签名实际尝试，无新增科学结果。
- 累计工程/修订/语法/CPU：4/1/2/2→5/2/3/3，增量1/1/1/1；全局上限各6，余额1/4/3/3。
- 原冻结两验证槽已用尽，剩余工程1仅条件性独封；S2完整累计不可核，I/S3条件不成立，保持NOT_RUN。

## 实际资源消耗
- 外层失败输出：V2=4.1817488秒/979727 B读/739809 B写/4083扫描扣账；命令外层观测4.7335112秒。
- V1/S1原读1208686/写796156/8959扫描保留；加V2已记为2188413读/1535965写/13042扫描。
- S2至少成功读bundle214680 B，总已知读下界2403093 B；完整S2读写/扫描/秒及终端尾耗null。
- S2输出read=000…21468000、scans=000…12884是拼接污染，不是实际21 MB读取；下一写动作前被拒，未证明实际硬限触顶。
- V2四文件218558 B；failure/checkpoint/ledger/receipt/manifest未生成，不能补造来源、哈希或闭合PASS。
- 本轮峰null；硬限Job进程树2 GiB/CPU代理256 MiB/CUDA0；物理/隐式I/O、平台完成证明仍null。
- V2/S2本轮冻结1020秒/16777216读/8388608写/80384扫描；使用事实保留，差额不回收；S2整块隔离。
- I/S3原预留130秒/8912896读/4194304写/16396扫描未使用；旧120秒块/风险/FAIL/null不变。
- 准备：10次有限读取/Git命令观测约7.055秒，非全墙钟；其中源码长度已知下界88558 B、bundle两次读取429360 B，另规则/文档/Git读。
- 准备/人工累计、全量I/O、编辑与提交尾耗、历史峰均null；未把未知补0或重领一工作日；不存在独立预检/CPU/封存程序启动。

## 阻塞
- V2验证槽耗尽且S2封存未闭合；前驱完整累计不可核，不满足I/S3启动条件，需审查者核查后续处置。

## 异议
- 无。

## 需要审查者裁决的问题（≤3条）
- 核查最后复验失败、S2计数污染及不完整证据包；不得把现有程序记录视为92项独立通过或科学假设失败。
