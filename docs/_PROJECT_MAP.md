# 项目地图

[推断] 分类为检索分组。

### 1. 运行时骨架

1. main.py:run()：按 trial 调用 mapper.py:Mapper.initialize_FL()，经 get_dataset/get_net/get_indices 组装实验。
2. main.py:train_epoch() → fl.py:FL.train()：按参与率选择 cross_silo_step() 全参与或 cross_device_step() 抽样。
3. client.py:client：update_model() 同步，train_()→local_step() 训练；get_grad() 返回动量/Adam 更新。
4. FL：本地攻击走训练；全知攻击调用首个恶意客户端 omniscient_callback() 并复制 adv_momentum；良性在前、恶意在后。全参与且关闭 MITM 时，Byzantine_grad_preds() 模拟动量。
5. FL.aggregate()：统一设备，可选 Bucketing.`__call__()`，再调用聚合器 `__call__()`。
6. FL.update_global_model()→utils.py:update_model()：参数减去学习率×聚合向量；evaluate_accuracy() 测试，主块经 logger.py:save_results() 保存汇总。

localIter 是批次数；FL.epoch 按参与人数×本地步数×批量大小/样本数累加，train_epoch() 推进到下一整数；global_epoch 非通信轮数。

### 2. 扩展点清单

| 对象 | 实现与注册位置 |
|---|---|
| 聚合器 | aggregators/base.py:_BaseAggregator 子类实现 `__call__()`（张量列表→向量）；在 aggregators/aggr_mapper.py 导入并加入 aggr_mapper、set_aggr_params()。 |
| 攻击 | 全知类继承 attacks/base.py:_BaseByzantine，实现 omniscient_callback()、设置 adv_momentum；本地类继承 client.py:client，覆盖 local_step()。在 attacks/attack_mapper.py:attack_mapper 注册；工厂传客户端参数及 n,m,z,eps,layer_inds。 |
| 模型 | models/ 中实现 torch.nn.Module；在 model_registry.py:get_net() 的 neural_networks 注册类与参数，补 labels；层边界见 utils.py:get_layer_dims_lasa()。 |
| 数据集 | datasets/ 工厂接收 root,download，返回训练/测试集；自定义类继承 torch.utils.data.Dataset。在 data_loader.py:dataset_mapper 注册，适配 get_dataset() 路径、get_indices() 标签及模型类别表。 |

参数：config/ 下 DefenseConfig（defense.py）、AttackConfig（attack.py）、ModelConfig（model.py）；同步 parser.py 的 _build_parser()、_namespace_to_config()、FLConfig.to_flat_namespace() 及工厂。稀疏掩码入口：pruners/prune_mapper.py:get_attack_locations()。

FLGo 独立注册：flgo_byzantine/algorithm.py 的 AGGREGATORS＋_build_aggregator()、ATTACKS＋_attack_update()。

### 3. 已有聚合器分类

目录：aggregators/。

| 类别 | 成员文件与机制 |
|---|---|
| 距离类 | krum.py：近邻平方距离评分后选一个或多个更新；rfa.py：平滑 Weiszfeld 迭代；dnc.py：随机子空间中按首奇异方向投影平方筛选；fedredefense.py：按截断 SVD 的相对重构误差筛选。 |
| 截断类 | cm.py、ca.py：坐标上下中位数平均；trimmed_mean.py：逐坐标去除两端后平均；tm_abs.py：按绝对值去除两端；tm_capped.py：按截尾后的边界限幅再平均；tm_cheby.py：按均值±标准差倍数限幅；tm_history.py：截尾后加入前轮聚合值副本；tm_perfect.py：先删除末尾 b 个输入，再非对称截尾。 |
| 截断类 | clipping.py：围绕持久参考向量裁剪；cc_lw.py：逐层裁剪；ccangular.py：计算余弦后将权重设为 1，实际执行中心裁剪；cc_seq.py：分桶后顺序裁剪；cc_seq_ecc.py：两组桶裁剪，可选固定参考迭代。 |
| 聚类类 | cc_cluster.py：余弦排序分组、轮换桶与参考并裁剪；flame.py：余弦距离聚类、取最大簇、范数裁剪及可选高斯噪声；skymask.py：根数据参与掩码优化流程，按掩码聚类并选服务器所在簇。 |
| 信誉类 | foolsGold.py：当前/历史余弦相似度加权；fl_defender.py：相似度 PCA 后累计信任加权；fldetector.py：累计参考距离、聚类筛选后取中位数；fl_trust.py：根数据动量决定正余弦权重和范数归一化。 |
| 符号类 | sign_sgd.py：逐坐标符号多数表决；signguard.py：符号比例聚类与范数筛选交集，再裁剪平均；fedseca.py：符号一致性加权选举，裁剪、限幅、稀疏化后聚合同向坐标。 |
| 混合类 | bulyan.py：Multi-Krum 后坐标截尾；med_krum.py：Multi-Krum 后坐标中位数；scc_krum.py：Multi-Krum 后分桶顺序裁剪；cc_tm.py：中心裁剪后截尾；cc_threshold.py：裁剪后调用 self.tm()，但类中仅定义 tm_modified()。 |
| 混合类 | gas.py：随机切分坐标，用子聚合结果计算距离总分，再选原向量平均；hybrid_aggr.py：串联筛选/变换，另有自适应加权选择类；hybrid_aggr2.py：按配置串联内部处理后平均；foundation.py：按到坐标极值向量的距离选更新复制，再执行截尾或中位数；lasa.py：范数裁剪、稀疏筛选，按层范数与符号筛选后平均裁剪值。 |
| 基础/辅助 | fedavg.py：等权平均；Bucketing.py：随机、余弦或 L2 分桶并桶内平均；base.py：同步/异步基类、均值及邻居加权实现；aggr_mapper.py：名称与参数工厂；`__init__.py`：空白。 |

未注册实现：ca.py、cc_lw.py、cc_threshold.py、cc_tm.py、ccangular.py；Bucketing.py 独立构造。

### 4. 已有攻击分类

目录：attacks/。

| 类别 | 成员文件与机制 |
|---|---|
| 标签/梯度 | label_flip.py：标签变为 C−1−标签，C 为 100（CIFAR100）或 10；cw.py：预测前两类选非真标签；bit_flip.py：梯度取负；gaussian_noise.py：梯度加高斯噪声。 |
| 统计/方向扰动 | alie.py：良性均值减 z 倍逐坐标标准差；ipm.py：良性均值取负并缩放；rop.py：融合历史聚合参考与均值，按角度构造扰动并迁移攻击位置。 |
| 距离约束 | minmax.py：搜索扰动尺度，使最大平方距离不超过良性两两最大值；minsum.py：搜索尺度，使平方距离和不超过良性最小距离和。 |
| 防御定向/组合 | fang.py：Krum 约束搜索或坐标极值构造，区分全/部分信息；local_model_poisoning.py：Krum 邻近偏移、截尾边界扰动、最远点外推、距离缩放、自适应尺度及噪声。 |
| 稀疏/分层 | sparse.py：掩码内外使用不同标准差扰动尺度；sparse_opted.py：固定掩码内扰动，按距离和约束搜索外部尺度；lasa_attack.py：按小幅值出现频次选位置，构造反向扰动并匹配各层中位范数。 |
| 模仿 | mimic.py：按指定位置、投影极值或概率复制良性更新，含在线变体。 |
| 基础/辅助 | base.py：全知基类及参考接口；attack_mapper.py：工厂；`__init__.py`：空白。 |

未注册：gaussian_noise.py 全部实现；mimic.py 的 OnlineMimicAttack。

### 5. 配置与实验入口

- 原生：python main.py；CLI 覆盖 config/parser.py:_build_parser() 默认值，无 YAML/JSON 加载。args_parser() 直接返回 Namespace；CLI 默认 lasa/lasa，FederationConfig 默认 sparse/tm（攻击/防御）。
- config/：base.py 管次数/设备/输出，federation.py 管参与率/策略；FLConfig 组合各领域 dataclass。
- 原生输出：Results/[save_loc]/实验名-随机ID/（相对工作目录），含 log.txt、指标 PNG、vecs/*.npy 均值、std/*.npy 标准差及可选掩码；另存 opted_z_vals-*.npy。
- FLGo：python run_flgo_byzantine.py --task ./toy_10 --create-toy --clients 10 --rounds 2；已有任务省略创建参数。CLI→option→flgo.init()→runner.run()；程序调用传 byz_*。
- 桥接 flgo_byzantine/algorithm.py：Server(BasicServer).iterate() 采样通信，Client=BasicClient；aggregate() 聚合服务器−客户端参数差后扣除，仅 sign 另乘步长。聚合选项 avg/cm/tm/krum/cc/rfa/sign，攻击 none/alie/ipm；恶意比例与假定数量独立。
- FLGo 输出：tests/test_flgo_bridge.py 检查 `<task>/record/*.json`；ByzantineLogger 追加参与数量、良性均值偏差和配置。

### 6. 不确定项

- FLGo 可用性：读 run_flgo_byzantine.py、requirements.txt，入口引用的 easyFL/ 未挂载，依赖表未列 FLGo；外部安装未知。
- 原生运行：读 data_loader.py、config/parser.py，访问的 args.kuacc 未定义；读 fl.py，零攻击者仍访问首个恶意客户端；未确认这些配置可运行。
- 参数可达性：读 aggregators/aggr_mapper.py、config/parser.py，scc/adaptive_hybrid 缺参数条目，LASA 字段命名不一致；未确认这些选项生效。
