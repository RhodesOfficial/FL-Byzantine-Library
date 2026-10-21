# 来源及运行格式

## 单篇 evidence 元素

~~~json
{
  "id": "P0001:E01",
  "source_kind": "paper",
  "source_url": "实际读取的官方 URL",
  "locator": "PDF 文件页 4，§3.1，式(2)；或仓库 commit/路径/函数",
  "claim": "一条可核对的原文事实，不混入自己的改法",
  "accessed_at": "实际带时区时间",
  "read_status": "DIRECT"
}
~~~

这是空格式说明，不是真实证据。source_kind 为 paper/code/venue/review/recognition；read_status 为 DIRECT/METADATA/UNAVAILABLE。只有 DIRECT 可支撑事实 PASS。原文数字、公式、局限用来源；迁移、资源缩放和新组合假说标 INFERENCE，并给其依赖的证据 ID。PDF 页码与正文页码不混用。

正式单篇卡中的六条件证据须来自本卡；配对卡可引用两张单篇卡及本卡新增 evidence（Q0001:E01）。来源 URL 必须实际访问；版本差异不能拼成一个算法。

## staging/run.json

至少含 run_id、status、pressure、started_at、runtime、capabilities、usage、completion、unknown_costs。usage 含 search_queries、fetch_calls、deep_read_papers、active_children_peak，均为非负实际值；未测不能写零。最终状态 COMPLETE / COMPLETE_NO_PAIR / PARTIAL / CAPABILITY_BLOCKED。

requests.jsonl 每行保存 request_id、task_id、kind（search/fetch）、queries 或 url、实际结果/错误、访问时间和回执。子任务失败及零结果也保存，总控合并时不重复计同一 request_id。

## 输出与读法

- 单篇状态 ACCEPTED/HOLD/REJECTED；DISCOVERED 等只表明处理进度。未深读候选留 staging，而非强行填空卡。
- 六项条件用 PASS/HOLD/FAIL；真实发生的事实与读者推断分开。UNKNOWN 不伪装为 PASS。
- Pair 的 PAPER_COMPATIBLE 是纸面可继续推理，前四项 SUPPORTED、后四项 PLAN_READY；UNKNOWN → HOLD，确证 CONFLICT → REJECTED。不等同于“最小资格通过”。
- 真实 runtime ID/回执与换一个角色名称不同。结构程序不能验证远端 agent 身份或来源事实，Auditor 仍须实际核对。
- pool.py check 成功只表示这些结构和引用检查通过，不能证明搜索充分、论文正确、代码可运行或方法新颖。

exports/cards 与 exports/pairs 是生成目录，不手写个人笔记；每次 publish 根据当前 records/pairs 更新这些视图。修改准入状态后重新发布，旧 ACCEPTED 视图应消失；原始记录/来源不删除。
