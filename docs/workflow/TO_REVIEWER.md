# 交付单：P 正式第2轮恢复自检失败

- 对应任务单的基准 commit：ea6a10001998a6062b6365f5e5f3f0df862bca7e
- 本次交付 commit：见本提交

## 做了什么（≤5 条）
- 新建v6恢复入口、精确240头队列及预登记，v5拟合/统计算术复用原源码。
- 唯一语法检查PASS；唯一CPU套件22项中21 PASS、1 FAIL，保留原失败记录。
- 自检失败即停；真实输入/正式续跑/新拟合/编码均0；旧包未改写。

## 产出文件
- scripts/resume_direction_a_probe_formal.py、tests/test_direction_a_probe_formal_resume.py：恢复入口与合成套件。
- artifacts/direction_a/phaseP_formal_resume_v1/：preregistration、syntax_check、selfchecks、check_cost、run_record、artifact_hashes。
- 同目录resume_manifest、input_checks、results、uncertainty：明确标记未运行/未校验的部分交付，未生成新头或联合400头索引。

## 判据自评
|判据编号|结果 PASS/FAIL|证据位置 / 关键数字|
|---|---|---|
|1|FAIL|syntax_check PASS；selfchecks 21 PASS/1 FAIL，归档大小断言失败|
|2|FAIL|input_checks：真实输入资格未运行，新encoder/验证编码0|
|3|FAIL|resume_manifest仅预定队列；旧160头未读回，新完整头0/240|
|4|FAIL|results：未产生四点全指标/训练置乱对照|
|5|FAIL|uncertainty：验证置乱0/39996|
|6|FAIL|uncertainty：bootstrap 0/8000；未新增目标诊断|
|7|FAIL|run_record：failed_before_real_input；联合索引/工程资格未完成|
|8|FAIL|四点科学推断未完成，不构成表征无信息结论|

|参考|本轮尾R/改善|可分性|校准空间|
|---|---|---|---|
|C10 r40|未推断|FAIL|FAIL|
|C10 r80|未推断|FAIL|FAIL|
|C100 r40|未运行|FAIL|FAIL|
|C100 r80|未运行|FAIL|FAIL|

## 实际资源消耗
- 本次CPU程序保守20.562秒；实现/相关程序180秒、终末20秒预留已计入；恢复保守220.562000秒。
- 旧正式562.063秒/8259455 B/166480扫描按v6继承；新写入1537791 B/扫描1407；旧未知及旧判据6 FAIL保留。
- 正式总账782.625000/4380秒、9797246/134217728 B；余量3597.375000秒/124420482 B。
- 准备74.9171745秒/11988355 B只继承一次；P累计857.542175秒/21785601 B。
- 本轮CUDA峰0；Windows自检峰见check_cost，历史最大峰6447243264 B继承；CPU代理峰1430056 B。
- 旧有效160000更新与失败461次保守收费保留；新更新0、重复验证编码0；历史计数本轮未重新核验。
- 自评FAIL 8条；未因自检断言失败否定科学假设。

## 阻塞（没有写“无”）
- 唯一CPU套件21 PASS、1 FAIL；合成归档130526 B未大于断言131072 B（test_large_emergency_archive_and_cross_process_peaks），按任务单立即停止，未读取真实输入、未启动CUDA或真实续跑。

## 异议（没有写“无”）
无

## 需要审查者裁决的问题（≤3 条，没有写“无”）
- 是否授权修正归档大小测试断言并追加一次自检；本次恢复修订/语法/CPU套件各1次已耗尽，未擅自重试。
