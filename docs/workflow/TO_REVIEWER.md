# 交付单：G1.1 正式事件F类型修复续接

- 对应任务单的基准 commit：`cb8dd23bda83b3450808361e6367e3ecb2562808`。
- 本次授权：`befac4eb349beddb673babb73550c2bb03cfe85f`；源码/预登记：`4af17ebeb0248ed81dc56c0c7c4cc2f28a2bf258`；交付：见本提交。

## 做了什么（≤5条）
- 严格解析原字符串速度映射，共用整数视图；一次语法/CPU检查，5项测试通过。
- 唯一续接完成778项：主生成384/回放384、覆盖8/边界2；原包及预登记不改。
- 封存及确定性读回通过；交付复核发现模拟载荷全流程包络低估，停止并交审。

## 产出文件
- `artifacts/direction_a/phaseG1_1_formal_F_resume_v1/`：任务要求的输入、绑定、机制、支持、计划、事件、回放、覆盖、消费审计及封存全包。
- `repair_notes.json`、`preparation_ledger.json`、`selfchecks.json`、`preregistration.json`：一次准备及旧账定位。
- `delivery_readback.json`、`delivery_audit.json`：已封存产物哈希读回、估算偏差及最终联合/本段账。
- `direction_a/formal_f.py`、`scripts/run_direction_a_formal_f.py`及相关CPU套件：源码已先提交。

## 判据自评
|判据编号|结果 PASS/FAIL|证据位置 / 关键数字|
|---|---|---|
|1|PASS|input_checks/preregistration/entry/selfchecks；80绑定，新增修订/语法/CPU各1、入口1，累计3/3/3/2；样本/CUDA0|
|2|PASS|binding/support：两任务40端ACK绑定；4068正来源场景；先bootstrap后attempt|
|3|PASS|binding.mapping_conversion：120项一致；mechanism/plans/coverage保留精确格点及单列有理数等号|
|4|PASS|events/replay_checks：384+384一致，终态/费用保全，每主轨迹32δ、实际更新0|
|5|PASS|coverage：4+4+2、累计778，非法返回拒绝及重复round覆盖|
|6|PASS|run_record.simulated_costs/diagnostic_channel_audit：W01/W02成本分栏、隔离审计通过|
|7|FAIL|delivery_readback：实际模拟载荷29642603849 B > 登记包络28544398373 B；重建主任务保守上界35727851520 B > 32 GiB，启动前全流程估计不保守；实际硬限额未超|
|8|PASS|run_record/封存读回：completed、完整778/部分0/未开始0；索引/身份/回放/支持一致、终末实耗合规|

## 实际资源消耗
- F联合保守累计≤95.735152秒 / 写入≤2545091 B / 元数据≤15150236 B / 扫描≤523；Windows峰77742080 B、CPU代理峰23044385 B。
- 模拟载荷29642603849 B；新训练/前反向/编码/梯度/validation/test/CUDA/更新均0，物理网络null。
- 旧F最终账只加一次；本段增量见delivery_audit.segment_delta；M用delivery_audit、P用f4dd9f3联合账；峰取max，旧尾耗不重复相加。

## 阻塞
- 有：启动前模拟载荷保守包络低估；已停止后续执行，完整结果封存，不再修订/重入；需审查者裁决资源估算保护缺口。
## 异议
- 无；不以实际实耗仍合规替代全流程保守估算要求。
## 需要审查者裁决的问题（≤3条）
- 仅申请G1.1裁决：判据7 FAIL如何影响本次778项结构证据的接收；不自行进入下一节点。
