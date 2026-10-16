param([ValidateSet('inspect','validate')][string]$Mode='validate')
$ErrorActionPreference='Stop'
$g13Clock=[Diagnostics.Stopwatch]::StartNew()
$g13Out=Join-Path $PSScriptRoot '../artifacts/direction_a/phaseG1_3_A_v1'
[IO.Directory]::CreateDirectory($g13Out) | Out-Null
$g13State=Join-Path $g13Out 'outer_receipt.json'
$g13Previous=0.0
if(Test-Path -LiteralPath $g13State){$g13Previous=(Get-Content -Raw -LiteralPath $g13State | ConvertFrom-Json).cumulative_seconds}
# 50s first round +40s repair +30s sealing. No per-restart renewal.
$g13Timeout=if($Mode -eq 'inspect'){20.0}else{50.0-$g13Previous}
if($g13Timeout -le 0 -or $g13Previous -ge 90){throw 'Cumulative active time unavailable'}
$g13Info=[Diagnostics.ProcessStartInfo]::new()
$g13Info.FileName='E:\anaconda3\python.exe'
$g13Info.WorkingDirectory=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$g13Info.ArgumentList.Add('-B')
$g13Info.ArgumentList.Add((Join-Path $PSScriptRoot 'prepare_direction_a_g1_3.py'))
if($Mode -eq 'inspect'){$g13Info.ArgumentList.Add('--inspect')}
$g13Info.UseShellExecute=$false
$g13Info.CreateNoWindow=$true
$g13Info.RedirectStandardOutput=$true
$g13Info.RedirectStandardError=$true
$g13Info.Environment['G13_OUTER_ACTIVE']='1'
$g13Info.Environment['G13_DEADLINE_UTC']=[DateTime]::UtcNow.AddSeconds($g13Timeout).ToString('o')
$g13Proc=[Diagnostics.Process]::new()
$g13Proc.StartInfo=$g13Info
$g13Proc.Start() | Out-Null
$g13Stdout=$g13Proc.StandardOutput.ReadToEndAsync()
$g13Stderr=$g13Proc.StandardError.ReadToEndAsync()
$g13Killed=$false
$g13Peak=0L
while(-not $g13Proc.HasExited){
    $g13Proc.Refresh()
    $g13Peak=[Math]::Max($g13Peak,$g13Proc.PeakWorkingSet64)
    if($g13Clock.Elapsed.TotalSeconds -gt $g13Timeout -or $g13Peak -gt 2147483648){
        $g13Proc.Kill($true);$g13Killed=$true;break
    }
    Start-Sleep -Milliseconds 20
}
$g13Proc.WaitForExit()
$g13Receipt=@{cumulative_seconds=$g13Previous+$g13Clock.Elapsed.TotalSeconds;invocation_seconds=$g13Clock.Elapsed.TotalSeconds;
    timeout_seconds=$g13Timeout;peak_working_set_bytes=$g13Peak;killed=$g13Killed;exit_code=$g13Proc.ExitCode;
    reserved_tail_seconds=30;outer_io_reserve_bytes=65536;outer_io_actual_bytes=$null;implicit_io_bytes=$null}
[IO.File]::WriteAllText($g13State,($g13Receipt | ConvertTo-Json),[Text.UTF8Encoding]::new($false))
Write-Output $g13Stdout.Result
Write-Output $g13Stderr.Result
if($g13Killed -or $g13Proc.ExitCode -ne 0){exit 1}
