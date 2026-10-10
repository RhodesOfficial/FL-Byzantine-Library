# D2′ 3.1 数值阻断：审查证据与报告勘误

日期：2026-10-10。只读审查；没有训练、改代码或运行项目测试。审查时HEAD为`b81a2b059085c9db90cd0253c9d158e62d3dd16d`。除读取代码/产物外，仅做JSON计数与一个两元素张量的数值算术核算。

以下`[事实]`为可定位记录，`[核算]`为按所列规则从保存记录计算，`[推断]`不冒充已证明的因果关系。

## E1．诊断没有产生完整资格M，但“full从未启动”须纠正

[事实] A/B分别执行2500/2000任务，两者`M`字段均为null，`endpoint`分别为0.095/0.100。这些不是原10400–12000末五点M。[A结果L4–8、48–49](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2500_attack/result.json:4>)；[B结果L4–8、47–48](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2000_attack/result.json:4>)。

[事实] `full_attack/failure.json`实际存在，记有JSON非有限值序列化异常、issued=880、terminated=840、tick=115、version=42；不是只有空目录。[中断记录L1–7](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/full_attack/failure.json:1>)。当前运行器将没有`--limit`的非smoke单元命名为`full_attack`，且使用完整预算。[运行器L154–166](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/scripts/run_d2_prime_phase3_attack.py:154>)；[目录命名L184–188](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/scripts/run_d2_prime_phase3_attack.py:184>)。

**勘误：**STATE的“full_attack不存在”不准确；“完整资格单元从未启动”不能继续作为已核实事实。应写“没有完成可用于资格判断的12000任务单元；另有full标识的早期中断尝试，需补齐其运行版本/调用参数”。未保存的v105口述记录不能覆盖这份v42存盘记录；二者是否不同尝试，尚待运行台账澄清。[原STATE L47](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_0_3_1_blocked/STATE.md:47>)；[阻断报告L48–54](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE3_1_BLOCKED_REPORT.md:48>)。

## E2．两次诊断的上传状态并不相同

以下仅统计**源版本>=70的恶意任务**，不是尚未运行的L1/L2/L3。恶意身份采用登记名单。[名单L23–24](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE3_0_CONTRACT_REGISTRATION.md:23>)。

| [核算] 指标 | A：diag2500 | B：diag2000 |
|---|---:|---:|
| 该子集任务数 | 440 | 228 |
| 合法到达数 | 440 | 228 |
| 到达且raw_norm恰为0 | 438 | 0 |
| 该子集过期数 | 0 | 0 |

计数源是对应`tasks.json`，条件为`identity属于登记恶意集 && source_version>=70`；合法到达为`arrived_at!=null`，零上传为`raw_norm==0`。[A逐任务记录L1起](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2500_attack/tasks.json:1>)；[B逐任务记录L1起](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2000_attack/tasks.json:1>)。

可逐条复核的锚点：

- [事实] A的task1421：候选范数9.701599250593846，源版本70；到达后raw_norm=0。[决策L436](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2500_attack/decisions.jsonl:436>)；[任务L32642–32661](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2500_attack/tasks.json:32642>)。
- [事实] B的task1414：候选范数9.701600090368476；到达后raw_norm=9.830239937923782，并被消费。[决策L436](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2000_attack/decisions.jsonl:436>)；[任务L32377–32397](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2000_attack/tasks.json:32377>)。

**勘误：**“退化区上传必全被抹零”不成立，B提供直接反例；“后期三段≈0%”是尚未运行到6001任务以后的外推，不是实测。B的线上重构范数还超过登记10B_M=9.701598816245317约1.33%，所以“候选被裁剪”也不能证明“服务器实际收到的原始更新严格满足同一资源上限”。[登记上限L14–15](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE3_0_CONTRACT_REGISTRATION.md:14>)。

## E3．过期身份、梯度与前向溢出的证据边界

[核算] A的650个过期任务、B的395个过期任务，**全部属于非恶意身份**；两份事件日志分别有650/395条`reject_packet(reason=vector)`，恶意端选择expire动作均为0。统计按任务身份与登记名单连接，不把向量拒绝与过期当两个训练任务。[A结果L13–15、35–38](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2500_attack/result.json:13>)；[B结果L13–15、34–37](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2000_attack/result.json:13>)；[A事件首个vector拒绝L37685–37689](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2500_attack/events.json:37685>)；[B对应事件L36650–36654](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2000_attack/events.json:36650>)。

[事实] `vector`拒绝包含类型、dtype、形状或元素非有限四种可能；该分支不终结任务，任务可随后按deadline过期。它没有“原始范数为0所以拒绝”的条件。[接收分支L118–127](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/async_baseline_state.py:118>)；[到期分支L91–101](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/async_baseline_state.py:91>)。

**勘误：**不能把20%–26%过期直接归因为“恶意上传抹零”。[推断] 这些记录与正常本地训练产生非法数值、回复被拒后到期相容，但须保存具体拒绝子原因/非有限元素数，不能只凭通用`vector`理由把类型/形状问题排除。

[事实] B的攻击梯度范数从v69到v104仍约2.80e19，没有在保存曲线中变为null；v104末段模型范数也在继续变化。A确有后段梯度范数null。因此报告L67“之后均溢出为inf”不准确。[B曲线L419–428](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_0_3_1_blocked/run3_diag2000_curve.json:419>)；[B曲线L629–632](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_0_3_1_blocked/run3_diag2000_curve.json:629>)；[A决策L436](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2500_attack/decisions.jsonl:436>)。

[事实] A/B分别在决策L428/L418已有正常本地模型差的范数null；当前日志清洗会把NaN与Inf都变成null，不能据此区分二者。[A决策L428](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2500_attack/decisions.jsonl:428>)；[B决策L418](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2000_attack/decisions.jsonl:418>)；[日志清洗L217–230](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/scripts/run_d2_prime_phase3_attack.py:217>)。

[事实] 评价器用`outputs.max(...)[1]`计正确率，没有先查logits有限；运行器保存正确数，未保存本次前向的非有限logit计数。[评价器L328–350](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/easyFL/flgo/benchmark/toolkits/cv/classification/__init__.py:328>)；[运行器评价L204–215](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/scripts/run_d2_prime_phase3_attack.py:204>)。

**边界：**“有限准确率不能保证前向有效”成立；“A/B的末点准确率都已经证明来自logits溢出”则证据不完整。本审查未执行保存模型的重新前向。若要补证，可只读重评保存终点模型并保留logits/逐样本CE有限性；这只能证明保存终点，不能恢复第一次失效时刻。

## E4．“纯合同冲突、实现已排除”的前提尚不成立

1. [事实] `_unit`用float64范数检查后，却重新以原dtype的`vector.norm()`除；裁剪分支有同类双范数口径。[归一化/裁剪L26–37](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/attacks/causal_joint_32.py:26>)。
   [核算] 对float32的两元素向量`(1e20,1e20)`，本机CPU算术得到float64范数1.4142135907151756e20、float32范数Inf、该除法返回`(0,0)`。这违反“有限、非小量输入应得到单位方向”。该反例不是CIFAR训练，也没有证明历史发散由它首先触发；正式设备仍须验此性质。
2. [事实] 攻击损失/梯度模型为float64；梯度先转float32再单位化。报告笼统说“全float32轨迹”不足以描述搜索数值口径。[评分与梯度L46–55、77–90](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/attacks/causal_joint_32.py:46>)。这不是服务器训练改成float64，但旧合同没有把搜索精度单列冻结。
3. [事实] 代理把候选delta直接装入更新队列，真实路径先形成float32上传模型，再由服务器相减重构。代理没有重放这次编码往返。[代理L49–62](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/async_attack_state.py:49>)；[实际封包L129–133](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/async_attack_algorithm.py:129>)；[实际解码L123–139](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/flgo_byzantine/async_baseline_state.py:123>)。E2给出了往返抹零与放大的实际锚点。

[推断] 这些足以否定“已排除数值实现/搜索代理问题”的强结论，尚不足以反向断言“修好它们一定恢复可学、一定能过3.1”。

## E5．同seed、同公共哈希，不等于相同有效执行或逐位轨迹

[事实] A/B的公共configuration_hash相同，但实际task_limit分别2500/2000；运行器在读取公共登记后以`--limit`覆盖预算和评价点，结果仍沿用公共hash。[A结果L2–8](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2500_attack/result.json:2>)；[B结果L2–8](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2000_attack/result.json:2>)；[覆盖L161–166、结果登记L260–274](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/scripts/run_d2_prime_phase3_attack.py:161>)。

[事实] A/B第10条决策、同task1/source0/t7，发布模型范数已分别为15.508710737250585和15.508710737042788。v67是明显放大的位置之一，**不是首次逐值不同**。[A决策L10](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2500_attack/decisions.jsonl:10>)；[B决策L10](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2000_attack/decisions.jsonl:10>)。

[事实] 两者第421条决策的task/time/source已不同，不能把完整“运行路径完全一致”当作事实；同一代码不是同一运行状态序列。[A决策L421](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2500_attack/decisions.jsonl:421>)；[B决策L421](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/diag2000_attack/decisions.jsonl:421>)。

[推断] 不同总长度不能直接解释预算未耗尽前的早期微差；CUDA归约、随机状态或其他数值因素尚未隔离。报告的“CUDA混沌放大”可以保留为假设，不能写作唯一已证原因。[原报告L56–69](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/docs/D2_PRIME_PHASE3_1_BLOCKED_REPORT.md:56>)。

[事实] 保存的smoke结果hash是`5c8de33c…`，不是当前`a01eb2e8…`；故不能无条件以这份smoke抵扣当前或修订版本的入口验证。[smoke结果L2](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_1_attack_20261010/smoke_attack/result.json:2>)。审查时当前源文件与现有preregister中的source_sha256均匹配；这只核对当前文件，不能补足已被覆盖版本的证据。

## E6．保存状态

[事实] STATE本身列出了未跟踪文档与代码，outputs被.gitignore排除。“已提交3.0”“工作树没有未跟踪内容”均不适用于这些资产。[STATE L13–31](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/outputs/d2_prime_phase3_0_3_1_blocked/STATE.md:13>)；[.gitignore L7](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/.gitignore:7>)。

[事实] 当前运行器在同名单元目录存在时删除它再建目录，这会覆盖历史证据。[运行器L184–189](<E:/Federated Machine Learning/FL-Byzantine-Library-astra/scripts/run_d2_prime_phase3_attack.py:184>)。后续保存约束必须禁止这种覆盖；审查本轮没有删除/移动/提交任何既有文件。
