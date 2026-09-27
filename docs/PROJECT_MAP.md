# FLGo 项目地图

范围：当前挂载源码的静态核对；不含原生入口；未读取论文/PDF，未运行实验。

证据简写（路径相对主库，冒号后为行号）：`B`＝`flgo_byzantine/algorithm.py`，`R`＝`run_flgo_byzantine.py`；以下均位于 `easyFL/flgo/`：`F`＝`utils/fflow.py`，`S`＝`algorithm/fedbase.py`，`P`＝`benchmark/base.py`，`U`＝`utils/fmodule.py`，`L`＝`experiment/logger/__init__.py`。

## 1. 运行时骨架

- 位置：主库 `E:/Federated Machine Learning/FL-Byzantine-Library-astra`；依赖为其 `easyFL/`。实见 easyFL 顶层 `docker/ docs/ example/ flgo/ resources/ tutorial/`；FLGo 源码为 `easyFL/flgo/{algorithm,benchmark,decorator,experiment,simulator,utils}/` 和 `__init__.py`，不是 `resources/algorithm/`。入口优先把本地 easyFL 加入导入路径（R:17–20）。
- 生成：R:`main()` → `flgo.gen_task_by_()`（F:559–617）→ benchmark 的 `core.TaskGenerator/TaskPipe` → `generate()`、`create_task_architecture()`、`save_info()`、`save_task()`；创建分区任务。
- 初始化：R:125–127 → `flgo.init(task, flgo_byzantine, option, Logger=ByzantineLogger)`（F:697）→ 读取任务 `info`，加载数据、默认模型、计算器 → `TaskPipe.generate_objects()` 实例化桥接 Server/Client、`distribute()` 分发数据 → 模型初始化、通信器/模拟器初始化 → B:`Server.initialize()` → 返回 server 作为 runner（F:800–940、1010；P:178–204）。
- 每轮：继承的 `BasicServer.run()`（S:293–327）→ B:`Server.iterate()`（109–117）→ 继承的 `sample()/communicate()/pack()` → `VirtualCommunicator.request()` → `BasicClient.reply()` → `unpack()`、`train()`、`pack()` → 服务端 `unpack()` 收集模型。客户端 `train()` 通过任务计算器计算损失并更新参数（S:364–487、910–1001；`easyFL/flgo/__init__.py`:7–17）。
- 更新：B:`aggregate(models)` → `_parameter_vector()` → `_attack_update()`（有恶意响应时）→ `_build_aggregator()`/缓存实例 → 实例 `__call__(updates)` → `_model_from_update()` → `iterate()` 写回 `self.model`；随后 runner 评估、推进轮次/学习率，结束时保存 JSON（B:119–156；S:308–327）。

## 2. 扩展点清单

### 聚合器扩展

- **算法实现**：在 `aggregators/<组件>.py` 定义继承 `_BaseAggregator` 的类，实现 `__call__(self, inputs)`；返回一个聚合 Tensor。基类无强制构造参数，`get_attack_stats()` 默认返回 None（`aggregators/base.py`:4–20；`aggregators/fedavg.py`:4–11）。
- **桥接注册**：在 B 导入该类，将小写名称加入 `AGGREGATORS`，并在 `_build_aggregator(name,n,f,option)` 增加构造分支和所需输入条件。现有工厂最后直接返回 RFA；只添加集合名称会落到 RFA 分支（B:19–30、52–74）。
- **配置接线**：组件参数由工厂从 `option` 读取；需要命令行设置时，在 R 的 parser 和 option 字典同时增加参数。CLI choices 自动取桥接集合，无须另加名称列表（R:70–83、107–126）。
- **注册边界**：桥接直接 import 算法类，没有另写聚合算法，也不调用 `aggregators/aggr_mapper.py`。此 FLGo 链只在桥接层注册；修改库内同一类会被桥接复用，仅改库 mapper 不会新增 FLGo 可选项（B:19–25、52–74、145；`aggregators/aggr_mapper.py`:37–62）。
- **状态与上下文**：缓存键只对 krum 包含人数。新组件若构造时固定 n，接线还须覆盖缓存键中的 n，否则响应人数变化仍使用旧实例。额外上下文须在 B 的工厂/`aggregate()` 接线，当前没有自动注入机制（B:137–145）。

### 攻击扩展

- **算法接口**：库内全知攻击继承 `_BaseByzantine(client)`，`omniscient_callback(self,benign_gradients)` 将结果存入 `self.adv_momentum`；父客户端构造需要 `id,dataset,device,args`。但 FLGo 桥接不实例化这些攻击客户端（`attacks/base.py`:11–30；`client.py`:39–67；`attacks/alie.py`:21–35；B:26–27、159）。
- **FLGo 可复用部分**：在 `attacks/<组件>.py` 提供造假更新函数；现有 ALIE/IPM 类与桥接共用同一函数，而非桥接独立实现。仅新增 `_BaseByzantine` 子类或修改其回调，不会自动进入 FLGo（`attacks/alie.py`:7–18、32–35；`attacks/ipm.py`:4–17；B:77–84）。
- **桥接注册**：在 B import 造假函数、加入 `ATTACKS`、在 `_attack_update(name,benign,n,m,option)` 增加调用分支；返回单个恶意更新向量。按需在 R 接入参数。库 `attack_mapper` 不参与此链，名称无需在那里重复注册（B:26–31、77–84、132–136；R:71、107–126；`attacks/attack_mapper.py`:22–40）。
- **攻击类型边界**：当前桥接是服务端全知更新替换；没有恶意 Client、标签投毒、本地训练替换或每个攻击者不同返回值的适配。需要这些语义时，现有单向量分发接口不能直接表达（B:128–136、159）。

## 3. FLGo 桥接契约

### 对象与调度

- B:`Server(BasicServer)`；`Client = BasicClient` 是别名。两个 easyFL 基类均继承 `BasicParty`；桥接覆盖 `initialize/iterate/aggregate`，训练与主循环由 easyFL 提供（B:17、87–159；S:258、293、870）。
- **FLGo 算法接入**：`flgo_byzantine/__init__.py`:8–10 导出 Server/Client；F:`init()` 接收模块/类，P:`generate_objects()` 读取 `algorithm.Server/Client`。本链不是字符串中央注册表；F 还注入 gv/TaskCalculator 并包装模拟器行为，无须修改 easyFL（F:875–925；P:188–204）。
- **边界签名**：`Server.iterate(self)` 无参数，有响应则令 `self.model=self.aggregate(models)` 并返回 True；无响应返回 False，runner 不推进轮次。`aggregate(self,models:list,*args,**kwargs)` 接收本轮已训练模型列表，返回完整模型对象，空列表返回当前模型（B:109–123；S:308–323）。
- **顺序**：`models[i]` 对应 `received_clients[i]`。模拟器 `with_clock` 按有效响应重排并更新 ID 列表；桥接检查二者长度。这里是实际收到人数，不是配置的总人数或最初选中人数（`easyFL/flgo/simulator/base.py`:660–665；B:122–140）。

### Tensor 与模型

- `FModule` 是 `torch.nn.Module` 子类，提供模型运算；本桥接没有调用 U 的 `_model_to_tensor/_model_from_tensor`，使用 PyTorch 参数向量工具（U:4–43、275–306；B:34–49）。
- 设 D 为全局模型全部 `parameters()` 元素数，n 为响应数。桥接按参数迭代顺序展平并 detach，得到 `base:[D]`；每个输入为 `base-client_vector.to(base)`。聚合器收到 `List[Tensor[D]]`，不是层列表、完整模型、原始梯度或客户端对象（B:34–38、124–125）。
- 输入包括冻结参数，不含 `buffers()`；客户端必须与服务器参数布局一致。桥接拒绝无参数模型和非有限原始更新；模型名称/各层形状没有另行核对（B:34–38、124–127）。
- **返回合同**：`__call__` 必须返回与 `base.shape` 完全一致的有限 Tensor，不能返回模型、列表、元组或 None。设备/类型保持与输入一致，使误差计算可执行；最终写回还会 `.to(current)`。桥接不会替组件做按层拆装（B:145–156、41–49）。
- 写回深拷贝旧全局模型，在 `no_grad` 中设置 `parameters=base-aggregate`；buffer 保留旧全局副本。普通更新不再乘学习率；仅 `sign` 乘 `byz_server_step`，缺省取 `option['learning_rate']`（B:41–49、148–156）。
- **与基类比较**：Tensor 调用形态一致；`_BaseAggregator` 文档写“in-place”，桥接实际消费返回值，不能仅原地改 inputs。更新语义是模型差值；库客户端的 `get_grad()` 则返回动量/Adam 处理量。桥接不传样本权重、客户端 ID、层边界、根数据或模型，也不调用 `get_attack_stats()`（`aggregators/base.py`:10–20；`client.py`:159–173；B:124–156）。

### 注册项与生命周期

两个“注册表”均为 `frozenset[str]`，条目本身没有函数签名。实际接口是 `_build_aggregator(name:str,n:int,f:int,option:dict)` → 可调用实例，及 `_attack_update(name:str,benign:Sequence[Tensor],n:int,m:int,option:dict)->Tensor`（B:30–31、52、77–78）。所有聚合实例统一调用 `__call__(self,inputs)`。

| 聚合名称 | 工厂调用及条件（B:55–74） |
|---|---|
| avg | `fedAVG()` |
| cm | `CM()` |
| sign | `SignSGD()` |
| tm | `TM(b=f)`；f>0，n>2f |
| krum | `Krum(n=n,f=f,m=n-f-2)`；f>0，n≥2f+3；mk默认True，即Multi-Krum（`aggregators/krum.py`:94） |
| cc | `Clipping(tau=float(option.get('byz_clip_tau',1.0)),b=f)`；n_iter默认1（`aggregators/clipping.py`:7） |
| rfa | `RFA(T=int(option.get('byz_rfa_steps',5)),nu=float(option.get('byz_rfa_nu',1e-6)))` |

- f=`byz_assumed_count`，初始化检查非负，独立于真实攻击人数。实例首次聚合才构造，按 `(名称, krum时的n否则None, f)` 缓存；键不变则保留跨轮状态。键不含 D、设备、其他参数或客户端身份；传给实例的只有 updates，成员/顺序可能跨轮变化（B:95–107、139–145；S:552–556）。
- 输入顺序没有“恶意在末尾”保证；库中 TM/Krum/CC 的部分统计按末尾恶意计数，桥接不读取这些统计，而用真实 ID 记录本轮人数和良性均值误差（B:128–155；`aggregators/trimmed_mean.py`:24–35；`aggregators/krum.py`:112–129；`aggregators/clipping.py`:41–53）。

| 攻击名称 | 实际签名/行为 |
|---|---|
| none | 不调用 `_attack_update`，初始化恶意人数为 0（B:102、132） |
| alie | `craft_alie_update(benign_gradients,n,m,z=None)`；返回均值−z×逐坐标标准差；至少两个良性更新且0<m<n；z 缺省由 n、m 计算并检查分位合法性（`attacks/alie.py`:7–18） |
| ipm | `craft_ipm_update(benign_gradients,epsilon)`；返回−epsilon×良性均值；至少一个良性更新（`attacks/ipm.py`:4–8） |

- B 分发器从 `byz_alie_z`/`byz_ipm_epsilon` 取参数，后者缺省 1.0。初始化按 `byz_seed` 随机固定 `floor(比例×总客户端数)` 个恶意 ID；每轮 n 是实际响应数、m 是其中恶意数、benign 长度为 n−m。只有 m>0 才造假；同一个 `[D]` 结果 clone 后替换全部恶意位置。攻击函数没有持久实例、模型、ID或数据入参；造假之后没有单独的逐输入形状/有限性检查（B:77–83、98–104、124–147）。

## 4. 已有聚合器分类

以下覆盖 `aggregators/` 全部文件；文件后数字为机制实现行号。**✓为桥接注册；其余均未注册**（注册证据 B:19–30、52–74）。类别按代码操作归组。

| 类别 | 成员文件与机制 |
|---|---|
| 距离类 | ✓`krum.py`:103：近邻距离评分选取后均值；✓`rfa.py`:9：平滑 Weiszfeld 迭代；`dnc.py`:104：随机子空间奇异向量投影筛选；`fedredefense.py`:100：按归一化重构误差筛选。 |
| 截断类 | ✓`cm.py`:9、`ca.py`:6：逐坐标上下中位数平均；✓`trimmed_mean.py`:15：移除坐标两端后均值；`tm_abs.py`:62：按绝对值截两端；`tm_capped.py`:18：裁到中间区间边界；`tm_cheby.py`:42：均值±k倍标准差裁界；`tm_history.py`:24：截断结果加入历史更新；`tm_perfect.py`:23：先排除末尾b项再截坐标。 |
| 截断类 | ✓`clipping.py`:33：围绕持久中心裁范数；`cc_lw.py`:20：逐层中心裁剪；`ccangular.py`:14：计算余弦但把系数置1后裁剪。 |
| 聚类类 | `cc_seq.py`:127：分桶后顺序裁剪；`cc_seq_ecc.py`:85：两组桶结合固定/移动参考裁剪；`cc_cluster.py`:154：分桶轮换、更新多参考后平均；`Bucketing.py`:16：随机/距离分桶取均值，返回缩短的列表，非最终聚合器。 |
| 信誉类 | `fl_trust.py`:36：根数据参考梯度的正余弦信任和范数归一；`foolsGold.py`:70：历史/当前更新余弦相似度权重；`fl_defender.py`:92：相似度PCA与历史信任加权；`fldetector.py`:201：历史距离/预测误差分组后取中位数。 |
| 符号类 | ✓`sign_sgd.py`:9：逐坐标符号多数票；`signguard.py`:169：范数筛选与符号聚类交集后裁剪均值；`fedseca.py`:252：符号选举、裁剪稀疏化、同向坐标平均。 |
| 混合类 | `bulyan.py`:24：Multi-Krum后坐标截断；`med_krum.py`:32：Multi-Krum后中位数；`scc_krum.py`:172：Multi-Krum后分桶裁剪；`cc_tm.py`:34：中心裁剪后TM；`cc_threshold.py`:36：裁剪后调用未定义的self.tm。 |
| 混合类 | `gas.py`:100：坐标分组基础聚合、累加距离筛选后均值；`foundation.py`:65、121：复制距坐标极值较远的更新，再TM/中位数；`hybrid_aggr.py`:300、370、517：顺序筛选/变换及自适应选择版本；`hybrid_aggr2.py`:212：串联筛选/裁剪后均值。 |
| 混合类 | `lasa.py`:207：裁剪、稀疏检测、逐层范数与符号筛选；`flame.py`:97：余弦聚类、范数裁剪及可选噪声；`skymask.py`:143：根梯度参与掩码权重训练、分组后均值。 |
| 均值/基础设施 | ✓`fedavg.py`:9（avg）：等权平均；`base.py`:4–73：基类、Mean/AsyncMean/图邻居加权；`aggr_mapper.py`:37–140：库内名称/构造参数映射；`__init__.py`：空包初始化。 |

## 5. 已有攻击分类

覆盖 `attacks/` 全部文件。**只有 alie.py、ipm.py 的造假函数已桥接注册**；none 是关闭开关，其余文件/类均未接入（B:26–31、77–84）。

| 类别 | 成员文件与机制（行号） |
|---|---|
| 统计/方向操纵 | ✓`alie.py`:7：均值减标准差扰动；✓`ipm.py`:4：良性均值反向缩放；`rop.py`:24：结合全局动量/良性均值定位并旋转扰动。 |
| 距离约束 | `minmax.py`:27：搜索满足最大成对距离约束的扰动；`minsum.py`:27：搜索满足距离和约束的扰动。 |
| 防御定向/混合 | `fang.py`:24：按聚合类型及MITM选Krum选择搜索或坐标极值/统计边界；`local_model_poisoning.py`:20–428：Krum/AdaptiveKrum、TrimmedMean/LocalTrimmedMean、EdgeCase、LocalMinMax、Stealthy分别使用近邻、坐标边界、外推、距离尺度或噪声组合。 |
| 稀疏/分层 | `sparse.py`:39：掩码内外不同标准差扰动；`sparse_opted.py`:19：固定大扰动、按距离和搜索其余强度；`lasa_attack.py`:18：按小坐标出现频率选位置并按层范数定标。 |
| 模仿 | `mimic.py`:18–330：复制指定、投影选择或自适应抽样的良性更新，含Mimic、Variant、Adaptive、Online四类。 |
| 本地训练/数据 | `bit_flip.py`:4：反转梯度；`gaussian_noise.py`:4：梯度加高斯噪声；`label_flip.py`:4：标签映射为类别数−1−原标签；`cw.py`:10：从模型前两名预测选替代标签计算损失。 |
| 基础设施 | `base.py`:11：攻击客户端基类；`attack_mapper.py`:22–40：库内攻击映射/构造；`__init__.py`：空包初始化。 |

## 6. 配置与实验入口

- 启动示例：`python run_flgo_byzantine.py --task ./toy_task --create-toy --clients 10 --aggregator krum --attack alie --malicious-fraction 0.2 --assumed-count 2 --rounds 2 --proportion 1 --alie-z 0.5`。已有任务仅传 `--task`；创建开关仅在任务不存在时生效。MNIST 支持 iid/dirichlet 与 alpha；toy 固定 IID（R:57–105）。
- CLI→option：aggregator/attack/malicious-fraction/assumed-count/clip-tau/ipm-epsilon/alie-z 对应 `byz_` 下划线键；seed 同时给 seed/byz_seed；rounds→num_rounds、epochs→num_epochs；proportion/learning-rate/gpu 控制参与率、学习率和设备。入口固定 sample/aggregate 为 uniform；桥接聚合不调用基类加权路径（R:107–127；B:145）。
- F:772–788 保留自定义键。`byz_rfa_steps/byz_rfa_nu/byz_server_step` 只有字典入口，R没有对应CLI。默认5轮、1 epoch、学习率0.1、全参与、CPU、avg/none；ALIE z自动、IPM epsilon=1、clip tau=1（R:65–83；B:73–83、148–150）。
- `config/{defense,attack,model}.py` 是库数据类；`model_registry.py:get_net()`、`data_loader.py:get_dataset/get_indices()` 不被本入口调用。FLGo模型/数据由任务benchmark提供：MNIST默认cnn，toy默认线性FModule（R:20–24、91–126；F:803–816、856–910；对应benchmark的 `__init__.py/core.py/model`）。桥接也不调用 `fl.py/mapper.py`；但攻击函数的模块导入会经 `attacks/base.py`:1–3加载 `client.py/utils.py`，不代表实例化库客户端（B:19–27、159）。
- 输出 `<task>/record/*.json`，包含普通评估、option、攻击配置及每轮响应数/恶意数/良性均值误差；默认还记录初始评估。文件名含DEF/ATK/MR/F及byz配置SHA1前8位；默认同名可覆盖。CLI未开启日志文件或checkpoint（R:27–54；S:298–327；L:2145–2159、2207–2226、2304–2309；F:179–186）。

## 7. 不确定项

- 已定位全部指定职责：任务生成/初始化在F、基类/主循环在S、参数模型在U；未找到本链独立算法注册表或runner文件，职责由F与P的模块属性实例化、S.run承担（另读 `easyFL/flgo/algorithm/__init__.py`，为空）。
- 未执行环境安装或训练，无法从源码确认当前依赖/设备下每个组件实际可运行；“已注册”仅指接线成立。已读 `tests/test_flgo_bridge.py`:51–75，现有测试覆盖avg对齐与krum+alie流程，不能据此宣称全部组合验证通过。
- `cc_threshold.py`:47调用self.tm，但该文件只定义tm_modified；`ca.py`:2使用顶层base导入。不能仅凭这些文件确认它们可独立导入/执行；分类只陈述实现操作。
- 桥接无checkpoint状态扩展，S:804–842未保存聚合器实例；[推断] 有状态聚合器恢复后的轨迹不能仅靠全局模型checkpoint保证延续（B:106–107、139–145）。
