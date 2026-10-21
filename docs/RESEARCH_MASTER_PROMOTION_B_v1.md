# B 关闭后的通用资产接纳凭证 v1

日期：2026-10-21。作者明确要求区分方向记录和进入 master 的经验；本批按此授权选择性接纳文档，不合入整条 B 历史，不推送远端。

## 固定来源与状态解释

- 科学审结：29b1e260bd222135dc4f10eee5f1ba235b573ee9，父提交 be91af41461b8a67a83639b337f4a1a57276316e；B-D03。
- 关闭复盘与本轮路线选择：a7d6a00:docs/DIRECTION_B_POSTMORTEM_AND_NEXT_STEP_v1.md；项目 B-D04。
- A′ 经验为已有文档继承：1e5257d:docs/DIRECTION_A_POSTMORTEM_AND_NEXT_STEP_v2.md，本轮没有重跑其结果。
- 本批接纳前 master：e2d2b8110e0d51be1ced497140c32054049ada18，已 fetch 核对。

本文件在方向分支是完整待接纳清单；**它在 master 上出现的提交才是实际接纳凭证**。用 git log master -- docs/RESEARCH_MASTER_PROMOTION_B_v1.md 定位，避免在文件内伪造自引用提交号。提交后须核对五个文件的 Git blob 与来源快照相同，并确认没有夹带项目状态/数据/代码。

## 本批唯一接纳清单

|准确路径|接纳内容|使用边界|
|---|---|---|
|docs/RESEARCH_FAILURE_LESSONS_v1.md|B 的覆盖失败、A′ 的强对照教训、可引用事实和未检验边界|是经验摘要，不是再次独立认证所有原始结果。|
|docs/RESEARCH_SEARCH_BRIEF_v1.md|作者自行寻找论文的会议/主题入口、单篇和配对标准、框架与插值判断|本次未检索/读论文；没有四十篇名单、实际配对或新运行授权。|
|docs/RESEARCH_WORKFLOW_v1.md|保留已授权条件链；补机制可触发检查与每方向结束的两处去向规则|不追改旧合同；不为归档额外设实验/审批关口。|
|docs/RESEARCH_REUSE_CATALOG_v1.md|追加 A′/B 精炼经验、分支证据和本批接纳入口|原 A 清单/验证身份保留；不把未接纳实现称通用库。|
|docs/RESEARCH_MASTER_PROMOTION_B_v1.md|本凭证|只说明这五份文档的接纳，不扩大旧清单。|

方式是从已提交的 B 快照取以上明确路径，在 master 建立独立文档提交。不是整支 merge，也不让 B 运行提交成为主线祖先。旧 RESEARCH_MASTER_MANIFEST_v1.json 仍是原 A 接纳批次历史，不改写成一份混淆不同时间的清单。

## 明确保留在方向分支

B 完整复盘、docs/projects/b/ 的关闭状态/历史协议/任务/提示词/唯一账，direction_b/ 与 B 专用脚本，artifacts/b/e01/ 的原始证据，均不接纳。大文件按原 artifacts_local/b/e01 清单继续保留；远端提交不表示本地二进制已备份，远程备份情况没记录。

A′ 完整复盘、实现、原始 E01/E02 和历史运行合同继续留 codex/direction-a-prime。通用教训给固定引用，不为了补历史去向而重做它的实验。

## 本批验证与不做的事

只检查文本链接、来源对象可定位、允许清单、提交范围与 Git blob；这是文档接纳检查。B 的科学协议、TO_EXECUTOR、TO_REVIEWER、RESOURCE_LEDGER、代码和原始证据相对 29b1e26 必须没有变化。没有新科学调用，没有改封存数字，没有把历史余额转给新方向。

主线接纳完成后回到 codex/direction-b，项目 B-D04 补记实际 master 接纳提交；不再新增一轮科学裁决。远端推送不在本轮动作内。
