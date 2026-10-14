# 交付单：P准备第3轮 启动链路修复与CPU隔离回归

- 对应任务单的基准 commit：aa5f6d00535a339ad2753aded515dff20fa70925
- 本次交付 commit：见本提交

## 做了什么（≤5 条）
- P专用真实RecoveryBudget延后派生snapshot，完成完整父类构造后显式继承计数/成本。
- 包装器复用可注入回归的启动/异常/归档生命周期，保护封存失败目录和已有标记。
- 累计2次纯语法检查、2次CPU套件；最终12用例；首轮临时目录权限失败及成本保留。
- 按commit审计两轮失败历史，保留旧未知项；24头仍未执行，原七条准备判据仍FAIL。

## 产出文件
- direction_a/probe_startup.py及两入口：P专用构造/继承、保护和终态记录。
- tests/test_direction_a_probe_startup.py、scripts/check_direction_a_probe_startup.py：隔离回归与有界执行/审计。
- artifacts/direction_a/phaseP_startup_repair_v1/regression_results.json：实际命令/源哈希/逐用例结果/隔离证据。
- 同目录accounting_audit.json：v1/v2提交、累计值、恢复写入/时间/扫描界及未知项。
- 同目录run_record.json、artifact_hashes.json：新增真实消耗、临时写入、累计可核算值、归档索引。

## 判据自评
|判据编号|结果 PASS/FAIL|证据/关键数字|
|---|---|---|
|1|PASS|真实FullBudget/PreparationBudget构造、pending/final snapshot、保存读回与精确写入/修订/扫描继承用例|
|2|PASS|合成时钟/请求触顶后失败账本；已有标记/账本及封存目录拒绝且不覆盖用例|
|3|PASS|包装器budget前/后注入异常与正常归档；终态/错误/哈希读回/无自动重试；计时覆盖归档并校验写出预留|
|4|PASS|accounting_audit.json：继承4.9019854秒/500678 B、2启动/1重启/4修订；v2不重复加v1，旧判据6仍FAIL|
|5|PASS|regression_results.json、run_record.json：语法/用例与真实资源；CUDA和实验调用拦截，操作0|

## 实际资源消耗
- 精确新增/累计时间、Windows峰、CPU字节缓冲代理、扫描和全部覆盖/临时写入见run_record.json。
- 新增修订2；语法2/套件2；准备启动仍2/失败重启仍1；真实实验操作0。
- 历史CUDA/CPU代理和终末峰/精确扫描缺项保留未知，不扩大v1豁免或宣称全历史合规。

## 阻塞
无

## 异议
无

## 需要审查者裁决的问题（≤3 条，没有写"无"）
- 是否另行放行后续准备运行；本修复通过不替代原七条准备或P科学验收。
