# 交付单：G1.1 D3结转观测记录定点修复

- 对应任务单的基准 commit：5174b06bb1a6d90e58ed6e07b5ab6e88e283f269
- 本次交付 commit：见本提交

## 做了什么（≤5 条）
- 复制旧辅助实现，仅将 synthetic.check 委托给复制观测及期望的 snapshot_check；实际回归调用该记录函数。
- 一次结转、重复拒绝、原三笔各维+1；独立子进程重新读取 JSON，逐字段检查值与 result。
- 11项定点回读断言通过；旧记录及注入别名作为预定负例检出，不重跑53项。
- 首次语法子进程因编译复制估算不足被守卫拒绝，CPU未启动；保留一次修订完成修复和复验，失败原文见 attempt1.json。
- 两轮共用原50秒/524288 B写/3145728 B读/48扫描，未扩大资源或真实入口。

## 产出文件
- artifacts/direction_a/phaseG1_1_carry_record_repair_v1/：实现、最小差异、计划、身份、两轮证据和自动哈希。
- observations.json / reader_receipt.json：新快照及独立回读；attempt1.json：首次失败及当时源码、收据。
- accounting.json / workflow_audit.json：程序、工作流和历史分账；artifact_hashes_workflow.json：补全工作流哈希。

## 判据自评
| 判据编号 | 结果 PASS/FAIL | 证据位置 / 关键数字 |
|---|---|---|
|1|PASS|identity.json：Git对象及旧包锁定、基准祖先；引用778/0/0，无逐事件扫描，科学/事件/回放/费用新增0|
|2|PASS|source_patch.json、validate_snapshot.py；实调旧 synthetic.check 共用 snapshot_check，独立字面期望未改|
|3|PASS|reader_receipt.json：11/11；17/39/52/9/272固定，后账20/42/55/12/275；重复拒绝、别名检出|
|4|PASS|plan.json、repair_note.json、两轮收据：下一动作/子进程/封存守卫，外层0.3980749+0.6727536秒无超时；各Python峰已保存|
|5|PASS|新段工程/修订/语法/CPU=2/2/2/1，D3累计6/6/4/2，历史工程10；旧判据5永久FAIL，未采旧3/3自报|
|6|PASS|旧3本次补证；旧1/2/4/6仅引用v8 PASS，不重新验证；历史FAIL及未关闭条件保留|

## 实际资源消耗
- 两轮外层合计1.0708285秒；Windows已保存峰最大 29061120 B，CPU代理最大 2031322 B；外层峰/OS隐式I/O/工作流精确峰仍null。
- 程序逻辑上界含失败/重复/子进程：首次写≤32768 B、读≤417296 B、扫描≤10；复验写44844 B、读877904 B、扫描16；工作流及全部写入/哈希回读见 workflow_audit.json。
- 新增磁盘见 workflow_audit.json 的有限文件清单及 artifact_hashes_workflow.json 的最终大小；实现两版及重复输出写入保守占额，未知物理I/O不补0。
- 正式入口/费用2/2、正式修订/语法/CPU各3/3继续关闭；历史辅助修订精确数、旧segment_actual/joint_upper/峰均null。
- F第7条、封账第5条、恢复第4条、旧D3 1–5及P全范围FAIL保留；79端无超时；U=34871421077 B及差额511682709 B仅旧替代上界缺口，不重算。

## 阻塞（没有写“无”）
无（本单定点修复完成；G1.1仍未关闭、G1.3未放行，既有科研与资格条件仍待审查）。

## 异议（没有写“无”）
无。

## 需要审查者裁决的问题（≤3 条，没有写“无”）
确认旧判据3的补证；旧判据5及其他历史FAIL不追认，新授权仅向前生效。