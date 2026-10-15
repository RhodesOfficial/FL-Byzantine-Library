# 交付单：G1.1 成本补测M（单次有界采集）

- 对应任务单的基准 commit：e63a2ccde436335612a363567c56cce651bea8a8
- 本次交付 commit：见本提交
- 授权提交：ca391789a43cf1b3fc33cba6e14dae866fcf6e85
- 源码/预登记提交：096b468f58f42bfa3da28cef957b691fc628c530

## 做了什么（≤5 条）
- 实现独立参考复制的W01计时、旧消息纯准备计时及精确有理数汇总。
- 相关CPU合成检查通过；真实入口仅一次；完整/部分/未开始清单封存并读回。
- M结论仅交审，正式G1.1仍未通过，事件F未运行。

## 产出文件
- `direction_a/cost_m.py`、`scripts/measure_direction_a_cost_m.py`：实现及有界入口。
- `tests/test_direction_a_cost_m.py`：计时、累计门禁、异常留存及完整性夹具。
- `artifacts/direction_a/phaseG1_1_cost_M_v1/`：预登记、输入身份、80项清单、自检、运行账及哈希/封存回执。
- 同目录 `delivery_audit.json`：确定性复核、最终累计账及全部JSON哈希；`final_delivery.json`为前一快照。

## 判据自评
| 判据编号 | 结果 PASS/FAIL | 证据位置 / 关键数字 |
|---|---|---|
| 1 | PASS | selfchecks.json、preregistration.json、input_checks.json；入口1，修订2，语法/CPU各1 |
| 2 | PASS | run_record.json；{'backwards': 400, 'calls': 80, 'forwards': 400, 'samples': 25600, 'scans': 167, 'steps': 400, 'writes': 201747} |
| 3 | PASS | measurements.json、input_checks.json；逐项W01/保全/分辨率 |
| 4 | PASS | measurements.json；旧W02精确十进制及b/B/L，无message_save_read重复 |
| 5 | PASS | delivery_audit.json；含首次源码重写、外部程序及封存尾耗的保守累计上界 |
| 6 | PASS | seal_receipt.json；终态completed，清单{'complete': 80, 'not_started': 0, 'partial': 0} |

## 实际资源消耗
- 程序时间/写入/内存详见delivery_audit.json；W01 7.780565499993827秒；CUDA峰 164613120 B。
- 源码/文档/证据累计写入包含重复及本交付；物理网络不适用。

## 阻塞（没有写“无”）
- 无

## 异议（没有写“无”）
- 无

## 需要审查者裁决的问题（≤3 条，没有写“无”）
- M完整交付，请裁决补测验收；F仍待另派单。
