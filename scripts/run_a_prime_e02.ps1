param(
    [Parameter(Mandatory=$true)][ValidateSet('representative','full','verify')][string]$Mode,
    [Parameter(Mandatory=$true)][double]$Seconds,
    [string]$Python = (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python310\python.exe')
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root 'artifacts/a_prime/e02'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$receipts = @(Get-ChildItem -LiteralPath $out -Filter '*_outer_receipt*.json' | ForEach-Object {
    Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
})
$prior = [double](($receipts | Measure-Object -Property program_wall_seconds -Sum).Sum)
if ($Seconds -le 0 -or $prior + $Seconds -gt 1800) { throw 'E02 cumulative time not covered' }
if ($Mode -eq 'representative' -and $Seconds -gt 300) { throw 'Representative limit is 300s' }
if ($Mode -eq 'full' -and $Seconds -gt 900) { throw 'First remaining compute/evaluation/save plan is at most 900s' }
if ($Mode -eq 'full' -and $prior + $Seconds + 600 -gt 1800) { throw 'Preserve complete 600s recovery/repair reserve' }
if (@($receipts | Where-Object { $_.exit_code -ne 0 }).Count -ge 3) { throw 'Initial failure plus at most two repair validations for the entire package' }
$failedThisStage = @($receipts | Where-Object { $_.stage -eq $Mode -and $_.exit_code -ne 0 }).Count
$headWorkStarted = @(Get-ChildItem -Path (Join-Path $root 'artifacts_local/a_prime/e02') -Filter '*_call_journal.json' -ErrorAction SilentlyContinue).Count -gt 0
if ($failedThisStage -and (($Mode -eq 'representative' -and $headWorkStarted) -or $Mode -eq 'full')) { throw 'Interrupted scientific stage: preserve partial objects; no implicit repeat. Read-only verification/packaging only, unless identity-valid remaining boundaries are explicitly defined.' }
$attempt = @($receipts | Where-Object stage -eq $Mode).Count + 1
if ($attempt -gt 3) { throw 'At most two repair validations' }
if (@($receipts | Where-Object { $_.stage -eq $Mode -and $_.exit_code -eq 0 }).Count) { throw 'Do not repeat completed stages' }
$timer = [Diagnostics.Stopwatch]::StartNew()
$proc = Start-Process -FilePath $Python -ArgumentList @('scripts/check_a_prime_e02.py', $Mode, '--stage-seconds', $Seconds) -WorkingDirectory $root -NoNewWindow -PassThru
$handle = $proc.Handle
$finished = $proc.WaitForExit([int]($Seconds*1000))
if (-not $finished) { $proc.Kill(); $proc.WaitForExit() }
$proc.Refresh()
$record = [ordered]@{stage=$Mode; attempt=$attempt; exit_code=$proc.ExitCode; timed_out=(-not $finished); program_wall_seconds=$timer.Elapsed.TotalSeconds; cumulative_before_seconds=$prior; clock_scope='Outer Stopwatch includes interpreter startup and child work; final receipt serialization excluded, not added to internal timings'; windows_process_peak_working_set_bytes=$null}
try { $record.windows_process_peak_working_set_bytes = $proc.PeakWorkingSet64 } catch { }
$path = Join-Path $out ($Mode + '_outer_receipt_' + $attempt + '.json')
$record | ConvertTo-Json | Set-Content -LiteralPath $path -Encoding utf8
$readback = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
if ($readback.stage -ne $Mode) { throw 'Receipt readback failed' }
$record | ConvertTo-Json
if (-not $finished) { exit 124 }
exit $proc.ExitCode
