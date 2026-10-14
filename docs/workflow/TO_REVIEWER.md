# 交付单：P 正式第3轮保留160头续跑

- 对应任务单的基准 commit：10e0b657d616983d41de081863a97bf8332534d5
- 本次交付 commit：见本提交

## 做了什么（≤5 条）
- 最小v7恢复入口及一次合成CPU套件，v5科学算术完整复用；源码与预登记先提交。
- 旧包校验在共享源码历史哈希处停止；旧160头未完成本轮资格核验，新头0/240，第161头未启动。
- 保留失败终态，分列原正式、失败v1、新v2与准备账本；四点联合推断未完成。

## 产出文件
- artifacts/direction_a/phaseP_formal_resume_v2/：恢复源码预登记、语法/CPU/输入检查、计划manifest、失败results/uncertainty、run_record/artifact_hashes。
- startup_failure.txt：历史models/ResNet.py哈希不符的异常；没有新增heads/predictions或联合索引。

## 判据自评
|判据编号|结果 PASS/FAIL|证据位置 / 关键数字|
|---|---|---|
|1|PASS|syntax_check.json / selfchecks.json；24/24 PASS，大归档实际182526 B>131072 B|
|2|FAIL|input_checks.json；新encoder 0/24；新验证编码 0/3000|
|3|FAIL|resume_manifest仅计划队列；joint_index未产出；新拟合0/240、反向/Adam 0/0|
|4|FAIL|results.references为空；未完成四点指标/训练置乱汇总|
|5|FAIL|uncertainty；验证置乱0/39996，未产生调整p|
|6|FAIL|uncertainty / results；bootstrap 0/8000，联合目标诊断未完成|
|7|FAIL|run_record / artifact_hashes；old_preservation未产出；终态 failed_no_retry；旧峰失败保留|
|8|FAIL|四点固定科学判据，逐点见下表|

|参考|尾R %|Δ pp|可分性|校准空间|
|---|---:|---:|---|---|
|A-backbone-CIFAR10-s2026101321-r0040-v1|未完成|未完成|FAIL|FAIL|
|A-backbone-CIFAR10-s2026101321-r0080-v1|未完成|未完成|FAIL|FAIL|
|A-backbone-CIFAR100-s2026101322-r0040-v1|未完成|未完成|FAIL|FAIL|
|A-backbone-CIFAR100-s2026101322-r0080-v1|未完成|未完成|FAIL|FAIL|

## 实际资源消耗
- 旧正式562.063秒/8259455 B/166480扫描、失败v1 220.562秒/1537791 B/1407扫描；v2保守661.719000秒/1681119 B/2350扫描。
- 正式总账 1444.344000/4380秒、11478365/134217728 B；余量 2935.656000秒、122739363 B。
- 本轮CUDA峰0 B、Windows峰414269440 B、CPU代理峰1924328 B；跨阶段最大峰及缺项见run_record.joint_formal_accounting.resource_peaks。
- 准备74.9171745秒/11988355 B只继承一次；P累计 1519.261175秒/23466720 B；旧未知及旧判据6 FAIL保留。
- 新有效更新0，完整头160/400；失败461次与CPU前向分列；重复编码及近似区间见证据。
- 自评FAIL 7条；完整性/工程资格与科学得分分开。

## 阻塞（没有写“无”）
- RuntimeError: historical artifact mismatch: models/ResNet.py

## 异议（没有写“无”）
无

## 需要审查者裁决的问题（≤3 条，没有写“无”）
- 请裁决共享源码的历史字节/commit定位不符；唯一真实续跑已使用，不自动修复或重试。
