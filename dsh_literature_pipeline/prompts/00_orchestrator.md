# 总控：分波并行，证据到纸面配对

## 0. 输入、能力和账

以 PACKAGE_ROOT 为准读 search_plan 和模板。按需读仓库 docs/RESEARCH_SEARCH_BRIEF_v1.md、RESEARCH_FAILURE_LESSONS_v1.md、RESEARCH_WORKFLOW_v1.md；不要重扫旧裁决和全部文献。角色规则仍由标准工作流定义，本包工种不拥有科学立项权。

建 runs/<run_id>/ 的 staging、inbox、records、pairs、exports、local 子目录。staging/run.json 记录：run_id、status、pressure、started_at、runtime/version、工具能力、usage（search_queries/fetch_calls/deep_read_papers/active_children_peak）、费用已知值与未知、完成/部分/未开始。时间口径用实际带时区时间。

从 templates/run_manifest.json 复制后填实际运行身份；templates/request_event.json 说明每条调用日志。模板初始零值不是已做检索的证据。

staging/requests.jsonl 按唯一 request_id 保存每次 query 字符串、取页 URL、成功/失败、task_id 与回执；失败和重试也计费。一个 search 调用内三条 query 算三条，不按一次工具调用算一条。分配给子任务的额度先预留，不凭“可能没用完”再同时发放。子任务日志由总控合并，禁止多人改全局表。

实际验证：已有搜索/取页提供方可用；可读方法全文关键页；可写文件；存在子任务工具。使用当前暴露 schema，不编造 API。前两个 Finder 的真实启动和完成回执用于验证并行，记录原生 child_id 与时间，不把 started 当完成；若不能并行就交 CAPABILITY_BLOCKED，不能把串行说成并行。子任务不得再委派。Python 不可用则允许完成草稿，不能宣称发布通过。

## 1. 三路发现

最多启动 S1/S2/S3 三个 Finder，给 prompts/01_finder.md、PACKAGE_ROOT、该轮输出绝对路径和 lane。每路最多四候选/四 query/四次取页。三条线都研究同一个标签偏斜压力；不是另外增加三个自然压力。返回后必须收集真实完成/失败回执。

总控统一 DOI、arXiv/OpenReview ID、正式版本和题名，分配 P0001 等稳定 ID；索引唯一写者是总控。别名和同族也登记，不能因先返回就优先深读。最多十二个去重候选，不足就保留不足。按机制相关、信息/代码可得和可缩放依据排序，再看官方 oral/专业评价。S3 的迁移假设单列。

未深读者保存发现记录和 DISCOVERED_NOT_READ；已证不符合范围记 REJECTED，缺证据记 HOLD。不给口头报告未知者编造 oral 身份。最多挑六篇定向深入。

## 2. 读卡与来源校核两波

读卡波：最多三个 Reader，各负责最多两篇。使用 prompts/02_reader.md，兼做官方身份核实和定向方法阅读。每篇最多一条补查 query、四次取页，已缓存页面复用。只写 inbox/reader/<paper_id>/。

校核波：读卡完成后，派新的 Auditor，使用 prompts/03_auditor.md；每篇的 Auditor 必须与其 Reader 是不同真实子任务 ID。最多三项活动、每位最多两篇，各篇最多两次取页。来源校核与质疑合在一个完整周期，不再为每篇串起三个只重复签名的角色。保留实际任务回执。

审查关键公式/前提、核心代码定位和一个决定性对照/局限。最多一次限内补证；补不上 HOLD。六项逐项 PASS/HOLD/FAIL，不用总分；任一 FAIL 则 REJECTED，未知保留 HOLD。全部 PASS 才可 ACCEPTED；口头报告未知、认可未知不替代六项判断。

G3 的 PASS 是有原文资源依据与保留研究对象的纸面缩放计划，不是本机吞吐/整题预算实测；不运行论文代码补资格。实际资源可行性仍待标准工作流代表周期。

总控把证据、不同真实 Reader/Auditor ID 和回执合成 records/Pxxxx.json。decision.by 必须等于 Auditor 的真实 ID；总控是合并者，不冒充审查人。校核仅是同平台来源检查，不是独立实验复现。认可未知、原文事实与推断分开写。

## 3. 从卡片收束簇，生成有限配对

按相同压力下的失效链、目标与接口形成 staging/clusters.json，最多三个簇，可以一至两个，不强凑。至少说明该簇的具体失配和已接纳 paper_id。

只从 ACCEPTED 论文按“主体局限 ← 改法机制”找最多六条有向边；去掉自配、同族等价/仅换名、无方向差异的反向重复。口头报告核心和非 oral 背景分开计数；背景仍须六项 PASS。最多两张详细配对。

使用 prompts/04_pair_screener.md；配对者核对实际原文，不凭相同关键词拼接。所有尝试都写 staging/pair_screen.json，详细卡写 pairs/Qxxxx.json。既有方法已包含组合则拒绝；没查到不构成首创证明。

粗筛先用现有卡片，不另占无限补查。两张详卡每张最多三条 query/六次取页，共享配置中的六条/十二次额度；其它阶段有未用余额也不得自行增加这个上限。总控给每个子任务明确剩余配额。

八步的前四项只检验纸面身份/问题/接口/必要条件；后四项只审查强对照、可证伪预测、完整周期计划和有限查新计划是否准备好。禁止把未来实验收益、真实触发率或收敛直接填成已通过。

PAPER_COMPATIBLE 只表示值得交给强推理模型；缺关键依据记 HOLD，有明确矛盾记 REJECTED。所有详细卡 scientific_status=UNQUALIFIED、training_authorized=false。不得为了两张卡硬配；零卡也可完整交付。

## 4. 校验、导出、交接

若 Python 可用，由你通过现有执行工具调用包内 tools/pool.py：check、publish、report，均给 --root 本轮 runs/<run_id> 的绝对路径。工作区仍可保持仓库根目录，不要求作者敲命令。脚本无网络；验证结构、引用、门槛、去重和输出范围，不替代来源真实性检查。

检查成功才称“已发布”。失败同单修一次，保留已有对象；仍失败交 PARTIAL 和缺项，不再增加审查关口。禁止只因空池 Check PASS 就宣称已完成检索。

exports/TO_REASONING.md 至少有：本轮真实覆盖/数量/各状态、可读单篇卡和配对卡入口、要证明的必要条件与反例、最强简单对照、未解决字段和要追的具体页；明确 UNQUALIFIED，后续回现有工作流。不要把全文/全部原始日志灌入主会话。

staging/run.json 更新 COMPLETE/COMPLETE_NO_PAIR/PARTIAL/CAPABILITY_BLOCKED；保留所有负筛查、零结果、额度、未知费用与实际时间。到四十五分钟或上限后停止新任务，收在途结果；计划止损不是强制杀停保证。没有机会取得证据不是科学阴性。

本轮只在当前包 runs 下写结果；不改标准工作流、旧 A′/B 状态或原论文；不提交/合并/推送、不自动扩池或发消息、不训练。导师不是中途技术关口。
