param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("representative", "resume", "formal")]
    [string]$Phase
)
$ErrorActionPreference = "Stop"
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskOut = Join-Path $taskRoot "artifacts\direction_b\r01_v1"
$taskPython = "C:\Users\冰美式\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
New-Item -ItemType Directory -Force -Path $taskOut | Out-Null
$priorSeconds = 0.0
Get-ChildItem -LiteralPath $taskOut -Filter "invocation_*.json" | ForEach-Object {
    $priorSeconds += (Get-Content -Raw -LiteralPath $_.FullName | ConvertFrom-Json).external_seconds
}
$remainingMs = [int][Math]::Floor((120.0 - $priorSeconds) * 1000)
if ($remainingMs -le 0) { throw "Cumulative Python wall time cap reached." }
$invocationPath = Join-Path $taskOut "invocation_$Phase.json"
if (Test-Path -LiteralPath $invocationPath) { throw "Invocation already exists; preserve evidence." }
$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $taskPython
$startInfo.Arguments = '"' + (Join-Path $PSScriptRoot "qualify.py") + '" ' + $Phase
$startInfo.WorkingDirectory = $taskRoot
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $true
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError = $true
$process = New-Object System.Diagnostics.Process
$process.StartInfo = $startInfo
$watch = [System.Diagnostics.Stopwatch]::StartNew()
$process.Start() | Out-Null
if (-not $process.WaitForExit($remainingMs)) {
    $process.Kill()
    $process.WaitForExit()
}
$watch.Stop()
$stdout = $process.StandardOutput.ReadToEnd()
$stderr = $process.StandardError.ReadToEnd()
$exitCode = $process.ExitCode
$record = [ordered]@{
    phase = $Phase
    external_seconds = $watch.Elapsed.TotalSeconds
    prior_external_seconds = $priorSeconds
    cumulative_external_seconds = $priorSeconds + $watch.Elapsed.TotalSeconds
    exit_code = $exitCode
    stdout = $stdout
    stderr = $stderr
    scope = "Python launch through process exit; wrapper/document work excluded"
}
$record | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 -LiteralPath $invocationPath
if ($stdout) { Write-Output $stdout.Trim() }
Write-Output ($record | ConvertTo-Json -Compress)
if ($exitCode -ne 0) { throw "B-R01 process failed; preserve outputs and inspect." }
if ($record.cumulative_external_seconds -gt 120) { throw "Cumulative wall time cap exceeded." }
