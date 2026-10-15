# 交付单：P 正式第6轮空壳修复及保留160头续跑

- 对应任务单的基准 commit：7f481ec94a1a8a5256b4c361955f8d42cca5a6df
- 本次交付 commit：见本提交

## 做了什么（≤5 条）
- 最小v10恢复入口及3次合成CPU套件（末次31/31 PASS，前两次FAIL封存），v5科学算术完整复用；源码与预登记先提交。
- 旧160头只读复用；新完整头 240/240，第161头从零重做。
- 累计账本与实际检查结果已封存；四点联合推断是否完成见下表，旧6 GiB失败和未知保留。

## 产出文件
- artifacts/direction_a/phaseP_formal_resume_v5/：预登记、语法/CPU/输入检查、manifest、results/uncertainty、run_record/artifact_hashes。
- 完成运行时另产出 joint_index、heads/、head_results/、predictions/；本轮完成量见判据3。

## 判据自评
|判据编号|结果 PASS/FAIL|证据位置 / 关键数字|
|---|---|---|
|1|PASS|syntax_check.json / selfchecks.json；末次31项合成检查、3次套件成本及保护证据|
|2|PASS|input_checks.json；新encoder 24/24；新验证编码 3000/3000|
|3|PASS|resume_manifest / joint_index；新拟合 240/240；新反向/Adam 240000/240000|
|4|PASS|results / predictions；完整分母、机会、99训练置乱及CP|
|5|PASS|uncertainty；39996次全标签配对置乱、≥、加一p及四点调整|
|6|PASS|uncertainty / results；8000次类配对bootstrap、linear分位及目标诊断|
|7|PASS|run_record / artifact_hashes / old_preservation；终态 completed；旧峰失败保留|
|8|FAIL|四点固定科学判据，逐点见下表|

|参考|尾R %|Δ pp|可分性|校准空间|
|---|---:|---:|---|---|
|A-backbone-CIFAR10-s2026101321-r0040-v1|38.250000|38.250000|PASS|PASS|
|A-backbone-CIFAR10-s2026101321-r0080-v1|40.000000|40.000000|PASS|PASS|
|A-backbone-CIFAR100-s2026101322-r0040-v1|7.941176|7.941176|PASS|PASS|
|A-backbone-CIFAR100-s2026101322-r0080-v1|7.647059|7.647059|FAIL|FAIL|

## 实际资源消耗
- 旧正式562.063秒/8259455 B/166480扫描、失败v1 220.562秒/1537791 B/1407扫描、失败v2 661.719秒/1681119 B/2350扫描、失败v3 694.077秒/2356081 B/4585扫描、失败v4 687.516秒/3463904 B/4601扫描；v5保守1345.827000秒/38234729 B/301679扫描。
- 正式总账 4171.764000/9000秒、55533079/134217728 B；余量 4828.236000秒、78684649 B。
- 本轮CUDA峰137482752 B、Windows峰9445175296 B、CPU代理峰1505435128 B；跨阶段最大峰及缺项见run_record.joint_formal_accounting.resource_peaks。
- 准备74.9171745秒/11988355 B只继承一次；P累计 4246.681175秒/67521434 B；旧未知及旧判据6 FAIL保留。
- 新有效更新240000，完整头400/400；失败461次与CPU前向分列；重复编码及近似区间见证据。
- 自评FAIL 1条；完整性/工程资格与科学得分分开。

## 阻塞（没有写“无”）
无

## 异议（没有写“无”）
无

## 需要审查者裁决的问题（≤3 条，没有写“无”）
- 按v6联合工程资格及v5四点科学门槛裁决；P交付后由审查者接续原G1.1文档任务。
