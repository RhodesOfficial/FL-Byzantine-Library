# E02 同篇 FedStale 定向事实与缺项

日期：2026-10-20；只读查阅，不改变科学协议或创新判断。未扫描文献目录、旧提交／裁决或硕士论文目录，未读取第三篇论文。

- [出版页](https://ebooks.iospress.nl/doi/10.3233/FAIA240849)：Angelo Rodio、Giovanni Neglia，ECAI2024，3071–3078。摘要第5–6句说明每轮将参与端 fresh 与未参与端 stale 更新作凸组合，权重在 FedAvg（只 fresh）与 FedVARP（fresh/stale 同等处理）之间插值。摘要第4、7句讨论非均匀参与和最少参与端对收敛误差的作用。
- [arXiv 官方标题查询](https://export.arxiv.org/api/query?search_query=ti%3AFedStale&start=0&max_results=1) 定位同作者、同题预印本 `2405.04171v1`，2024-05-07，33页含补充材料及 [PDF](https://arxiv.org/pdf/2405.04171v1)。
- 使用有限3次定位调用＋2次后续 fetch；一次搜索服务 HTTP401，[HTML](https://arxiv.org/html/2405.04171v1) HTTP404，PDF fetch 不支持 `application/pdf`。**本周期未取得可读全文**，没有绕限制或因查新缺项阻塞已授权资格包。

因此具体聚合式、式号、缓存读取／刷新顺序、参与概率是已知还是估计、独立性／正下界等理论假设仍未核实。摘要的“凸组合”不足以认证与 A′ 完整公式等价或不同，不能据此宣告未知概率设定已查新或其创新已被否定。

A′ 本身的条件关系仍为 `E[Ghat|history]=Σ_i[M_i+(p_i/ptilde_i)(h_i−M_i)]`。`ptilde_i=max(.4*(1+past_R_i)/(2+past_A_i),.05)` 是只用历史的估计，不是已知真实 p。类均衡固定权重可写一般有限和，这只是协议对象的重写，不是 FedStale 全文事实。先校正后刷新是 A′ 定义；FedStale 是否相同仍缺测。

Reviewer 如仍考虑后续投入，可只补该同篇 PDF 的算法与概率前提，不需要全目录扫描。本文不作贡献成立或硕士资格裁决。
