# 交付单：G1.1 正式事件F v1（输入工程阻塞）

- 对应任务单基准：`22c7418d40f62c81f2639e86d1b7a166a6898920`。
- 授权：`bbe939a2d8cf6ea14c7dfd18f96e24821a52ed3d`；源码预登记：`f8a00f23456fe5cd461aee8789e05fbb27d999f6`；交付：见本提交。

## 做了什么（≤5条）
- 实现有理数机制、元数据绑定、事件消费者、回放及资源保护；两轮语法/CPU套件通过，每轮4项。
- 源码和预登记先提交，唯一真实入口在C10速度映射类型检查处停止；新增事件0，未训练或初始化CUDA。
- 保全输入核对及异常、778项未开始清单和最终资源账；没有恢复、重抽或修改冻结映射。

## 产出文件
- `artifacts/direction_a/phaseG1_1_formal_F_v1/`：preregistration、selfchecks、preparation_history_v1、preparation_ledger、entry。
- 同目录failure、run_record、artifact_hashes、seal_receipt、delivery_audit：部分核对、异常、清单、哈希及尾耗。
- `direction_a/formal_f.py`、`direction_a/formal_f_policy.py`、`scripts/run_direction_a_formal_f.py`、`tests/test_direction_a_formal_f.py`。

## 判据自评
|判据编号|结果 PASS/FAIL|证据位置 / 关键数字|
|---|---|---|
|1|FAIL|祖先/预登记顺序及合成检查通过；四参考80端绑定尚未完成。|
|2|FAIL|C10 ACK/计数核对后停止；40端及4068正来源场景证明未完成。|
|3|FAIL|合成格点检查通过；真实计划和完整机制证据未生成。|
|4|FAIL|主生成/回放均0，未达到384+384。|
|5|FAIL|覆盖/边界事件0，未达到8+2；合成单测不替代正式夹具。|
|6|FAIL|无派发，完整成本频率及实际消息消费隔离审计未运行。|
|7|PASS|delivery_audit.resources：各累计上界/峰值在额度内；旧账保留。|
|8|FAIL|run_record：stopped，完整0/部分0/未开始778，未补0或续跑。|

## 实际资源消耗
- 含最终封存尾耗上界：程序≤41.678959秒，累计写入≤225391 B，元数据复制≤6594493 B，扫描≤250。
- Windows实测峰42762240 B，CPU代理实测峰7215437 B；attempt0，模拟载荷0 B；物理网络null。
- 实现修订/语法/CPU各2，真实入口1；工程阻塞，不是科学结果失败，也未触及资源上限。
- 发现阶段及封存尾耗使用保守上界，见preparation_ledger和delivery_audit；自评修正只读汇总既有事实。
- M只引用delivery_audit；P总账定位f4dd9f3联合账；旧G1.1/G1.2/P未重计，不借余额。

## 阻塞
- 原speed_assignments以字符串"1"/"4"存储，入口将其与整数集合比较，触发speed map mismatch；原映射未变。
- 修订2次和唯一入口已耗尽，禁止自行修复重跑；failure.json保全堆栈与已完成输入核对。

## 异议
无。

## 需要审查者裁决的问题（≤3条）
- 仅交G1.1工程阻塞审查：是否另派保持原机制的类型兼容修复与入口授权；本次不申请科学通过。
