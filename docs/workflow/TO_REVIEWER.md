# 交付单：P 可分性探针有界准备

- 对应任务单的基准 commit：2f7b638550c1b986b7fa2ffd3eabcd191e956cc8
- 本次交付 commit：见本提交

## 做了什么（≤5 条）
- 锁定已通过G1.2训练缓存/原参考头；按类内部划分、全局置乱和固定200步执行。
- 完成24/24个头；自检与存储读回均在同一次受限运行。
- 提交描述性门槛依据及正式方案申请；τ_probe未冻结，未运行正式P验证。

## 产出文件
- artifacts/direction_a/phaseP_preparation_v3/preregistration.json、split.json：输入及划分/置乱锁定。
- 同目录results.json、heads/：目标下降、所有对照、逐类CE/recall及分母。
- 同目录syntax_check.json、selfchecks.json、run_record.json、artifact_hashes.json：实际语法/相关检查、累计成本及自动哈希索引。
- 同目录threshold_basis.md、formal_plan.json：描述性零范围/离散性与未放行的正式预算。
- direction_a/probe_preparation.py、scripts/prepare_direction_a_probe.py、tests/test_direction_a_probe_preparation.py：实现及相关测试。

## 判据自评
| 判据编号 | 结果 PASS/FAIL | 证据位置 / 关键数字 |
|---|---|---|
|1|PASS|startup_regression.json：生产run_once真实构造、构造前/后异常、归档异常、正常资源峰及终末触顶/防覆盖|
|2|PASS|syntax_check.json、selfchecks.json、results.json.input_checks：语法/自检通过，G1.2缓存哈希、20端索引/标签频数、参考状态；新编码/正式评价0|
|3|PASS|split.json：每类拟合≥2/校准≥1，互斥并集=原train，同数据集两点完全相同|
|4|PASS|split.json.label_permutations、results.json：四点各1真+5置乱，频数守恒、校准真标签不变|
|5|PASS|heads/、results.json：完整C维/bias零初始化，Adam固定200步，0/50/100/200目标及有限性|
|6|PASS|results.json：逐类/全类/头中尾CE/recall/分母、解析机会、所有差值用pp；零值保留|
|7|PASS|run_record.json、artifact_hashes.json：全部头定位/读回/哈希；b702a84修复账本按commit继承、未知峰值/旧覆盖写入保留，有限豁免不追溯PASS|
|8|PASS|threshold_basis.md、formal_plan.json：未冻结门槛；5置乱只描述，优化与表征信息分开|
- A-backbone-CIFAR10-s2026101321-r0040-v1：内部尾recall=35.639566%，原头=0.000000%；100→200目标相对下降=0.055755（非科学裁决）。
- A-backbone-CIFAR10-s2026101321-r0080-v1：内部尾recall=29.918699%，原头=0.000000%；100→200目标相对下降=0.048119（非科学裁决）。
- A-backbone-CIFAR100-s2026101322-r0040-v1：内部尾recall=4.656863%，原头=0.000000%；100→200目标相对下降=0.169982（非科学裁决）。
- A-backbone-CIFAR100-s2026101322-r0080-v1：内部尾recall=4.656863%，原头=0.000000%；100→200目标相对下降=0.181643（非科学裁决）。

## 实际资源消耗
- 新阶段程序及预检包络上界59.078秒；P累计保守上界74.917秒（含20秒预检工具包络和终末预留）。
- CUDA峰81744384 B；Windows峰1320845312 B；CPU代理峰807983952 B。
- 最终核验archive_verification.json；修订3/累计9，语法3、CPU套件2（最终20例全PASS）；首次测试参数缺项已封存。
- 新增/累计写入、全部覆盖及临时文件成本见run_record.json；封存历史未知项仍保留。
- 拟合24次；反向/优化器4800/4800；新增encoder/编码/通信/类梯度请求均0。
- 原G1.2成本与80端训练缓存生成费用见results.json.reused_costs，不计作本轮新编码。
- b702a84修复账本累计14.4303879秒/1159812 B/修订6；保守时间上界15.8391745秒/扫描286继承，未知保留，旧判据6仍FAIL。

## 阻塞
无

## 异议
无

## 需要审查者裁决的问题（≤3 条，没有写"无"）
- 正式P的τ_probe、最低改善量、重复/不确定性程序与formal_plan.json预算须冻结后另行放行。
