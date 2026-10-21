param(
  [Parameter(Mandatory=$true)][string]$Python,
  [Parameter(Mandatory=$true)][string]$Mode,
  [Parameter(Mandatory=$true)][string]$RunId,
  [Parameter(Mandatory=$true)][double]$MaxSeconds
)
$ErrorActionPreference='Stop'
$root = (Get-Location).Path
$outDir = Join-Path $root 'artifacts/b/e01/processes'
New-Item -ItemType Directory -Force $outDir | Out-Null
$receipt = Join-Path $outDir ($RunId + '.json')
if (Test-Path -LiteralPath $receipt) { throw "Run identity exists: $RunId" }
$env:OMP_NUM_THREADS='4'; $env:MKL_NUM_THREADS='4'; $env:OPENBLAS_NUM_THREADS='1'
$env:NUMEXPR_NUM_THREADS='1'; $env:PYTHONHASHSEED='0'; $env:PYTHONPATH=$root
$stdout = Join-Path $outDir ($RunId + '.stdout.txt')
$stderr = Join-Path $outDir ($RunId + '.stderr.txt')
$codeCommit = (git rev-parse HEAD).Trim()
$clock = [Diagnostics.Stopwatch]::StartNew()
$p = Start-Process -FilePath $Python -ArgumentList @('-u','-m','direction_b.e01',$Mode) -WorkingDirectory $root -NoNewWindow -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
$processHandle = $p.Handle # retain native handle so Windows exit code survives process exit
$peak=0L; $samples=0; $stopped=$false; $reason=$null
while (-not $p.HasExited) {
  $p.Refresh()
  if (-not $p.HasExited) {
    $peak=[Math]::Max($peak,$p.WorkingSet64); $samples++
    if ($clock.Elapsed.TotalSeconds -ge $MaxSeconds -or $p.WorkingSet64 -gt 8589934592L) {
      $reason=if ($clock.Elapsed.TotalSeconds -ge $MaxSeconds) {'external_wall_cap'} else {'sampled_working_set_cap'}
      $p.Kill($true); $stopped=$true
    }
  }
  if (-not $p.HasExited) { Start-Sleep -Milliseconds 100 }
}
$p.WaitForExit(); $clock.Stop(); $p.Refresh()
$r=[ordered]@{run_id=$RunId;mode=$Mode;python=$Python;implementation_commit=$codeCommit;start_time_utc=(Get-Date).ToUniversalTime().AddSeconds(-$clock.Elapsed.TotalSeconds).ToString('o');external_wall_seconds=$clock.Elapsed.TotalSeconds;exit_code=$p.ExitCode;sampled_peak_os_process_working_set_bytes=$peak;sample_count=$samples;sample_period_ms=100;full_peak_coverage='unknown_startup_between_samples_and_tail';stopped=$stopped;stop_reason=$reason;stdout=$stdout;stderr=$stderr}
$r | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receipt -Encoding utf8
$r | ConvertTo-Json -Depth 8
if ($null -eq $p.ExitCode) { throw 'Exit code was not observed; inspect preserved process output and do not assume zero.' }
if ($p.ExitCode -ne 0) { exit $p.ExitCode }
if ($stopped) { exit 1 }
