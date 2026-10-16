$ErrorActionPreference = 'Stop'
$taskWatch = [Diagnostics.Stopwatch]::StartNew()
$taskInfo = New-Object Diagnostics.ProcessStartInfo
$taskInfo.FileName = 'E:\anaconda3\python.exe'
$taskInfo.Arguments = '-B "' + (Join-Path $PSScriptRoot 'regress.py') + '"'
$taskInfo.WorkingDirectory = $PSScriptRoot
$taskInfo.UseShellExecute = $false
$taskInfo.CreateNoWindow = $true
$taskInfo.RedirectStandardOutput = $true
$taskInfo.RedirectStandardError = $true
$taskProcess = New-Object Diagnostics.Process
$taskProcess.StartInfo = $taskInfo
$taskStarted = $taskProcess.Start()
$taskEnded = $taskProcess.WaitForExit(14000)
if (-not $taskEnded) { & taskkill.exe /PID $taskProcess.Id /T /F | Out-Null }
$taskWatch.Stop()
$taskStdout = $taskProcess.StandardOutput.ReadToEnd()
$taskStderr = $taskProcess.StandardError.ReadToEnd()
if ($taskStdout.Length -gt 4096 -or $taskStderr.Length -gt 4096) { throw 'OuterCaptureCap' }
$taskPeak = $null
try { $taskPeak = $taskProcess.PeakWorkingSet64 } catch { }
$taskReceipt = [ordered]@{started=$taskStarted; timeout=(-not $taskEnded); seconds=$taskWatch.Elapsed.TotalSeconds; exit_code=$(if ($taskEnded) {$taskProcess.ExitCode} else {$null}); windows_peak_bytes=$taskPeak; cpu_proxy_bytes=$null; implicit_OS_IO=$null; receipt_in_shared_workflow_margin=$true; stdout=$taskStdout; stderr=$taskStderr}
$taskText = $taskReceipt | ConvertTo-Json -Depth 4
if ([Text.Encoding]::UTF8.GetByteCount($taskText) -gt 4096) { throw 'OuterReceiptCap' }
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'outer_receipt.json'), $taskText, [Text.UTF8Encoding]::new($false))
$taskText
if (-not $taskEnded -or $taskProcess.ExitCode -ne 0) { exit 1 }
