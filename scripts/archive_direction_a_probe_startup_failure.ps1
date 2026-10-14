# Archive the already-observed startup failure. Never launches the preparation,
# reads feature caches/checkpoints/datasets, or executes tests/optimization.
$ErrorActionPreference = 'Stop'
$archiveTimer = [System.Diagnostics.Stopwatch]::StartNew()
$taskRoot = Split-Path -Parent $PSScriptRoot
$evidenceRoot = Join-Path $taskRoot 'artifacts/direction_a/phaseP_preparation_v1'
if (Test-Path -LiteralPath $evidenceRoot) {
    throw 'Failure archive already exists; refusing to overwrite its consumed ledger.'
}
$null = New-Item -ItemType Directory -Path $evidenceRoot
$utf8 = [System.Text.UTF8Encoding]::new($false)
$reserveBytes = 131072L
$writtenBytes = $reserveBytes
$newSources = @('direction_a/probe_preparation.py', 'scripts/prepare_direction_a_probe.py',
    'tests/test_direction_a_probe_preparation.py', 'scripts/archive_direction_a_probe_startup_failure.ps1')
foreach ($name in $newSources) {
    $writtenBytes += (Get-Item -LiteralPath (Join-Path $taskRoot $name)).Length
}
function Write-EvidenceText([string] $path, [string] $value) {
    $data = $utf8.GetBytes($value)
    if ($script:writtenBytes + $data.Length -ge 134217728L) { throw 'Failure archive write cap reached.' }
    [System.IO.File]::WriteAllBytes($path, $data)
    $script:writtenBytes += $data.Length
}
function Json-Raw($value) { return ($value | ConvertTo-Json -Depth 30) + "`n" }
$failureText = @'
Single preparation launch:
E:\anaconda3\python.exe -B scripts/prepare_direction_a_probe.py
Returned exit_code=1, command wall_time_seconds=0.4250004.
  File "E:\Federated Machine Learning\FL-Byzantine-Library-astra\scripts\prepare_direction_a_probe.py", line 527
    **{h["name"]:h["metrics"] for h in result["heads"] if h["label_kind"]=="permuted"})
                                                                                      ^
SyntaxError: closing parenthesis ')' does not match opening parenthesis '{' on line 526
No Python module statements, preregistration, selfchecks or fits executed.
No retry, experimental repair, feature/cache/checkpoint or dataset read follows this launch.
'@
Write-EvidenceText (Join-Path $evidenceRoot 'startup_failure.txt') ($failureText + "`n")
$criteria = [ordered]@{}
1..7 | ForEach-Object { $criteria[[string]$_] = 'FAIL' }
$result = [ordered]@{
    run_id = 'FedPCC-P-preparation-v1'
    status = 'blocked_startup_syntax_error'
    baseline_commit = '298a3e8b22986691acf2ede893c0dee04b610881'
    input_commit = '86c0d6458b8f4698dd5ba7980a4b4007204adad8'
    accepted_evidence_commit = 'd3a3bd712d6bb28283b59faff16e17e099debcb4'
    baseline_ancestor_check = $true
    criteria = $criteria
    fail_count = 7
    blocked = $true
    blocker = 'Startup SyntaxError at prepare_direction_a_probe.py:527; retry forbidden and two implementation revisions consumed. Correction and a new execution require reviewer authorization.'
    heads = @()
    completed_heads = 0
    formal_P_executed = $false
    preregistration_written_before_execution = $false
    split_generated = $false
    threshold_basis_generated = $false
    formal_plan_generated = $false
    no_scientific_conclusion = $true
    feature_checkpoint_or_raw_dataset_reads = 0
    validation_or_test_accesses = 0
    reused_G1_2_costs = [ordered]@{
        this_run_reused_feature_samples = 0
        historical_ledger_path = 'artifacts/direction_a/phaseG1_2_full_v1/run_record.json'
        historical_program_seconds = 30.49900000001071
        historical_encoded_samples = 41838
        historical_cost_not_charged_as_new = $true
        original_head_and_backbone_modified = $false
    }
}
Write-EvidenceText (Join-Path $evidenceRoot 'results.json') (Json-Raw $result)
$checks = [ordered]@{
    run_id = 'FedPCC-P-preparation-v1'
    status = 'NOT_RUN'
    reason = 'Python parsing failed before imports and run_checks; no tests claimed to have passed.'
    test_source = 'tests/test_direction_a_probe_preparation.py'
    planned_checks = @('independent unequal-frequency class-balanced CE constants',
        '100-class zero-logit objective', 'nonfinite rejection', 'macro recall denominators and zeros',
        'analytic chance and percentage-point differences', 'PCG64 split and disjoint cover',
        'insufficient class support/duplicate rejection', 'global permutation and frequency preservation')
    optimizer_steps = 0
    backwards = 0
}
Write-EvidenceText (Join-Path $evidenceRoot 'selfchecks.json') (Json-Raw $checks)
$reviewText = @'
# 交付单：P 可分性探针有界准备（启动失败）

- 对应任务单的基准 commit：298a3e8b22986691acf2ede893c0dee04b610881
- 本次交付 commit：见本提交

## 做了什么（≤5 条）
- 核对基准为当前HEAD祖先，读取STATE、任务单和G1.2裁决。
- 写入训练内部划分、均衡线性头、置乱标签及受限计账的实现和相关自检代码；未经运行验证。
- 一次启动在Python解析阶段失败，未执行模块语句、自检、特征读取或拟合；没有重跑。
- 自动保存启动失败、零拟合结果、自检未执行标记、成本记录和文件哈希。

## 产出文件
- direction_a/probe_preparation.py：训练内部划分、损失、指标与拟合代码，未验证。
- scripts/prepare_direction_a_probe.py：准备入口，527行缺少外层字典闭合，当前不可执行。
- tests/test_direction_a_probe_preparation.py：相关解析/前向自检，未执行。
- scripts/archive_direction_a_probe_startup_failure.ps1：仅归档已发生失败，不运行实验。
- artifacts/direction_a/phaseP_preparation_v1/startup_failure.txt：原启动错误、退出码与命令耗时。
- 同目录results.json、selfchecks.json、run_record.json、artifact_hashes.json：失败状态与机器可读记录。
- preregistration.json、split.json、24个最终头、threshold_basis.md和formal_plan.json未生成。

## 判据自评
| 判据编号 | 结果 PASS/FAIL | 证据位置 / 关键数字 |
|---|---|---|
|1|FAIL|results.json：未完成四参考/逐端train特征核验；没有新编码或正式评价，原状态未操作|
|2|FAIL|results.json：划分代码未运行，split.json未生成|
|3|FAIL|results.json：完成0/24头，没有实际置乱/拟合结果|
|4|FAIL|startup_failure.txt：解析失败；反向/优化器均0，目标记录和最终头缺失|
|5|FAIL|results.json：所有实测CE/recall/差值和分母缺失|
|6|FAIL|run_record.json、artifact_hashes.json：失败账本可定位，但完整头/峰值证据缺失|
|7|FAIL|threshold_basis.md、formal_plan.json缺失；未冻结τ_probe，未判断P可分性|

## 实际资源消耗
- 唯一准备启动命令耗时0.4250004秒（执行工具计时，含进程启动/退出）；归档时间、写入和归档进程峰值见run_record.json。
- 准备运行启动1次，失败重跑0，搜索0，实现修订2次，拟合/反向/优化器/头前向/新编码/通信/类梯度请求均0。
- Python准备进程的峰值显存/Windows working-set/CPU代理未测得，写null，不声称全部资源检查通过。
- 旧G1.2成本在results.json.reused_G1_2_costs单列，本轮未实际读取训练特征。

## 阻塞
- scripts/prepare_direction_a_probe.py:527存在括号闭合语法错误；模块解析失败导致预注册和运行尚未开始。
- 任务单禁止失败重跑，且实现修订2次额度已耗尽；停止修订/执行，不自行扩额。修复和重新执行须由审查者重新授权。

## 异议
无

## 需要审查者裁决的问题（≤3 条，没有写"无"）
- 是否为语法修复及重新启动另行授权实现修订/运行额度；现有失败记录和成本必须保留，不清零。
'@
$reviewPath = Join-Path $taskRoot 'docs/workflow/TO_REVIEWER.md'
Write-EvidenceText $reviewPath ($reviewText + "`n")
$files = [ordered]@{}
$paths = @($newSources) + @('docs/workflow/TO_REVIEWER.md') + @(
    'artifacts/direction_a/phaseP_preparation_v1/startup_failure.txt',
    'artifacts/direction_a/phaseP_preparation_v1/results.json',
    'artifacts/direction_a/phaseP_preparation_v1/selfchecks.json')
foreach ($name in $paths) {
    $path = Join-Path $taskRoot $name
    $files[$name] = [ordered]@{path=$name; bytes=(Get-Item -LiteralPath $path).Length;
        sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$ledgerName = 'artifacts/direction_a/phaseP_preparation_v1/run_record.json'
$files[$ledgerName] = [ordered]@{path=$ledgerName; bytes=0; sha256=('0' * 64)}
$archiveIndex = [ordered]@{
    algorithm='SHA-256 file bytes'; files=$files
    excluded=@('artifacts/direction_a/phaseP_preparation_v1/artifact_hashes.json (self)')
    generating_script='scripts/archive_direction_a_probe_startup_failure.ps1'
    parameters='Single observed launch exit=1/wall=0.4250004 s; startup SyntaxError; no preparation retry.'
    large_new_files=@()
}
$process = [System.Diagnostics.Process]::GetCurrentProcess()
$ledger = [ordered]@{
    run_id='FedPCC-P-preparation-v1'; status='blocked_startup_syntax_error'
    preparation_launches=1; preparation_module_executions=0; failed_retries=0
    implementation_revisions=2; archive_only_invocations=1
    preparation_command_seconds=0.4250004
    preparation_time_measurement='exec_command wall time, includes startup and exit; no in-module timer ran'
    archive_program_seconds=$archiveTimer.Elapsed.TotalSeconds
    elapsed_seconds=(0.4250004+$archiveTimer.Elapsed.TotalSeconds)
    finalization_time_reserved_seconds=0.1
    counts=[ordered]@{fits=0; forwards=0; backwards=0; optimizer_steps=0; searches=0;
        feature_samples=0; encoder_forwards=0; communications=0; class_gradient_requests=0;
        preparation_statistical_scans=0; archive_hash_scans=$paths.Count; evidence_bytes=$writtenBytes}
    resources=[ordered]@{preparation_cuda_allocated_peak_bytes=$null;
        preparation_windows_working_set_peak_bytes=$null; preparation_cpu_tensor_proxy_peak_bytes=$null;
        archive_windows_working_set_peak_bytes=$process.PeakWorkingSet64;
        archive_known_array_proxy_upper_bytes=8388608}
    limits=[ordered]@{wall_seconds=600; cumulative_write_bytes=134217728;
        cuda_allocated_bytes=6442450944; windows_working_set_bytes=6442450944;
        cpu_tensor_proxy_bytes=2147483648; fits=24; head_forwards=6000;
        statistical_scans=10000; backwards=4800; optimizer_steps=4800;
        failed_retries=0; implementation_revisions=2; preparation_runs=1}
    emergency_status_reserved_bytes=$reserveBytes
    source_writes_charged_bytes=($writtenBytes-$reserveBytes-
        (Get-Item -LiteralPath $reviewPath).Length-
        (Get-Item -LiteralPath (Join-Path $evidenceRoot 'startup_failure.txt')).Length-
        (Get-Item -LiteralPath (Join-Path $evidenceRoot 'results.json')).Length-
        (Get-Item -LiteralPath (Join-Path $evidenceRoot 'selfchecks.json')).Length)
    implementation_write_limitation='Final newly written source sizes charged; superseded patch bytes not measured, so no exact cumulative source-write PASS claim.'
    hit=$null; blocked=$result.blocker
}
# Verify archived outputs without another preparation process. Ledger/index are
# closed together with fixed-size hash slots, and include this verification cost.
foreach ($name in $paths) {
    $path = Join-Path $taskRoot $name
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $files[$name].sha256) {
        throw "Archive hash mismatch: $name"
    }
}
$ledger.counts.archive_hash_scans += $paths.Count
$ledger.archive_program_seconds = $archiveTimer.Elapsed.TotalSeconds + 0.1
$ledger.elapsed_seconds = 0.4250004 + $ledger.archive_program_seconds
$ledger.resources.archive_windows_working_set_peak_bytes = [System.Diagnostics.Process]::GetCurrentProcess().PeakWorkingSet64
for ($i=0; $i -lt 12; $i++) {
    $ledgerRaw = Json-Raw $ledger
    $files[$ledgerName].bytes = $utf8.GetByteCount($ledgerRaw)
    $ledger.counts.evidence_bytes = $writtenBytes + $utf8.GetByteCount($ledgerRaw) + $utf8.GetByteCount((Json-Raw $archiveIndex))
}
$ledgerRaw = Json-Raw $ledger
$sha256 = [System.Security.Cryptography.SHA256]::Create()
$files[$ledgerName].sha256 = [Convert]::ToHexString($sha256.ComputeHash($utf8.GetBytes($ledgerRaw))).ToLowerInvariant()
$indexRaw = Json-Raw $archiveIndex
if ($ledger.elapsed_seconds -ge 600 -or $ledger.counts.evidence_bytes -ge 134217728) { throw 'Failure archive budget exceeded.' }
[System.IO.File]::WriteAllText((Join-Path $evidenceRoot 'run_record.json'), $ledgerRaw, $utf8)
[System.IO.File]::WriteAllText((Join-Path $evidenceRoot 'artifact_hashes.json'), $indexRaw, $utf8)
Write-Output (Json-Raw ([ordered]@{status=$ledger.status; fail_count=7; blocked=$true;
    cumulative_seconds=$ledger.elapsed_seconds; evidence_bytes=$ledger.counts.evidence_bytes}))
