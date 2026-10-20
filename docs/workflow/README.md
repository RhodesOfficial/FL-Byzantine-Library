# 工作流入口

更新：2026-10-20。此目录保存方向 A 的现行状态、旧冻结规则与交接，不再作为新方向的通用模板。

## 新方向

先读以下三份文件：

1. [通用研究工作流](../RESEARCH_WORKFLOW_v1.md)：问题、资格、确认、工程周期、资源和止损。
2. [硕士论文资格对照](../MASTERS_THESIS_BENCHMARK_v1.md)：以 master's thesis/ 的具体论文为中途判断依据。
3. [成果复用索引](../RESEARCH_REUSE_CATALOG_v1.md)：master 已接纳的基础与 A 分支可定向引用的材料。

导师不提供中途选题和机制指导，只在论文完成后判断是否够参加盲审。Reviewer 必须自己作技术与资格判断，不派“先问导师”的依赖任务。作者决定范围、时间和资源。

给未来 Reviewer 的启动提示：

“读 docs/RESEARCH_WORKFLOW_v1.md、docs/MASTERS_THESIS_BENCHMARK_v1.md 和 docs/RESEARCH_REUSE_CATALOG_v1.md，按 Reviewer 职责处理当前方向的交付。先判断必要条件与科研价值，再安排下一完整工作周期；不要继承 A 的待办或专用计次。”

给未来 Executor 的启动提示：

“读 docs/RESEARCH_WORKFLOW_v1.md，按 Executor 职责执行当前方向任务单。复用对象按 docs/RESEARCH_REUSE_CATALOG_v1.md 定位；在既有科学范围与总预算内自主修复，保留结果和费用，不根据分数改协议。”

新方向的 STATE、PROTOCOL、TO_EXECUTOR、TO_REVIEWER、DECISIONS 放在 docs/projects/<方向ID>/。本次未创建或启动新方向任务。

## 旧方向 A

- 当前科学状态：冻结 G1.3 场景静态失败；P 的四参考全范围不通过，但没有证明尾类特征不存在。
- 10 月 15 日已明确 C100 完成概率相同，仍放行后续事件；后续流程教训见修订后的复盘。
- D7 研究选择尚待作者决定。复盘、复用整理和规则通用化已获作者授权，与新实验授权分开。
- 现有 ROLE 只适用旧冻结任务；其中历史预算和失败不追溯改写。未来重新立项按通用流程建新身份。
- 旧操作手册全文可在 ba9b542:docs/workflow/README.md 定位。不要继续使用其中“首次 G1.2 实操”、导师月报、特定模型价格比较等过时建议作为当前任务。

[方向 A 复盘](../DIRECTION_A_POSTMORTEM_AND_NEXT_STEP_v1.md) 是理解失败的入口；[STATE.md](STATE.md) 保留 A 的精确状态。旧 TO_EXECUTOR/TO_REVIEWER 被覆盖时按具体提交查，不重新扫描全部历史。

## 日常操作

每次只交接当前问题、证据、四栏状态、累计资源和下一决定。普通修复不另建裁决 vN；范围或总预算变化追加到当前方向 DECISIONS。提交前只暂存本次相关文件；本地提交不自动授权远程推送。不要为了换会话重复运行已通过且未变化的实验。
