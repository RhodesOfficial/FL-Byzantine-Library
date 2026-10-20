param(
    [Parameter(Mandatory=$true)][ValidateSet('test','representative','full','verify')][string]$Mode,
    [Parameter(Mandatory=$true)][double]$Seconds,
    [string]$Python = (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python310\python.exe')
)
$ErrorActionPreference = 'Stop'
if ([double]::IsNaN($Seconds) -or [double]::IsInfinity($Seconds) -or $Seconds -le 0) { throw 'Seconds must be finite and positive' }
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root 'artifacts/a_prime/e01'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$receiptPath = Join-Path $out ($Mode + '_outer_receipt.json')
$attempt = 1
while (Test-Path -LiteralPath $receiptPath) {
    $old = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
    if ($old.exit_code -eq 0 -and -not $old.timed_out) { throw 'Completed stage: do not repeat it' }
    $attempt += 1
    if ($attempt -gt 3) { throw 'At most two repair validations within the same total budget' }
    $receiptPath = Join-Path $out ($Mode + '_outer_receipt_' + $attempt + '.json')
}
$previous = @(Get-ChildItem -LiteralPath $out -Filter '*_outer_receipt*.json' | ForEach-Object {
    (Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json).program_wall_seconds
})
# Measured metadata extraction plus a separately stated 60s allowance for unmetered dependency/Git setup.
$prior = 0.8177578 + (($previous | Measure-Object -Sum).Sum)
if ($prior + 60 + $Seconds -gt 1200) { throw 'Remaining complete-cycle budget not covered' }
if ($Mode -eq 'representative' -and $Seconds -gt 120) { throw 'Representative cycle must be at most two minutes' }
if ($Mode -eq 'full' -and $prior + 60 + $Seconds + 360 -gt 1200) { throw 'Full run must preserve six minutes for save/recovery/repair' }
$timer = [Diagnostics.Stopwatch]::StartNew()
$proc = Start-Process -FilePath $Python -ArgumentList @('scripts/check_a_prime_e01.py', $Mode, '--stage-seconds', $Seconds) -WorkingDirectory $root -NoNewWindow -PassThru
$handle = $proc.Handle
$finished = $proc.WaitForExit([int]($Seconds*1000))
if (-not $finished) { $proc.Kill(); $proc.WaitForExit() }
$proc.Refresh()
$record = [ordered]@{
    stage = $Mode
    exit_code = $proc.ExitCode
    timed_out = (-not $finished)
    program_wall_seconds = $timer.Elapsed.TotalSeconds
    clock_scope = 'PowerShell Stopwatch enclosing interpreter startup, computation, save/readback and inner receipt; final outer receipt serialization excluded'
    cumulative_metered_seconds_before_stage = $prior
    unmetered_setup_planning_allowance_seconds = 60
    outer_receipt_write_readback_seconds = $null
}
function Save-Receipt($value, $path) {
    $absolute = [IO.Path]::GetFullPath($path)
    $expected = [IO.Path]::GetFullPath($out)
    if ([IO.Path]::GetDirectoryName($absolute) -ne $expected) { throw 'Unexpected receipt move target' }
    $temp = $absolute + '.tmp'
    [IO.File]::WriteAllText($temp, ($value | ConvertTo-Json) + "`n", (New-Object Text.UTF8Encoding($false)))
    $check = Get-Content -LiteralPath $temp -Raw | ConvertFrom-Json
    if ($check.stage -ne $Mode -or [Math]::Abs($check.program_wall_seconds - $value.program_wall_seconds) -gt 1e-9) { throw 'Temporary receipt readback failed' }
    if ([IO.File]::Exists($absolute)) { [IO.File]::Replace($temp, $absolute, $null) }
    else { [IO.File]::Move($temp, $absolute) }
    $check = Get-Content -LiteralPath $absolute -Raw | ConvertFrom-Json
    if ($check.stage -ne $Mode -or [Math]::Abs($check.program_wall_seconds - $value.program_wall_seconds) -gt 1e-9) { throw 'Final receipt readback failed' }
}
$saveTimer = [Diagnostics.Stopwatch]::StartNew()
Save-Receipt $record $receiptPath
$readback = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
if ($readback.stage -ne $Mode) { throw 'Outer receipt readback failed' }
$saveTimer.Stop()
$record.outer_receipt_write_readback_seconds = $saveTimer.Elapsed.TotalSeconds
$record.program_wall_seconds = $timer.Elapsed.TotalSeconds
$record.clock_scope = 'PowerShell Stopwatch enclosing interpreter startup, computation, save/readback, inner receipt and first outer receipt write/readback; final meter update excluded'
Save-Receipt $record $receiptPath
$record | ConvertTo-Json
if (-not $finished) { exit 124 }
exit $proc.ExitCode
