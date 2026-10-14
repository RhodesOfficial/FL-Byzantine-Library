# 交付单：P 准备v2启动失败

- 对应任务单的基准 commit：d7706748e70f63885572aded57fab9e674d1a086
- 本次交付 commit：见本提交

## 做了什么（≤5 条）
- 纯语法检查后一次恢复启动失败，无再次启动。
## 产出文件
- phaseP_preparation_v2/run_record.json、results.json、startup_failure.txt：外层失败捕获。
## 判据自评
|判据编号|结果 PASS/FAIL|证据|
|---|---|---|
|1|FAIL|启动失败，未完成|
|2|FAIL|启动失败，未完成|
|3|FAIL|启动失败，未完成|
|4|FAIL|启动失败，未完成|
|5|FAIL|启动失败，未完成|
|6|FAIL|启动失败，未完成|
|7|FAIL|启动失败，未完成|

## 实际资源消耗
- 自动账本见run_record.json；v1历史保留。
## 阻塞
Traceback (most recent call last):
  File "E:\Federated Machine Learning\FL-Byzantine-Library-astra\scripts\recover_direction_a_probe.py", line 240, in run_once
    budget, results, criteria = namespace["main"]()
                                ^^^^^^^^^^^^^^^^^^^
  File "E:\Federated Machine Learning\FL-Byzantine-Library-astra\scripts\prepare_direction_a_probe.py", line 421, in main
    budget = RecoveryBudget(RECOVERY_CONTEXT)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "E:\Federated Machine Learning\FL-Byzantine-Library-astra\scripts\prepare_direction_a_probe.py", line 64, in __init__
    super().__init__(OUTPUT / "run_record.json", LIMITS, STARTED)
  File "E:\Federated Machine Learning\FL-Byzantine-Library-astra\direction_a\class_gradient_full.py", line 16, in __init__
    super().__init__(path, limits)
  File "E:\Federated Machine Learning\FL-Byzantine-Library-astra\direction_a\backbone_preparation.py", line 58, in __init__
    self.save()
  File "E:\Federated Machine Learning\FL-Byzantine-Library-astra\direction_a\backbone_preparation.py", line 82, in save
    raw = encode(self.snapshot(now))
                 ^^^^^^^^^^^^^^^^^^
  File "E:\Federated Machine Learning\FL-Byzantine-Library-astra\scripts\prepare_direction_a_probe.py", line 90, in snapshot
    cumulative_implementation_revisions=history["implementation_revisions"]+value["counts"]["implementation_revisions"],
                                                                            ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
KeyError: 'implementation_revisions'

## 异议
无
## 需要审查者裁决的问题
- 重新执行须另行授权。
