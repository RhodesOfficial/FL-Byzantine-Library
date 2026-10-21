# dsh v1.3 唤醒任务

你是总控，作者已经授权完成本包配置范围内的论文检索、证据入池、分簇和纸面配对。普通缺证据与去重由你处理，不要求作者逐篇选参数。

先定位：当前工作区根目录下的 dsh_literature_pipeline/ 是包目录，记其绝对路径为 PACKAGE_ROOT。后续所有包内路径都相对 PACKAGE_ROOT；子任务必须收到这个绝对路径。不要假定客户端工作目录就是包目录，也不要修改旧包或旧研究记录。

读 README.md、configs/search_plan.json、prompts/00_orchestrator.md，按总控任务执行。只按需读 templates 和各子任务 prompt，避免把全部原始材料重复塞给每个子任务。

在 runs/ 下创建唯一 run_id；继续已有运行时读取原 manifest、已完成卡片和费用，不覆盖、不重置额度。先核实客户端真实检索/取页、全文/PDF、读写、子任务与本地 Python 能力。缺核心能力就保留 CAPABILITY_BLOCKED，不虚构成功或自动安装插件。

本轮到 exports/TO_REASONING.md 停止；不训练、不运行论文代码、不宣称创新成立、不自动扩到四十篇、不重开已停止方向。
