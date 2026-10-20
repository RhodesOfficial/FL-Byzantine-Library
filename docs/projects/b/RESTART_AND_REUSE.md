# B 重开、旧分支处理与复用记录

日期：2026-10-21。当前作者要求的是按 A′ 的条件任务链重开 B，而不是重做 A′ 的研究问题、清除负结果或把一次向量验证算成方向终点。[文件：作者本轮指令]

## 1. 实际读过的流程依据

定向读取 A′ 起始提交 f473304 的 PROTOCOL、TO_EXECUTOR、PROMPTS、PLAIN_GUIDE，随后读取 b9e8336 的 READY 交接和 1e5257d 上的当前协议/状态/提示词及相关决定。没有重新扫描 A′ 全部实验和裁决。[提交]

A′ 的起始协议已经说明 E01 之后是 E02、再是 E03；Reviewer 继续时要一次更新完整任务与预算。当前分支末尾虽然关闭 A′，那是后来主判据失败后的科学决定，不能复制成新 B 的默认终态。A′ 的历史预算追加也不能描述成它一开始就无条件开放全部后续训练。[文件：上述协议 §4、6；PROMPTS]

旧 B 的问题是 d35871b 把“完成作者当轮节点”落实为“没有新运行单”，留下了科学缺口，却没有把它交成下一项可执行任务。新协议将本单完成与方向状态分开：阶段通过立即给下一单，主判据失败停止；范围内不反复交作者选择。[提交：d35871b；推断：本轮流程修正]

## 2. 分支实际处置

- 旧本地 codex/direction-b-residual 改名为 **codex/archive-b-r01**，保留 d35871b392b46528666b0f00f93b81aa3708b061 的完整历史及全部结果；不删除、不改数字。
- 新 **codex/direction-b** 从再次 fetch 核对的 origin/master @ e2d2b8110e0d51be1ced497140c32054049ada18 建立。不是从旧 B 连续追加，也没有合并旧 B 的整条提交。
- 旧远端 origin/codex/direction-b-residual 继续保留作只读历史指针，不是当前运行入口。本轮没有推送、删除或改名远端分支。
- 新目录为 docs/projects/b/；旧 docs/projects/direction_b/ 的状态/权限只在归档分支解释历史，不能自动授权或禁止新协议。

[文件：本轮 Git 操作及核对]

分支操作曾因自动审批服务的用量限制未执行；在作者“继续”后通过同一审批路径重试成功。没有绕过审批、直接写 Git 内部文件或把服务故障当科学失败。[工具记录]

## 3. 复用对象、身份及限制

|来源提交 / 路径|继承对象与已验范围|B 新阶段改变及重验|
|---|---|---|
|e2d2b81: docs/RESEARCH_WORKFLOW_v1.md、RESEARCH_REUSE_CATALOG_v1.md、MASTERS_THESIS_BENCHMARK_v1.md|共同职责、止损、已接纳基础与硕士参照|只补条件任务链的衔接说明；不搬旧专用角色/费用规则|
|1e5257d: docs/DIRECTION_B_QUALIFICATION_DESIGN_v1.md，§6.4–6.5、§7、§10|绝对组等权的暖缓存反例、EF21/CA2FL/T8 近邻、修订门槛|原 §9 草案继续不用；原失败保留|
|d35871b: docs/DIRECTION_B_QUALIFICATION_REVISION_v1.md|总体占比残差分层、条件 MSE 推导、冷不可辨识与近邻记录|核心估计结构继承；真实梯度、连续时间和历史误差没有被旧证据验证|
|d35871b: artifacts/direction_b/r01_v1/{manifest,summary,controls,ledger}.json；docs/projects/direction_b/R01_RESULT.md|24 个二维单元、480 个反事实缓冲、状态/恢复与正负结果|仅有限基础；不重跑、不复制其运行状态。N/D、精度、持续历史、梯度来源均在 E01 新验|
|e2d2b81: direction_a/{task,model,evaluation}.py；models/ResNet.py|固定任务读入、ResNet-8 raw logits、评价分母|模型 eval 只固定 BN，全部参数仍求导；不使用 freeze_reference 关掉梯度，不做 A′ 分类头研究|
|e2d2b81: artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR10-N20-v1/|既有索引、计数、分割身份；alpha=0.1、训练 IF=100|客户端等权 CE；E01 固定本地训练子集，E02 才用全本地训练池；不新划分、不按结果选样本|
|ba9b542: artifacts/direction_a/backbone_preparation_v1/checkpoints/A-backbone-CIFAR10-s2026101321-r0080-v1.pt|已保存普通网络参考；仅用于固定起点|不是“已证足够强的模型”，不继承旧 P 阈值、类梯度或效用结论；全模型新梯度另算|

旧推导的近邻记录：EF21 官方 PDF 7–8 页、R06_Wang2024_CA2FL.pdf PDF 5–6 页、T8 PDF 41–43 页来自 B-Q00；FedVARP PDF 5–6 页、Fraboni Clustered Sampling PDF 4、6 页来自旧修订。**本轮未重读原文**，均标 [文件继承]，不可说本轮又完成全文查新。进入确认前按协议补最接近的完整机制对照。

本轮另定向读取 d35871b:direction_b/qualify.py 的 groups、gate 及相关聚合片段，补明确第一合格组、零消息单元素组、旧残差/缓存范数比的原有定义；没有执行旧代码。高维实际重建差、十缓冲年龄窗口及真实模型路径是新设计，不能将其写成旧代码已经验证。[提交]；[推断]

## 4. 本轮 S00 只读启动核验

核验日期 2026-10-21：

- 本地/远端 master 相同为 e2d2b81；新分支祖先不含旧 B 的三个提交。
- 固定 C10 任务的 data.json、counts.json、acceptance.json 与 info.json 记录的 SHA-256 相符；20 端、训练总数 11,165、最小端 2 个样本，无空端。按 min(32,n_i) 计划子集共 583；尚未选择或读取图像。
- 目标 r80 checkpoint 的 Git blob 可定位，大小 1,258,030 B；历史文件 SHA-256 为 d8e137b9feeda74bb3bf401b64569e0075f3ec52914eb0ccf72d56040965a5ed，模型 state SHA-256 为 c2a11303f977029a840946f1703047288365ec4b6bbb7136db3ad3eb65ad4b44。这里只读 manifest/hash/Git 对象大小，没有加载网络。
- 五份 CIFAR10 训练源文件存在；未在本轮读取其图像，尚未核对原始文件哈希。Python 路径存在，未启动 Python 或导入训练库。Executor 开始后先做这些生产前检查，其时间计入 E01。
- 旧 R01 的主判据及负结果按已封存记录接纳，没有重复实验或重新计算指标；没有把旧“暂无后续授权”的文字搬到新协议。

来源：本轮只读检查；历史 manifest/artifact_hashes 对应 ba9b542；旧 R01 对应 d35871b。[文件]；[提交]

S00 的结论是**可以派 E01**，不是高维程序已实现、环境全测通过或自然梯度假设成立。当前不存在已知必要条件反证直接否定整项新检查；门控可能关闭等问题必须由固定 E01 真实输入回答。

## 5. 费用与历史不清零

旧 R01 已记录 Python 墙钟 1.3655257 s、最大记录工作集 25,731,072 B、结果目录 575,616 B；这是历史限定口径，人工时间没记录，不扩大成历史完整成本。本轮只是读取引用，不把数值再次相加进新阶段运行增量。[文件：d35871b 的 ledger/R01_RESULT]

新项目独立 RESOURCE_LEDGER.json 保留这一历史引用及新任务自身增量。S00 无新科学程序调用；文档、Git、只读 PowerShell核验和人工时长没有完整计时，不把它们写成零研究成本。旧 A/A′ 费用与验证曝光历史继续保留，分支重开不代表新数据。

以后复用可直接引用本页的固定提交和路径；需要二进制时只提取指定 checkpoint，用字节方式保存并核对哈希。不要扫描整个文献目录、复制旧专用工作流，或执行旧 R01/A′ 的生产入口。
