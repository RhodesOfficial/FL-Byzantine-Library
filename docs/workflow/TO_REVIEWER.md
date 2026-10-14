# 交付单：G1.2 第一段 候选参考 smoke 与 W02 测量

> 本交付单在切换到新流程时，根据执行 agent 已有的交付整理而成，内容全部指向已提交的文件。

- 对应基准 commit：abcfded
- 本次交付 commit：948cfda

## 做了什么
- 接收 4 个候选冻结参考（CIFAR-10 / CIFAR-100，各取第 40、80 轮快照），核对身份和状态不变。
- 在 3 个客户端（0 / 9 / 19）上计算逐类完整分类头梯度，并与独立的 float64 解析式、CPU/CUDA 结果比较。
- 实测 W02（类梯度测量的样本量、耗时、载荷），给出梯度对象的数值容差候选值。
- 中途触到 64 MiB 证据额度上限，经作者授权提高额度后续跑，补算了 CIFAR-100 第 80 轮的缺失诊断。

## 产出文件
- `docs/DIRECTION_A_G1_2_SMOKE_MEASUREMENT_v1.md`：完整交付说明
- `docs/DIRECTION_A_G1_2_SMOKE_RUN_RECORD_v1.md`、`docs/DIRECTION_A_G1_2_SMOKE_RESUME_RUN_RECORD_v1.md`：运行与续跑记录
- `artifacts/direction_a/phaseG1_2_smoke_v1/decision.json`：执行侧的状态结论
- `artifacts/direction_a/phaseG1_2_smoke_v1/epsilon_candidate.json`：ε_num 候选
- `artifacts/direction_a/phaseG1_2_smoke_v1/W02_measurement.json`：W02 实测
- `direction_a/class_gradient_smoke.py`、`tests/test_direction_a_class_gradient_smoke.py`：实现与测试

## 判据自评（对照 `docs/DIRECTION_A_CHECKPOINTS_v1.md` §G1.2 第 4 项的梯度 smoke 部分）
| 判据 | 结果 | 证据位置 / 关键数字 |
|---|---|---|
| 含/不含偏置按声明实现，包含完整输出维度 | PASS | 测量说明 §3；C×128 + C 维 bias |
| 单端类均值与逐样本平均在容差内一致 | PASS | 与独立参照共 504 条比较，最大归一化 L∞ = 2.68e-7 |
| `G_c` 与按 `a_ic` 汇总一致 | PASS（仅选定来源） | 测量说明 §3；其余 17 端未测 |
| 重复读取参考后参数与缓冲哈希不变 | PASS | 测量说明 §3 "状态不变" |
| 缺类不产生伪梯度 | PASS | 测量说明 §3 "缺类" |
| 完整数据梯度与小批量噪声口径有明确选择 | PASS | 主梯度用完整类样本，端内无抽样噪声 |
| 正式参考资格、全 20 端正式测量 | 未做 | 属于第二段 |

## 实际资源消耗
- 程序累计时间约 11 秒；GPU 分配峰值约 136 MB；证据记账约 79 MB（额度已由 64 MiB 提到 256 MiB）。

## 阻塞
- 无

## 异议
- 无

## 需要审查者裁决的问题
1. 是否采纳梯度对象的数值容差 ε_num = 2e-6（依据：`epsilon_candidate.json`），并冻结 W02 测量协议？
2. 是否授权 G1.2 第二段（全部 20 个客户端的正式测量与全端目标诊断）？如授权，请给出资源上限。
3. 4 个参考的尾类 recall 全为 0：是否影响 G1.2 正式测量的意义？是否应先做或并行做 P 探针，还是重新准备参考？（作者提出）
