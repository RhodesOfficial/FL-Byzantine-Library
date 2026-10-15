# 交付单：P 正式第5轮保留160头续跑

> 现行预算补注（2026-10-15，合同及当前任务单已于722430c更新）：正式累计上限150分钟（9000秒），已记2825.937秒保留，余额6174.063秒。以下第5轮交付的7200秒上限及4374.063000秒余额为交付当时记录，原文与封存证据保留；本补注不增加运行消耗，不改变裁决、任务内容或其他边界。

- 对应任务单的基准 commit：56b3ac4a6466b9086fd28152002804c4bde84c7b
- 本次交付 commit：见本提交

## 做了什么（≤5 条）
- 最小v9恢复入口及一次合成CPU套件，v5科学算术完整复用；源码与预登记先提交。
- 旧160头只读复用；新完整头 0/240，第161头从零重做。
- 累计账本与实际检查结果已封存；四点联合推断是否完成见下表，旧6 GiB失败和未知保留。

## 产出文件
- artifacts/direction_a/phaseP_formal_resume_v4/：预登记、语法/CPU/输入检查、manifest、results/uncertainty、run_record/artifact_hashes。
- 完成运行时另产出 joint_index、heads/、head_results/、predictions/；本轮完成量见判据3。

## 判据自评
|判据编号|结果 PASS/FAIL|证据位置 / 关键数字|
|---|---|---|
|1|PASS|syntax_check.json / selfchecks.json；一次合成生产生命周期及保护检查|
|2|FAIL|input_checks.json；新encoder 8/24；新验证编码 1000/3000|
|3|FAIL|resume_manifest / joint_index；新拟合 0/240；新反向/Adam 0/0|
|4|FAIL|results / predictions；完整分母、机会、99训练置乱及CP|
|5|FAIL|uncertainty；39996次全标签配对置乱、≥、加一p及四点调整|
|6|FAIL|uncertainty / results；8000次类配对bootstrap、linear分位及目标诊断|
|7|FAIL|run_record / artifact_hashes / old_preservation；终态 failed_no_retry；旧峰失败保留|
|8|FAIL|四点固定科学判据，逐点见下表|

|参考|尾R %|Δ pp|可分性|校准空间|
|---|---:|---:|---|---|
|A-backbone-CIFAR10-s2026101321-r0040-v1|未完成|未完成|FAIL|FAIL|
|A-backbone-CIFAR10-s2026101321-r0080-v1|未完成|未完成|FAIL|FAIL|
|A-backbone-CIFAR100-s2026101322-r0040-v1|未完成|未完成|FAIL|FAIL|
|A-backbone-CIFAR100-s2026101322-r0080-v1|未完成|未完成|FAIL|FAIL|

## 实际资源消耗
- 旧正式562.063秒/8259455 B/166480扫描、失败v1 220.562秒/1537791 B/1407扫描、失败v2 661.719秒/1681119 B/2350扫描、失败v3 694.077秒/2356081 B/4585扫描；v4保守687.516000秒/3463904 B/4601扫描。
- 正式总账 2825.937000/7200秒、17298350/134217728 B；余量 4374.063000秒、116919378 B。
- 本轮CUDA峰70327808 B、Windows峰834269184 B、CPU代理峰515779452 B；跨阶段最大峰及缺项见run_record.joint_formal_accounting.resource_peaks。
- 准备74.9171745秒/11988355 B只继承一次；P累计 2900.854174秒/29286705 B；旧未知及旧判据6 FAIL保留。
- 新有效更新0，完整头160/400；失败461次与CPU前向分列；重复编码及近似区间见证据。
- 自评FAIL 7条；完整性/工程资格与科学得分分开。

## 阻塞（没有写“无”）
- KeyError: 'original_prediction'

## 异议（没有写“无”）
无

## 需要审查者裁决的问题（≤3 条，没有写“无”）
- 按v6联合工程资格及v5四点科学门槛裁决；P交付后由审查者接续原G1.1文档任务。
