$ErrorActionPreference = 'Stop'
$taskWatch = [Diagnostics.Stopwatch]::StartNew()
$taskRoot = $PSScriptRoot
$taskRepo = (Resolve-Path (Join-Path $taskRoot '../../..')).Path
$taskOld = Join-Path $taskRepo 'artifacts/direction_a/phaseG1_1_protection_validation_resume_v1'
$taskBase = '5174b06bb1a6d90e58ed6e07b5ab6e88e283f269'
function Save-TaskJson($name, $value) {
    $taskBytes = [Text.Encoding]::UTF8.GetBytes(($value | ConvertTo-Json -Depth 20) + "`n")
    if ($taskBytes.Length -gt 32768) { throw 'PreparationWriteCap' }
    [IO.File]::WriteAllBytes((Join-Path $taskRoot $name), $taskBytes)
}
& git -C $taskRepo merge-base --is-ancestor $taskBase HEAD
if ($LASTEXITCODE -ne 0) { throw 'BaseNotAncestor' }
$taskPaths = @('artifacts/direction_a/phaseG1_1_protection_validation_resume_v1',
 'artifacts/direction_a/phaseG1_1_formal_F_v1', 'artifacts/direction_a/phaseG1_1_formal_F_resume_v1',
 'artifacts/direction_a/phaseG1_1_resource_closure_v1', 'artifacts/direction_a/phaseG1_1_resource_closure_resume_v1',
 'docs/DIRECTION_A_G1_1_QUALIFICATION_v2.md', 'direction_a/formal_f.py', 'direction_a/formal_f_policy.py',
 'direction_a/cost_m.py', 'scripts/run_direction_a_formal_f.py', 'tests/test_direction_a_formal_f.py')
$taskIdentities = foreach ($taskPath in $taskPaths) {
    $taskBefore = (& git -C $taskRepo rev-parse ($taskBase + ':' + $taskPath)).Trim()
    $taskNow = (& git -C $taskRepo rev-parse ('HEAD:' + $taskPath)).Trim()
    if ($taskBefore -ne $taskNow) { throw ('IdentityMismatch:' + $taskPath) }
    [ordered]@{path=$taskPath; baseline=$taskBefore; head=$taskNow; equal=$true}
}
& git -C $taskRepo diff --quiet -- @taskPaths
if ($LASTEXITCODE -ne 0) { throw 'OldWorkingTreeModified' }
$taskOldSource = [IO.File]::ReadAllText((Join-Path $taskOld 'validate.py')).Replace("`r`n", "`n").Replace("`r", "`n")
$taskNeedle = @'
def synthetic():
    results = []
    def check(name, observed, expected=True):
        results.append(dict(name=name, observed=observed, expected=expected,
                            result='PASS' if observed == expected else 'FAIL'))
'@
$taskReplacement = @'
def snapshot_check(results, name, observed, expected=True):
    from copy import deepcopy
    observed, expected = deepcopy(observed), deepcopy(expected)
    results.append(dict(name=name, observed=observed, expected=expected,
                        result='PASS' if observed == expected else 'FAIL'))


def synthetic():
    results = []
    def check(name, observed, expected=True):
        snapshot_check(results, name, observed, expected)
'@
if (($taskOldSource.Split(@($taskNeedle), [StringSplitOptions]::None)).Length -ne 2) { throw 'PatchAnchorMismatch' }
$taskNewSource = $taskOldSource.Replace($taskNeedle, $taskReplacement)
$taskSourceBytes = [Text.Encoding]::UTF8.GetBytes($taskNewSource)
if ($taskSourceBytes.Length -gt 32768) { throw 'HelperWriteCap' }
[IO.File]::WriteAllBytes((Join-Path $taskRoot 'validate_snapshot.py'), $taskSourceBytes)
Save-TaskJson 'source_patch.json' ([ordered]@{old_git_blob='1dc6a1020504ed73e17e0a5b6470c6d92d8e1787'; normalization='CRLF/CR/LF only'; old=$taskNeedle; replacement=$taskReplacement; replacements=1; other_semantic_changes=0; invocation='regress.py executes snapshot_check, the same recorder called by synthetic.check; synthetic full suite never called'})
$taskExisting = @('docs/workflow/ROLE_EXECUTOR.md','docs/workflow/TO_EXECUTOR.md','docs/workflow/STATE.md',
 'docs/DIRECTION_A_G1_1_ADJUDICATION_v8.md','docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md',
 'artifacts/direction_a/phaseG1_1_protection_validation_resume_v1/validate.py',
 'artifacts/direction_a/phaseG1_1_protection_validation_resume_v1/launch.ps1',
 'artifacts/direction_a/phaseG1_1_protection_validation_resume_v1/plan.json',
 'artifacts/direction_a/phaseG1_1_protection_validation_resume_v1/bootstrap.json',
 'artifacts/direction_a/phaseG1_1_protection_validation_resume_v1/workflow_audit.json',
 'artifacts/direction_a/phaseG1_1_protection_validation_resume_v1/results.json')
$taskSizes = foreach ($taskPath in $taskExisting) { [ordered]@{path=$taskPath; bytes=(Get-Item -LiteralPath (Join-Path $taskRepo $taskPath)).Length} }
Save-TaskJson 'identity.json' ([ordered]@{task_base=$taskBase; checkout_head=(& git -C $taskRepo rev-parse HEAD).Trim(); base_is_ancestor=$true; identity_verified=$true; identities=$taskIdentities; working_tree_diff_exit=0; no_778_scan=$true; retained_counts=@(778,0,0); old_results_blob='5f3044d25a456b739e711919524535aad9c3e7d4'; old_pass_citations=@(1,2,4,6); preparation=[ordered]@{external_read_calls_before_prepare=7; command_seconds_before_prepare=@(0.6180108,0.5526559,0.7715005,0.4430088,0.6518369,0.8037355,0.7352176); existing_files=$taskSizes; source_read_bytes=([IO.FileInfo](Join-Path $taskOld 'validate.py')).Length; physical_IO=$null; Git_internal_IO=$null; workflow_peak=$null; reasoning_wall=$null; issue=[ordered]@{type='FiniteBootstrapAccountingGap'; occurrences=1; disposition='finite preparation only; not a restricted guard failure'}; auxiliary_issue=[ordered]@{type='PowerShellWildcardPath'; location='preparation call4 rg'; science_results=0; disposition='resolved by explicit protocol path'} }; prepare_seconds_prefix=$taskWatch.Elapsed.TotalSeconds})
$taskWatch.Stop()
Write-Output ('Prepared minimal snapshot copy; seconds=' + $taskWatch.Elapsed.TotalSeconds)
