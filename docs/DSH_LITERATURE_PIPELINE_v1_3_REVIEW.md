# dsh v1.3 交付与使用边界

2026-10-21。用户对五步的理解基本正确：单一异质压力、六条件卡片、收束问题簇、主体/改法的八步纸面筛查，然后进入已有标准工作流。补充：分簇可随检索迭代；未知不作 PASS；纸面配对不等于创新、真实触发或最小程序资格成立。

实际修改对象是用户提供的 dsh_literature_pipeline_v1.2.zip，来源哈希和逐项修改见 [CHANGELOG](../dsh_literature_pipeline/CHANGELOG.md)。引用对话的助手正文最初返回内容占位符；拿到附件后已实际读取初版包，不再以缺失正文作为交付依据。

客户端使用：包位于当前工作区 dsh_literature_pipeline/；dsh 选仓库根目录，发送“读取 dsh_literature_pipeline/START_HERE.md，按 v1.3 完成一次有界并行试运行”。[使用说明](../dsh_literature_pipeline/README.md)

本次更好的组织方式是原生子任务分波：三个 Finder → 唯一去重 → Reader 波 → 不同真实子任务 Auditor 波 → 最多两张纸面配对 → 总控校验发布。Reader 合并身份核实，Auditor 合并质疑与来源准入校核，减少只重复签名的中间角色；来源检查与科学 Reviewer 裁决仍分开。无需作者开命令行，也不依赖可选 workflow JS 插件。

已冻结默认试点为标签偏斜、同构同步；最多 12 候选/6 深读/6 粗配/2 详卡，3 子任务并行，不递归委派。上限和状态是设计选择，不是已发生结果。当前没有真实论文卡或已成立的新算法。

新内容在独立分支 codex/dsh-literature-pilot，从 master@8e7be0c 建立；未修改主线工作流、已关闭 A′/B 的原始协议、数字或预算。交付为当前包和 zip；不自动推送或合并。

真实 dsh 客户端的提供方、PDF 能力、原生并行仍由首次运行探针检查。本会话只读官方 dsh 文档，没有检索研究论文、运行论文程序或触发模型费用；离线结构/发布测试不代表真实 dsh 端到端验证。

实际交付：[v1.3 zip](../deliverables/dsh_literature_pipeline_v1.3.zip)，顶层单目录 dsh_literature_pipeline/，十九个文件，33 KB 左右。源码测试十八项通过，独立临时工作区解压后十八项再次通过，CRC/解压后逐文件字节核对通过。准确大小、SHA-256、成员和测试原始输出见 [checks](../deliverables/dsh_literature_pipeline_v1.3.checks.json)。
