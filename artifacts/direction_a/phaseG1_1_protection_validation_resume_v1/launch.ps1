$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskWatch = [Diagnostics.Stopwatch]::StartNew()
$taskInfo = New-Object Diagnostics.ProcessStartInfo
$taskInfo.FileName = 'E:\anaconda3\python.exe'
$taskInfo.Arguments = '-B "' + (Join-Path $taskRoot 'validate.py') + '"'
$taskInfo.WorkingDirectory = $taskRoot
$taskInfo.UseShellExecute = $false
$taskInfo.CreateNoWindow = $true
$taskProcess = New-Object Diagnostics.Process
$taskProcess.StartInfo = $taskInfo
$taskStarted = $taskProcess.Start()
$taskEnded = $taskProcess.WaitForExit(99000)
if (-not $taskEnded) {
    & taskkill.exe /PID $taskProcess.Id /T /F | Out-Null
}
$taskWatch.Stop()
$taskPeak = $null
try { $taskPeak = $taskProcess.PeakWorkingSet64 } catch { }
$taskReceipt = [ordered]@{
    started = $taskStarted
    timeout = (-not $taskEnded)
    seconds = $taskWatch.Elapsed.TotalSeconds
    exit_code = $(if ($taskEnded) { $taskProcess.ExitCode } else { $null })
    windows_peak_bytes = $taskPeak
    cpu_proxy_bytes = $null
    implicit_OS_interpreter_IO = $null
    explicit_application_input_bytes = 0
    receipt_write_cap = 4096
    role = 'outer 100s launch-through-exit watchdog; independent post-exit receipt'
}
$taskText = $taskReceipt | ConvertTo-Json -Depth 5
if ([Text.Encoding]::UTF8.GetByteCount($taskText) -gt 4096) { throw 'OuterReceiptCap' }
[IO.File]::WriteAllText((Join-Path $taskRoot 'outer_receipt.json'), $taskText, [Text.UTF8Encoding]::new($false))
$taskText
if (-not $taskEnded -or $taskProcess.ExitCode -ne 0) { exit 1 }
