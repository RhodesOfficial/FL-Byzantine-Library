# 交付单：P 可分性探针有界准备（启动失败）

- 对应任务单的基准 commit：298a3e8b22986691acf2ede893c0dee04b610881
- 本次交付 commit：见本提交

## 做了什么（≤5 条）
- 核对基准为当前HEAD祖先，读取STATE、任务单和G1.2裁决。
- 写入训练内部划分、均衡线性头、置乱标签及受限计账的实现和相关自检代码；未经运行验证。
- 一次启动在Python解析阶段失败，未执行模块语句、自检、特征读取或拟合；没有重跑。
- 自动保存启动失败、零拟合结果、自检未执行标记、成本记录和文件哈希。

## 产出文件
- direction_a/probe_preparation.py：训练内部划分、损失、指标与拟合代码，未验证。
- scripts/prepare_direction_a_probe.py：准备入口，527行缺少外层字典闭合，当前不可执行。
- tests/test_direction_a_probe_preparation.py：相关解析/前向自检，未执行。
- scripts/archive_direction_a_probe_startup_failure.ps1：仅归档已发生失败，不运行实验。
- artifacts/direction_a/phaseP_preparation_v1/startup_failure.txt：原启动错误、退出码与命令耗时。
- 同目录results.json、selfchecks.json、run_record.json、artifact_hashes.json：失败状态与机器可读记录。
- preregistration.json、split.json、24个最终头、threshold_basis.md和formal_plan.json未生成。

## 判据自评
| 判据编号 | 结果 PASS/FAIL | 证据位置 / 关键数字 |
|---|---|---|
|1|FAIL|results.json：未完成四参考/逐端train特征核验；没有新编码或正式评价，原状态未操作|
|2|FAIL|results.json：划分代码未运行，split.json未生成|
|3|FAIL|results.json：完成0/24头，没有实际置乱/拟合结果|
|4|FAIL|startup_failure.txt：解析失败；反向/优化器均0，目标记录和最终头缺失|
|5|FAIL|results.json：所有实测CE/recall/差值和分母缺失|
|6|FAIL|run_record.json、artifact_hashes.json：失败账本可定位，但完整头/峰值证据缺失|
|7|FAIL|threshold_basis.md、formal_plan.json缺失；未冻结τ_probe，未判断P可分性|

## 实际资源消耗
- 唯一准备启动命令耗时0.4250004秒（执行工具计时，含进程启动/退出）；归档时间、写入和归档进程峰值见run_record.json。
- 准备运行启动1次，失败重跑0，搜索0，实现修订2次，拟合/反向/优化器/头前向/新编码/通信/类梯度请求均0。
- Python准备进程的峰值显存/Windows working-set/CPU代理未测得，写null，不声称全部资源检查通过。
- 旧G1.2成本在results.json.reused_G1_2_costs单列，本轮未实际读取训练特征。

## 阻塞
- scripts/prepare_direction_a_probe.py:527存在括号闭合语法错误；模块解析失败导致预注册和运行尚未开始。
- 任务单禁止失败重跑，且实现修订2次额度已耗尽；停止修订/执行，不自行扩额。修复和重新执行须由审查者重新授权。

## 异议
无

## 需要审查者裁决的问题（≤3 条，没有写"无"）
- 是否为语法修复及重新启动另行授权实现修订/运行额度；现有失败记录和成本必须保留，不清零。
