# 交付单：G1.2 第二段 全20端正式测量与全端目标诊断

- 对应任务单的基准 commit：bfec9265ad57ac66fd45b90472e572a0e0eda0d3（当前输入13fb24f7865f3a9f3303bdaafb10ae0afbaf8e2b，已验证祖先关系）
- 本次交付 commit：见本提交

## 做了什么（≤5 条）
- 按冻结W02、四个固定参考和两份封存任务，顺序完成全部20端的单次正式测量。
- 保存80份完整float32端消息、一次编码的特征、NumPy float64类均值及独立逐样本外积全端参照。
- 落实2e-6通过线，完成自检、消息严格读回、状态/BN及重复读回检查，并核验全部归档哈希与唯一索引。
- 自动记录预登记、输入身份、累计限额、成本和逐项自评；归档核验时间/写入并入同一累计账本。
- 准备P方案，未运行探针；只自评G1.2，未裁决来源偏差或方法收益。

## 产出文件
- `artifacts/direction_a/phaseG1_2_full_v1/`（下称F）：本轮完整证据，旧smoke包保持原样。
- `direction_a/class_gradient_full.py`：冻结容差、全端加权、独立逐样本解析总和及累计资源保护。
- `scripts/measure_direction_a_class_gradient_full.py`、`scripts/verify_direction_a_full_archive.py`：单次测量及归档校验/累计记账。
- `tests/test_direction_a_class_gradient_full.py`：不等来源权重手算、独立外积及冻结容差边界测试；连同既有手算/有限差分自检在正式进程内运行，见F/selfchecks.json。
- `scripts/direction_a_P_plan.md`：脚本写入F/P_plan.md的方案原文。

## 判据自评
| 判据编号 | 结果 PASS/FAIL | 证据位置 / 关键数字 |
|---|---|---|
| 1 | PASS | F/reference_acceptance.json；四点原包/封存任务/生成与验证记录对应，模型/BN前后及重复读回哈希严格相等，无参数梯度/更新。 |
| 2 | PASS | F/measurements.json；逐点0–19端；C10每点11165样本/85正类，C100每点9754/593；80扫描、41838编码、1356完整主梯度、220个G_c，缺类列表无伪消息。 |
| 3 | PASS | F/preregistration.json、environment.json、W02_measurement.json；完整train一次、encode/head=128、eval float32纯CE、CPU float64累加/n_ic后float32消息；范数全部分母/统计齐全，端内无抽样噪声。 |
| 4 | PASS | F/measurements.json、archive_verification.json及diagnostics/；1356主比较最大3.1449943e-7，480辅助比较最大3.5667195e-7，均≤2e-6；每端最小/最大存在类前≤8样本，含逐样本均值和CPU/CUDA对照。 |
| 5 | PASS | F/measurements.json的provenance及diagnostics/；220个G_c与4个等权G共224比较，最大1.9243839e-7；独立逐样本外积求和/N_c；来源ID/计数/权重齐全，权重和误差最大0，L2已记录。 |
| 6 | PASS | F/run_record.json、W02_measurement.json、artifact_hashes.json、archive_verification.json；80消息唯一定位，原归档93文件哈希通过，最终索引纳入账本与归档校验；实际资源见下。旧第四点计时仍缺失。 |
| 7 | PASS | F/P_plan.md；四点、训练/验证隔离、均衡头/原头/无信息对照、τ_probe事前确定与成本/额度申请程序齐全，无实测门槛或P运行。 |

## 实际资源消耗
- 程序累计30.499秒（正式进程26.703秒，归档校验3.796秒）；CUDA allocated峰137180160 B，Windows working-set峰1570463744 B，CPU已知数组/张量保守代理峰815032704 B。
- 新证据累计写入253510045 B（含覆盖及128 KiB应急预留），逻辑上下行165341908 B；均低于256 MiB。纯张量、容器元数据、理论下行和诊断成本在F/W02_measurement.json分账。
- 前向3014、求导/梯度请求各2646、统计扫描9621；80端扫描/41838编码，额外编码0；正式运行1、失败重跑0、实现修订1；训练attempt/优化器/搜索0。
- 旧成本引用原smoke及resume账本单列；C100 r80旧逐端计时为null，没有回填。

## 阻塞
无

## 异议
无

## 需要审查者裁决的问题（≤3 条，没有写“无”）
无
