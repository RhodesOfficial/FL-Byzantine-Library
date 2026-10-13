# 合格骨干准备候选交付

parent_checkpoint=G1.2；work_item=合格骨干准备。

两份封存任务各完成一个普通 FedAvg 运行，各留第 40/80 更新轮，共四个预选参考；全部保留，缺失项为空。

manifest.json 定位全部参考、运行进度与验证记录；task_binding.json 绑定原 0.2 八文件、标签/IF/α/分组及两类 seed；generation_config.json 是预选普通训练/BN/变换/参与规则与实现指纹；run_record.json 是累计额度，runs/ 是实际进度/成本；validation_record.json 含四参考和两初始基线的完整分母/缺失项；checkpoints/ 保存同版本 backbone/head/全部 BN；artifact_hashes.json 封存字节。

加载：direction_a.backbone_preparation.restore_candidate(path, device='cpu')，返回 eval/冻结模型与来源元数据。仅核对保存/读取的精确状态，不使用 0.2 logits ε_num。没有断点续训，也不交 E1 全生命周期恢复包。

准备状态只是候选包完整、来源可核对，不签 G1.2 或 P；普通头验证不等于特征可分性，没有引入最低精度门槛。G1.1 正式仍证据不足，本次理想参与和 W01 实测不替代 W02/正式事件绑定。

接收方须继续核对正式参考与任务/模型/变换/训练/多个参考点相符，独立完成完整头梯度（含 bias）、逐样本/端类均值、a_ic 汇总 G_c、参数/缓冲读取不变、缺类/采样噪声口径及相关数值容差；之后 P 才裁决可分性。A1/A2/A3、G1.3、E1 均未执行。
