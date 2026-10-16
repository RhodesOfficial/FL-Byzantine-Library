# G1.1 现有证据资格对照与关闭缺项 v3

输入任务基准：`b249067cb36d95f18188ee110f7db1a9eef42a73`；现行交接/开工HEAD：`91d1f260e0d75ed1b926ba6fc922ae978eff5033`，前者为后者祖先。
原要求：该HEAD的`docs/DIRECTION_A_CHECKPOINTS_v1.md`共用规则及G1.1/G1.3；合同`docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md`§四W01–03/W07、E01–04、§六和§七现行补充。
本文只作资格申请，正式G1.1仍未通过，G1.3仍未放行；v1/v2及历史交付保留。

## 输入定位与结论口径
- F＝`b37efe0f53f899131b76926d681132af7b90f6b2:artifacts/direction_a/phaseG1_1_formal_F_resume_v1/`；F交接＝同commit的`docs/workflow/TO_REVIEWER.md`。
- C＝`76ce7f5a490be24a084fe87a666c09d308e3be01:artifacts/direction_a/phaseG1_1_resource_closure_resume_v1/`；C交接＝同commit的`docs/workflow/TO_REVIEWER.md`。
- R＝`b249067cb36d95f18188ee110f7db1a9eef42a73:artifacts/direction_a/phaseG1_1_carry_record_repair_v1/`；D3续接旧结论见`5174b06bb1a6d90e58ed6e07b5ab6e88e283f269:docs/DIRECTION_A_G1_1_QUALIFICATION_v2.md`及当前HEAD裁决v8。
- M＝`22c7418d40f62c81f2639e86d1b7a166a6898920:artifacts/direction_a/phaseG1_1_cost_M_v1/`；M已通过的依据为当前HEAD的`docs/DIRECTION_A_G1_1_ADJUDICATION_v3.md`§一/二。
- 本轮只读F六个允许的摘要、C两份汇总、R两份记录及指定文档；定向Git差异确认F/C/R目录自各自输入commit至HEAD无内容变更。
- 下表PASS指原识别前提有现成证据支持；逐事件/原支持表核验沿历史F判据1–6/8及本单裁决引用，未重新检验。历史资源和正式关闭资格另表列FAIL。

## 原G1.1要求→证据→现有结论→残余缺项
|原要求|输入路径/字段或历史裁决|结论|现有结论及残余缺项|
|---|---|---|---|
|全目标端注册及最终训练计数|F交接判据2；F/input_checks.json#checks的两任务counts/registration定位；合同W03|PASS|两任务40端ACK/计数/split绑定，注册先于attempt；本轮不读取注册明细，沿历史裁决，资源处置仍待审|
|所有n_ic>0来源q>0|F/mechanism.json#mechanism.q；F交接2的4068正来源场景|PASS|均匀无放回20邀8，q=2/5；有限未返回不能判永久缺席；逐来源对应引用历史支持表裁决|
|所有n_ic>0来源r>0及近似误差|F/mechanism.json#probability_formula,lower_r,lower_p,continuous_error_r_bound,continuous_error_p_bound；F交接2/3|PASS|整数/有理数格点，r=A*H*K/N^3、p=(2/5)r，正下界及连续误差已登记；不是经验率估计，未新增概率计算|
|计划邀请与有效完成逐条对应|F交接4/8；F/replay_checks.json#all_identical,trajectories；F/delivery_readback.json#replay_pairs,mapping_entries_exact|PASS|384生成/384主回放一致，含覆盖共388回放对，120映射项精确；逐条事件关系引用已通过裁决，本轮未扫描events|
|空返回仍记日志和预算|F/coverage.json#coverage的empty,round,round_after；F交接4/6；C/fees.json#preparation_includes_failed_dispatches,generation_and_replay_counted|PASS|空attempt不推进round；掉线/超时仍计准备、生成与回放均计费；原计费前保护失败保留，不能据此称预算整体PASS|
|三种分配保持同一速度集合|F交接3；F/delivery_readback.json#mapping_entries_exact；合同E02/裁决v3§二|PASS|random/tail_slow/tail_fast沿原映射，各10×1+10×4；120项对应引用历史精确核验，无按收益重排|
|固定工作量含新增计算|M裁决v3§一2–5及§二；F交接6指run_record.simulated_costs；合同W01/W02|PASS|每派发5步普通训练、完整W02及消息准备，失败派发不免账；绑定M实测b/L，F仅模拟引用，不声称F重训或新测梯度|
|真实概率诊断通道单独审计|F/diagnostic_channel_audit.json#status,diagnostic_inputs,invitation_inputs,return_inputs,prohibited_fields_rejected；F/coverage.json#rejections|PASS|status=passed；r/p、未观测U留模拟侧，策略只取已注册ID及计划/允许返回；diagnostic_leak按schema拒绝；沿历史消费路径裁决|
|按时返回覆盖|F/coverage.json#coverage及boundaries.checks|PASS|returned终态与格点前后/有理数等号夹具明确；夹具不冒充真实轨迹观测|
|未派发覆盖|F/coverage.json#rejections(probe=undispatched,reason=undispatched)及coverage的offline|PASS|未派发返回被拒绝；计划先于在线过滤的对应引用F判据3/5，不另扫事件|
|掉线覆盖|F/coverage.json#coverage(generate/0、2及对应replay)|PASS|有dropout终态及全掉线空返回，准备计费引用F判据6|
|超时覆盖|F/coverage.json#coverage(generate/0、replay/0)及boundaries|PASS|L_override=1的合成timeout与边界覆盖已封存；不能说主轨迹所有端都超时或用夹具代替主轨迹事实|
|全失败覆盖|F/coverage.json#coverage(generate/1、2及对应replay)|PASS|全offline和全dropout均empty=true，round保持1；未免除该次attempt与费用|
|同round不同attempt覆盖|F/coverage.json#plans.attempt及coverage.round,round_after|PASS|attempt 1、2均停在round 1，随后attempt 3从round 1到2；回放相同，不把round当attempt|
|预先固定轨迹及冻结身份|F/input_checks.json#preregistration_precedes_entry,source_commit,authorization；F/replay_checks.json#actual_updates|PASS|源码/预登记4af17eb先于入口，授权befac4e；S1固定、实际更新0；12轨迹不是12独立研究重复|

## 四种资格与历史失败处置
|层面/历史项|结论|依据、影响与仍需处置|
|---|---|---|
|778项结构接收|PASS|F/delivery_readback.json#complete,partial,not_started=778/0/0；历史F1–6/8通过，包身份保持；只保留已封存结构，不等同正式整体通过|
|现有科学前提证据|PASS|上表分别有注册、支持、对应/覆盖、工作量与隔离依据；资源估算错误没有提供这些字段作假的证据，不据此一概否定；本轮无来源偏差新结论|
|F7|FAIL|F交接7及delivery_readback的issue/stopping_category：启动前全流程包络不保守；实际未超硬限不能补成合规，科学前提证据可引用，未来不得沿用该估计启动|
|旧封账5|FAIL|C/accounting.json#historical_FAIL.previous_closure_criterion_5及prior_once；辅助失败/费用封账不完整的历史事实保留，C成功汇总仅补齐费用证据，不回写旧判据|
|费用恢复4|FAIL|C/accounting.json#new_segment_failed_identity_process_peak,historical_joint_peak,history_counts.auxiliary_revision_exact均null；resource_basis.metadata_plan_compliant=false；限制历史资源合规/可复制运行资格，不推出事件或支持为假|
|旧D3 1–5|FAIL|资格v2历史边界及R/workflow_audit.json#retained_FAIL；原有限准备缺账按现行规则局部登记，不算新守卫失效，也不追认旧通过；原段未完成验证，后续验证另给证据|
|旧续接3|PASS（新证据补齐）|R/reader_receipt.json#status,payload.assertions,per_field；11项均真，快照17/39/52/9/272，后账20/42/55/12/275；旧落盘记录仍原样，非旧程序资源合规证明|
|旧续接5|FAIL|裁决v8及R/workflow_audit.json#old_criterion5；实际工程/修订4/4超过当时3/3，新授权仅向前生效|
|R新段1–6|PASS|当前任务单逐条裁决、R/workflow_audit.json#current_self_assessment及reader_receipt；只证明定点快照和独立落盘回读、该段计次/保护，不自动证明正式事件程序具备新辅助守卫|
|未来正式运行资格|FAIL|正式入口/费用均2/2，正式修订语法CPU各3/3；D3工程/修订6/6，语法4/6、CPU2/6但本单全0；合成通过不开放真实入口，不以新峰填旧null|

C/fees.json#U=34871421077 B、U_minus_limit=511682709 B，是旧费用口径的替代保守上界及相对32 GiB的缺口；不是新增实耗或必需费用下界。
本轮只引用两数，不重算费用；不能据U直接断言实际越限，亦不能把上界缺口当成已证明至少需要扩到33 GiB。旧账只结转一次，历史FAIL/null保持。

## G1.1最小关闭条件及唯一下一步建议
现有摘要和历史裁决足以支持上表原识别前提的受限接收；缺的是正式关闭时对合同§七历史资源FAIL适用范围的明确裁决，不是再造事件或重测支持。
唯一建议：提交一次“带限制关闭G1.1”申请，由审查者逐项确认原识别前提，并明确仅接收F既有静态机制/封存事件作为后续识别输入，历史资源FAIL及null独立保留、运行资格继续关闭；本执行单不自行批准。
最小剩余条件：审查者明确该证据接收可满足原G1.1而不宣称§七历史全合规，并记录F7/封账5/恢复4/旧D3/旧续接5的保留处置。若§七整段合规是不可分割的关闭必要条件，须据该条驳回本申请，缺证即历史前置保护/峰/次数，现有包无法补造。
不以辅助合成覆盖正式入口保护；若审查者要求新正式运行、豁免冻结合规要求或增加资源/次数，属于新冻结授权，才提交具体作者决策；本次不请求该变更、不重复索取D3授权。

## G1.3原要求的输入与未放行缺项
|原输入/要求|现有定位|结论及缺项|
|---|---|---|
|G1.1＋G1.2先通过|本表及当前STATE；F/input_checks.json#reference_acceptance_locator指G1.2既有包|FAIL：G1.2已通过，G1.1正式关闭仍待本申请裁决；P全范围FAIL不替代这条依赖|
|每类持有端数、来源梯度、全端/可用性目标|0.2 counts与G1.2 measurements/参考，均由F/input_checks.json#checks定位；F机制支持|FAIL：具备旧输入定位，本轮不读梯度/支持原表，未交付G_avail−G逐类范数/相对量及完整来源差异结果|
|主场景、三速度配对、多参考、全类/尾类/逐类汇总|合同E02、四参考及S1；F/replay_checks.json#trajectories|FAIL：事件配对已有，来源偏差汇总规则及数值交付未齐；79端无超时仅为风险，不证明偏差存在或不存在|
|预定ε_bias、误差与重复核验|合同§六ε_bias和重复上限仍待登记；共用规则至少3配对种子|FAIL：须在正式偏差结果前冻结实质阈值/汇总、至少3配对种子的上限/区间或明确获准的概率误差核验方案；S1轨迹不冒充重复，S2/S3未运行|
|零范数分母、单来源/近同梯度、均匀概率零对照|检查点G1.3判据4；合同§六ε_num仅已覆盖0.2/G1.2对象|FAIL：G1.3归一化/零分母规则、适用容差、退化标注和均匀对照误差结果未交付；非均匀概率不预设必定非零|
|阶段预算与正式放行|合同§七、当前任务单零运行分配|FAIL：无G1.3新计算授权；须先裁决G1.1并冻结下一段参数/误差/预算，才可另派；本轮不登记新参数|

本单无须作者立即拍板；技术性资格裁决先交审查者。科研推进限于明确识别前提的证据范围，未证明来源偏差或方法收益。
到M仍缺G1.1正式关闭、G1.3、G2、T、G3（含P全范围资格障碍）及4.1/4.2；本表下游FAIL是缺项说明，不计作本单五项自评FAIL。
