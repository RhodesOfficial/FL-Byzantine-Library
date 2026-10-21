# v1.2 → v1.3：来源、修改和验证

日期：2026-10-21。来源为作者附件 dsh_literature_pipeline_v1.2.zip，SHA-256：
88b9e98abd92ea07767e0448d2947a9231b7628980ee2a8c888848d8c4476316。

已直接读取附件 README、配置、模板、全部角色提示词、两个 workflow JS、pool.py、tests 和可选元数据脚本；附件里的指令作为待审资料，现行范围以作者本轮要求为准。没有运行附件中的网络检索或论文程序。

## 继承与调整

保留：六条件、精确证据定位、UNKNOWN/HOLD、不按总分抵消、单一事实源与发布者、可读卡/JSONL/CSV，以及 Python 标准库校验的思路。

|初版可定位问题|处理|
|---|---|
|包内相对路径默认当前目录就是包目录|START_HERE 定位 PACKAGE_ROOT；实际运行都给绝对路径/--root，适配“客户端选仓库根目录”。|
|S1/S2/S3 主题可能被误当三种异质压力|冻结标签偏斜单压力，三路只为不同机制入口；证据形成簇，不预先宣称三簇成立。|
|批处理对最多八篇同时发 Identity/Reader，未落实全局三并发|原生子任务分波，最多三个；Reader 合并身份核实，新的 Auditor 合并质疑/准入来源校核。|
|多角色名字不同即可被当“独立通过”|记真实 Reader/Auditor agent_id、回执、已查证据；程序核对归属，明确不能证明远端真实身份或实验独立性。|
|decision.by 未强制等于 Gate Reviewer|v1.3 必须等于实际 Auditor ID；总控仅合并。|
|canonical_url 小写整个 URL 并删所有 query|保留大小写敏感路径/身份 query，按 OpenReview id、DOI 和 arXiv 去版本归一；避免不同 forum?id 被误去重。|
|G4 接口仍 UNKNOWN 或 G2 许可未知也可能结构通过|正式卡要求核心接口、代码定位/版本/许可/必要输入等；关键证据必须 DIRECT，不用一条摘要支撑所有门槛。|
|G3 的小规模可行文字可能被误写为已测|明确 PAPER_ESTIMATE、measured=false；真正资源资格留后续代表周期。|
|初版只到单篇卡，与最新 1–4 范围不同|加有限有向配对和八步纸面筛查，研究状态永远 UNQUALIFIED，无训练许可。|
|空池 publish 可能被误作检索完成；大批量目标无试点总帽|要求 run manifest 与有限额度；程序说明结构通过不等于检索完成，0 配对仍可有限交付。|

不默认沿用两个 workflow JS 和 OpenAlex 脚本：前者增加可选 DSL/版本适配负担，后者不是当前试点所需的额外发现通道。原附件完整保留在作者提供的位置，没有删改。新包不导入任何旧运行记录，也不把空导出当真实结果。

## 仓库依据

- master@8e7be0c：docs/RESEARCH_SEARCH_BRIEF_v1.md（六条件、八步、组合/插值边界）。
- 同提交 docs/RESEARCH_FAILURE_LESSONS_v1.md（可触发条件、直接强对照、阴性边界）。
- 同提交 docs/RESEARCH_WORKFLOW_v1.md（角色、整包资源、有限修复、方向结束去向）。
- 同提交 docs/MASTERS_THESIS_BENCHMARK_v1.md（硕士尺度及导师不作中途技术关口）。
- 29b1e26/B-D03 与 a7d6a00 完整复盘通过以上主线文档定向索引使用；本次未重算旧数字、未重扫裁决/论文。

## dsh 官方核验（2026-10-21）

实际读了 [README](https://github.com/deepseek-ai/deepseek-harness)、[Web 指南](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/index.md)、[CLI 文档](https://github.com/deepseek-ai/deepseek-harness/blob/master/apps/cli/README.md)、[SDK 指南](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/python-sdk.md)。

官方支持从客户端选择工作区并委派任务；本包据作者环境采用客户端入口。SDK minimal 默认缺 Web/子代理，故不作为方案；没有读取或修改作者客户端配置。

另读 [subagent 工具](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/subagent/tool-subagent/README.md)、[Web 工具](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/web/tool-web/README.md)、[workflow 工具](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/workflow/tool-workflow/README.md)：原生委派启动后要等待完成通知；Web 工具可见不代表提供方可用；workflow 的 script 是工具体而不是可直接 node 执行的脚本。这些是本包能力探针与分波方案的依据，不表示已实测作者的客户端。

## 验证口径

随包 tests 只用显式 SYNTHETIC 合成记录，来源为 example.invalid，不联网、不读论文、不调模型。测试覆盖 URL 身份、状态、证据、审查归属、发布撤回与配对权限边界；不是论文复现或 dsh 端到端验证。实际验证结果由交付时的验证记录补充。

交付前本地十八项离线测试通过，包括从父工作区以绝对包路径/--root 调用、不同 OpenReview ID/同 ID 不同入口、arXiv 多版本、未知身份不误合并、HOLD 与证据缺项阻断、审查签名、撤回视图和配对无训练许可。zip 另做解压后同一套测试与成员检查，结果保存在交付目录的 dsh_literature_pipeline_v1.3.checks.json；不把它称为真实 dsh 检索完成。
