param([ValidateSet('validate','seal')][string]$Mode='validate')
# One owner keeps the aggregate; children use synchronous reserve-before-access RPC.
$ErrorActionPreference='Stop'
$g13Clock=[Diagnostics.Stopwatch]::StartNew()
$g13Root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$g13Out=Join-Path $g13Root 'artifacts/direction_a/phaseG1_3_A_guard_v1'
$g13Encoding=[Text.UTF8Encoding]::new($false)
$g13Cache=@{}
$g13Phase='round1'
$g13Limits=@{round1=@{read=393216L;write=393216L;scans=24L;seconds=15.0};round2=@{read=393216L;write=393216L;scans=24L;seconds=15.0};seal=@{read=262144L;write=262144L;scans=16L;seconds=10.0}}
$g13State=@{version='G13-guard-v1';used=@{read=0L;write=0L;scans=0L};phases=@{
 round1=@{read=0L;write=0L;scans=0L;seconds=0.0};round2=@{read=0L;write=0L;scans=0L;seconds=0.0};seal=@{read=0L;write=0L;scans=0L;seconds=0.0}};
 operations=[Collections.Generic.List[object]]::new();counters=@{engineering=2;implementation_revisions=1;syntax=0;cpu=0};
 windows_peak_bytes=0L;cpu_known_proxy_upper_bytes=67108864L;failures=@();status='IN_PROGRESS';syntax_status='NOT_RUN';results=$null;probe=$null}
$g13PhaseStart=0.0
$g13PriorSeconds=0.0
$g13TerminalDeadline=$null
$g13Sources=@('direction_a/g1_3_preparation.py','scripts/prepare_direction_a_g1_3.py','tests/test_direction_a_g1_3_preparation.py','scripts/prepare_direction_a_g1_3_outer.ps1','scripts/prepare_direction_a_g1_3_seal.ps1')
$g13StartupKnownRead=9443L+2105L+2421L+2*8961L
foreach($g13StartupPath in @('docs/workflow/ROLE_EXECUTOR.md','docs/workflow/TO_EXECUTOR.md','docs/workflow/STATE.md','docs/workflow/ROLE_REVIEWER.md','docs/DIRECTION_A_G1_3_ADJUDICATION_v2.md','artifacts/direction_a/phaseG1_3_A_v1/failure.json','artifacts/direction_a/phaseG1_3_A_v1/resource_ledger.json','artifacts/direction_a/phaseG1_3_A_v1/outer_receipt.json','artifacts/direction_a/phaseG1_3_A_v1/seal_receipt.json','artifacts/direction_a/phaseG1_3_A_v1/workflow_adjustment.json','artifacts/direction_a/phaseG1_3_A_v1/selfchecks.json')){$g13StartupKnownRead+=(Get-Item -LiteralPath (Join-Path $g13Root $g13StartupPath)).Length}
$g13StartupKnownRead+=3*(Get-Item -LiteralPath (Join-Path $g13Root 'docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md')).Length
$g13Checkpoint=Join-Path $g13Out 'state_checkpoint.json'

function Check-G13 {
 $g13Now=$g13Clock.Elapsed.TotalSeconds
 if($null -ne $g13TerminalDeadline -and $g13Now -gt $g13TerminalDeadline){throw 'terminal two-second reserve'}
 if($g13PriorSeconds+$g13Now -gt 40.0){throw 'new cumulative 40-second limit'}
 if($g13State.phases[$g13Phase].seconds+$g13Now-$g13PhaseStart -gt $g13Limits[$g13Phase].seconds){throw "phase deadline $g13Phase"}
 $g13Owner=[Diagnostics.Process]::GetCurrentProcess()
 $g13Owner.Refresh()
 $g13State.windows_peak_bytes=[Math]::Max($g13State.windows_peak_bytes,$g13Owner.PeakWorkingSet64)
 if($g13State.windows_peak_bytes -gt 2147483648L){throw 'Windows peak limit'}
}
function Reserve-G13([string]$Label,[long]$Read=0,[long]$Write=0,[long]$Scans=0,[long]$Proxy=67108864L) {
 Check-G13
 if($Read -lt 0 -or $Write -lt 0 -or $Scans -lt 0 -or $Proxy -gt 268435456L){throw 'invalid charge or CPU proxy limit'}
 foreach($g13K in @('read','write','scans')){
  $g13Delta=switch($g13K){read {$Read} write {$Write} scans {$Scans}}
  if($g13State.used[$g13K]+$g13Delta -gt (@{read=1048576L;write=1048576L;scans=64L})[$g13K]){throw "new total reserve $g13K"}
  if($g13State.phases[$g13Phase][$g13K]+$g13Delta -gt $g13Limits[$g13Phase][$g13K]){throw "phase reserve $g13K"}
 }
 $g13State.used.read+=$Read;$g13State.used.write+=$Write;$g13State.used.scans+=$Scans
 $g13State.phases[$g13Phase].read+=$Read;$g13State.phases[$g13Phase].write+=$Write;$g13State.phases[$g13Phase].scans+=$Scans
 $g13State.cpu_known_proxy_upper_bytes=[Math]::Max($g13State.cpu_known_proxy_upper_bytes,$Proxy)
 $g13State.operations.Add(@{label=$Label;phase=$g13Phase;read=$Read;write=$Write;scans=$Scans;proxy=$Proxy})
}
function Bytes-G13($Value) {
 # Known graphs <=1024 nodes/64 KiB strings, <=64 ops; graph/string/UTF8/base64/compile buffers coexist <64 MiB.
 Check-G13
 $g13Raw=$g13Encoding.GetBytes((ConvertTo-Json -InputObject $Value -Depth 50 -Compress)+"`n")
 if($g13Raw.Length -gt 65536){throw 'serialization capacity 64 KiB'}
 return ,$g13Raw
}
function Read-G13([string]$Path) {
 $g13Full=Join-Path $g13Root $Path
 $g13Size=(Get-Item -LiteralPath $g13Full).Length
 if($g13Size -gt 65536){throw 'explicit read capacity'}
 Reserve-G13 "read $Path" -Read $g13Size -Scans 1
 $g13Raw=[IO.File]::ReadAllBytes($g13Full)
 if($g13Raw.Length -ne $g13Size){throw 'input length changed'}
 $g13Cache[$Path]=$g13Raw
 return ,$g13Raw
}
function Write-G13([string]$Name,$Value) {
 $g13Raw=Bytes-G13 $Value
 Reserve-G13 "write $Name" -Write $g13Raw.Length
 [IO.File]::WriteAllBytes((Join-Path $g13Out $Name),$g13Raw)
 $g13Cache["artifacts/direction_a/phaseG1_3_A_guard_v1/$Name"]=$g13Raw
}
function Snapshot-G13 {
 return @{used=@{read=$g13State.used.read;write=$g13State.used.write;scans=$g13State.used.scans};phase=$g13Phase;
 remaining=@{read=1048576L-$g13State.used.read;write=1048576L-$g13State.used.write;scans=64L-$g13State.used.scans}}
}
function Invoke-G13Child([string]$Argument) {
 Check-G13
 $g13Info=[Diagnostics.ProcessStartInfo]::new()
 $g13Info.FileName='E:\anaconda3\python.exe';$g13Info.WorkingDirectory=$g13Root
 $g13Info.ArgumentList.Add('-B');$g13Info.ArgumentList.Add((Join-Path $PSScriptRoot 'prepare_direction_a_g1_3.py'));$g13Info.ArgumentList.Add($Argument)
 $g13Info.UseShellExecute=$false;$g13Info.CreateNoWindow=$true
 $g13Info.RedirectStandardInput=$true;$g13Info.RedirectStandardOutput=$true;$g13Info.RedirectStandardError=$true
 $g13Info.Environment['G13_RPC_ACTIVE']='guard-v1'
 $g13Proc=[Diagnostics.Process]::new();$g13Proc.StartInfo=$g13Info
 $g13Proc.Start() | Out-Null
 $g13Err=$g13Proc.StandardError.ReadToEndAsync();$g13Line=$g13Proc.StandardOutput.ReadLineAsync()
 try {
  while(-not $g13Proc.HasExited -or $g13Line.IsCompleted){
   Check-G13
   if(-not $g13Proc.HasExited){$g13Proc.Refresh();$g13State.windows_peak_bytes=[Math]::Max($g13State.windows_peak_bytes,$g13Proc.PeakWorkingSet64)}
   if($g13Line.IsCompleted){
    $g13Text=$g13Line.GetAwaiter().GetResult()
    if($null -eq $g13Text){break}
    if($g13Text.Length -gt 65536){throw 'RPC line capacity'}
    $g13Request=ConvertFrom-Json -InputObject $g13Text -AsHashtable
    $g13Value=$null
    switch($g13Request.action){
     check {Check-G13}
     reserve {Reserve-G13 $g13Request.label -Read $g13Request.read -Write $g13Request.write -Scans $g13Request.scans -Proxy $g13Request.proxy}
     snapshot {$g13Value=Snapshot-G13}
     read {
      $g13Rel=$g13Request.path
      if($g13Rel -notin $g13Sources -and $g13Rel -ne 'artifacts/direction_a/phaseG1_3_A_guard_v1/failure_fixture.json'){throw 'read outside literal regression whitelist'}
      $g13Value=[Convert]::ToBase64String((Read-G13 $g13Rel))
     }
     write {
      if($g13Request.name -ne 'failure_fixture.json'){throw 'child write outside fixture'}
      Write-G13 $g13Request.name $g13Request.value
     }
     syntax_start {if($g13State.counters.syntax -gt 2){throw 'syntax attempts exhausted'}}
     syntax_pass {$g13State.syntax_status='PASS'}
     cpu_start {$g13State.counters.cpu++;if($g13State.counters.cpu -gt 2){throw 'CPU attempts exhausted'}}
     result {if($Argument -eq '--continuation-probe'){$g13State.probe=$g13Request.value}else{$g13State.results=$g13Request.value}}
     failure {$g13State.failures+=,$g13Request.value}
     default {throw 'unknown RPC'}
    }
    $g13Reply=ConvertTo-Json -InputObject @{ok=$true;value=$g13Value} -Depth 30 -Compress
    $g13Proc.StandardInput.WriteLine($g13Reply);$g13Proc.StandardInput.Flush()
    $g13Line=$g13Proc.StandardOutput.ReadLineAsync()
   } else {Start-Sleep -Milliseconds 2}
  }
  $g13Proc.WaitForExit()
  if($g13Proc.ExitCode -ne 0){throw "child exit $($g13Proc.ExitCode): $($g13Err.GetAwaiter().GetResult())"}
 } finally {if(-not $g13Proc.HasExited){$g13Proc.Kill($true);$g13Proc.WaitForExit()}}
}

# A bootstrap debit exists BEFORE reading prior accounting. It is then merged, never reset.
$g13ResumePath=Join-Path $g13Out 'resource_ledger.json'
if(Test-Path -LiteralPath $g13ResumePath){$g13Checkpoint=$g13ResumePath}
if(Test-Path -LiteralPath $g13Checkpoint){
 $g13BootstrapLimit=@{read=65536L;scans=1L;seconds=2.0}
 $g13Length=(Get-Item -LiteralPath $g13Checkpoint).Length
 if($g13Length -gt $g13BootstrapLimit.read -or $g13Clock.Elapsed.TotalSeconds -gt 2){throw 'bootstrap capacity'}
 $g13BootstrapRaw=[IO.File]::ReadAllBytes($g13Checkpoint)
 $g13Previous=ConvertFrom-Json -InputObject $g13Encoding.GetString($g13BootstrapRaw) -AsHashtable
 if($g13Previous.ContainsKey('new_work')){$g13Previous=$g13Previous.new_work}else{throw 'interrupted closure: no complete ledger, no renewed tail allowance'}
 if($g13Previous.version -ne 'G13-guard-v1' -or $g13Previous.status -eq 'PASS'){throw 'closed or foreign shared state'}
 $g13State=$g13Previous
 $g13OldOps=[Collections.Generic.List[object]]::new();foreach($g13Op in $g13State.operations){$g13OldOps.Add($g13Op)};$g13State.operations=$g13OldOps
 foreach($g13P in @('round1','round2','seal')){$g13PriorSeconds+=$g13State.phases[$g13P].seconds}
 $g13Phase=if($Mode -eq 'seal'){'seal'}else{'round2'}
 Reserve-G13 'bootstrap prior shared-state read' -Read $g13BootstrapRaw.Length -Scans 1
 if($Mode -ne 'seal'){
  if($g13State.counters.engineering -ge 6 -or $g13State.counters.implementation_revisions -ge 2){throw 'repair allocation exhausted'}
  $g13State.counters.implementation_revisions++
 }
} elseif($Mode -eq 'seal'){throw 'no cumulative state to seal'}
[IO.Directory]::CreateDirectory($g13Out) | Out-Null
$g13Success=$false
try {
 if($Mode -eq 'validate'){
  $g13State.counters.engineering++
  if($g13State.counters.engineering -gt 6){throw 'engineering allocation exhausted'}
  $g13Plan=@{identity='literal-synthetic-guard-fixture-v1';base_commit='eaecc95a6fd0e096dd2ccfd3928c676dc6aa2a54';
   scope='guard repair only';allocations=$g13Limits;old_risk_once=@{seconds=80;read=3145728;write=3145728;scans=192};
   estimates_per_round=@{seconds_risk=15;read_upper=196608;write_upper=131072;scans_upper=21;CPU_proxy_upper=67108864};
   estimate_seal=@{seconds_risk=10;read_upper=196608;write_upper=196608;scans_upper=16};
   graph=@('outer PS syntax 2 reads','Python syntax 3 reads; reuse compiled code for CPU','label scan 1; rejected top scans 0; accepted class before nested refusal 1','nested class/source scans 3','literal fixture read 1','second interpreter marker 1','seal hash cached sources 5; plan/results/fixture 3; checkpoint read 1; checkpoint hash 1','terminal ledger/receipt hash 2; terminal independent reads 3');
   counters_original=@(3,3,0,0);counters_corrected=@(2,0,0,0);
   revision_event=@{trigger='old inspected entry failed MetadataTraversalGuardGap';modified=@('direction_a/g1_3_preparation.py','scripts/prepare_direction_a_g1_3.py','scripts/prepare_direction_a_g1_3_outer.ps1','scripts/prepare_direction_a_g1_3_seal.ps1');increment=1};
   attempt_definition='same round: PS/Python syntax -> CPU -> continuation interpreter -> shared seal';
   uncertainty=@{physical_io=$null;implicit_interpreter_io=$null;historical_peak=$null};
   memory='64 MiB covers <=64 KiB inputs/RPC, <=64 op records, 3 compiled source graphs, raw/UTF8/base64/JSON and final copies; owner and child peaks polled, no torch/CUDA'}
  Write-G13 'plan.json' $g13Plan
  $g13State.counters.syntax++
  foreach($g13Script in $g13Sources[3..4]){
   $g13ScriptRaw=Read-G13 $g13Script
   $g13Tokens=$null;$g13Errors=$null
   [Management.Automation.Language.Parser]::ParseInput($g13Encoding.GetString($g13ScriptRaw),[ref]$g13Tokens,[ref]$g13Errors) | Out-Null
   if($g13Errors.Count){throw "PS syntax: $($g13Errors[0].Message)"}
  }
  Invoke-G13Child '--guard-regression'
  Invoke-G13Child '--continuation-probe'
  if($g13State.probe.probe -ne 'PASS'){throw 'continuation probe missing'}
  $g13State.results.cases[3].status='PASS';$g13State.results.cases[3].subprocess=$g13State.probe
  $g13State.results.cases[4].status='PASS'
  $g13State.results.cases[4]['terminal_witness']='receipt.json and process success after independent terminal assertion'
  $g13Success=$true
 }
} catch {
 $g13State.failures+=,@{type=$_.Exception.GetType().Name;location='outer';root_cause=$_.Exception.Message;new_scientific_results=0}
} finally {
 $g13State.phases[$g13Phase].seconds+=$g13Clock.Elapsed.TotalSeconds-$g13PhaseStart
 $g13Phase='seal';$g13PhaseStart=$g13Clock.Elapsed.TotalSeconds
 if($Mode -eq 'seal'){$g13State.counters.engineering++}
 $g13State.status=if($g13Success){'PASS'}else{'SEALED_FAILURE'}
 Write-G13 'state_checkpoint.json' $g13State
 # Own checkpoint is read under the same owner before constructing final records.
 $g13CheckpointRaw=Read-G13 'artifacts/direction_a/phaseG1_3_A_guard_v1/state_checkpoint.json'
 $g13Recovered=ConvertFrom-Json -InputObject $g13Encoding.GetString($g13CheckpointRaw) -AsHashtable
 if($g13Recovered.counters.engineering -ne $g13State.counters.engineering){throw 'checkpoint independent read mismatch'}
 $g13Checks=if($g13State.results){$g13State.results}else{@{status='NOT_RUN';original_arithmetic_14='NOT_RUN';cases=@()}}
 $g13Checks['syntax_status']=$g13State.syntax_status
 Write-G13 'selfchecks.json' $g13Checks
 if($g13State.failures.Count){Write-G13 'failure.json' @{failures=$g13State.failures}}
 $g13HashRows=[Collections.Generic.List[object]]::new()
 foreach($g13Path in @($g13Cache.Keys)){
  Reserve-G13 "hash cached $g13Path" -Scans 1
  $g13Bytes=$g13Cache[$g13Path]
  $g13HashRows.Add(@{path=$g13Path;bytes=$g13Bytes.Length;sha256=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($g13Bytes)).ToLowerInvariant()})
 }
 $g13TerminalDeadline=$g13Clock.Elapsed.TotalSeconds+2.0
 $g13State.phases.seal.seconds+=$g13Clock.Elapsed.TotalSeconds-$g13PhaseStart+2.0
 $g13PhaseStart=$g13Clock.Elapsed.TotalSeconds
 $g13Ledger=@{status=$g13State.status;new_work=$g13State;old_risk_once=@{seconds=80;read=3145728;write=3145728;scans=192;is_actual_or_proved_bound=$false};
  old_actual=@{first_read=327534;first_write=42032;first_file_scans=15;schema_scan_total=$null;guard_status='FAIL';outer_seconds=@(0.4005749,0.2895423);seal_read=86427;seal_scans=15;seal_write_including_8192_reserve=20969;seal_write_actual=$null;first_windows_peak=24158208;seal_windows_peak=97779712};
  historical_D3_reference_once=@{counts=@(6,6,4,2);seconds=395.73515180000686;write=5913736;read=31328482;scans=1159;payload=29642603849;status='closed; FAIL/null retained'};
  event_comparison=@{original_report=@(3,3,0,0);corrected_before=@(2,0,0,0);current=$g13State.counters;repair_trigger='old MetadataTraversalGuardGap; one running-failure repair';new_files_revision_cost=0};
  unknowns=@{physical_io=$null;implicit_io=$null;historical_peak=$null;whole_preparation_wall=$null};
  preparation=@{known_read_bytes_lower_bound=($g13StartupKnownRead);known_command_seconds=@(0.5953938,0.5494498,0.7694805,0.6405423,0.6142781);total_read_bytes=$null;total_write_bytes=$null;Git_internal_io=$null;issue='bounded startup-accounting totals unknown, recorded once; no scientific results';read_target=1048576;write_target=131072;wall_target_seconds=1800};
  allocations=$g13Limits;terminal=@{accounting='exact fixed point for final writes, hashes and independent reads';readback_required=$true;new_total_seconds_upper=$g13PriorSeconds+$g13Clock.Elapsed.TotalSeconds+2.0}}
 $g13Receipt=@{status=$g13State.status;ledger_readback_consistent=$true;manifest_readback_consistent=$true;terminal_after_all_writes=$true;new_used=$g13State.used;counts=$g13State.counters;
  final_readback_condition='all three terminal files must match cached bytes, ledger totals and receipt totals; process success is emitted only afterward'}
 # Fixed-width hashes break byte-length dependencies. Final self-hash is excluded explicitly.
 $g13Manifest=@{algorithm='SHA-256 raw bytes; each hash counts one scan';files=$g13HashRows;excluded=@('artifact_hashes.json self');terminal_hashes=@{ledger=('0'*64);receipt=('0'*64)}}
 $g13BaseUsed=@{};$g13BasePhase=@{};foreach($g13K in @('read','write','scans')){$g13BaseUsed[$g13K]=$g13State.used[$g13K];$g13BasePhase[$g13K]=$g13State.phases.seal[$g13K]}
 # Terminal operation records have constant labels; byte lengths converge monotonically in <=8 iterations.
 $g13Terminal=@{label='terminal: ledger/receipt/manifest writes + independent reads + ledger/receipt hashes';phase='seal';read=0L;write=0L;scans=5L;proxy=67108864L}
 $g13State.operations.Add($g13Terminal)
 $g13Last=-1L
 for($g13Iteration=0;$g13Iteration -lt 8;$g13Iteration++){
  $g13LedgerRaw=Bytes-G13 $g13Ledger;$g13ReceiptRaw=Bytes-G13 $g13Receipt;$g13ManifestRaw=Bytes-G13 $g13Manifest
  $g13Total=$g13LedgerRaw.Length+$g13ReceiptRaw.Length+$g13ManifestRaw.Length
  if($g13Total -eq $g13Last){break}
  $g13Last=$g13Total;$g13Terminal.read=$g13Total;$g13Terminal.write=$g13Total
  $g13State.used.read=$g13BaseUsed.read+$g13Total;$g13State.used.write=$g13BaseUsed.write+$g13Total;$g13State.used.scans=$g13BaseUsed.scans+5
  $g13State.phases.seal.read=$g13BasePhase.read+$g13Total;$g13State.phases.seal.write=$g13BasePhase.write+$g13Total;$g13State.phases.seal.scans=$g13BasePhase.scans+5
 }
 if($g13Iteration -ge 8){throw 'terminal byte fixed point did not converge'}
 foreach($g13K in @('read','write','scans')){if($g13State.phases.seal[$g13K] -gt $g13Limits.seal[$g13K]){throw 'terminal reservation refused'}}
 $g13Manifest.terminal_hashes.ledger=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($g13LedgerRaw)).ToLowerInvariant()
 $g13Manifest.terminal_hashes.receipt=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($g13ReceiptRaw)).ToLowerInvariant()
 $g13ManifestRaw=Bytes-G13 $g13Manifest
 $g13Names=@('resource_ledger.json','receipt.json','artifact_hashes.json');$g13Finals=@($g13LedgerRaw,$g13ReceiptRaw,$g13ManifestRaw)
 for($g13I=0;$g13I -lt 3;$g13I++){Check-G13;[IO.File]::WriteAllBytes((Join-Path $g13Out $g13Names[$g13I]),$g13Finals[$g13I])}
 for($g13I=0;$g13I -lt 3;$g13I++){
  Check-G13
  $g13FinalRead=[IO.File]::ReadAllBytes((Join-Path $g13Out $g13Names[$g13I]))
  if(-not [Linq.Enumerable]::SequenceEqual[byte]($g13FinalRead,$g13Finals[$g13I])){throw 'terminal bytes mismatch'}
  if($g13I -lt 2){
   $g13FinalParsed=ConvertFrom-Json -InputObject $g13Encoding.GetString($g13FinalRead) -AsHashtable
   $g13FinalUsed=if($g13I -eq 0){$g13FinalParsed.new_work.used}else{$g13FinalParsed.new_used}
   foreach($g13K in @('read','write','scans')){if($g13FinalUsed[$g13K] -ne $g13State.used[$g13K]){throw 'terminal accounting mismatch'}}
  }
 }
 Check-G13
 Write-Output (ConvertTo-Json -InputObject @{status=$g13State.status;used=$g13State.used;counts=$g13State.counters;observed_seconds=$g13PriorSeconds+$g13Clock.Elapsed.TotalSeconds;terminal_readback='PASS'} -Compress)
}
if(-not $g13Success){exit 1}
