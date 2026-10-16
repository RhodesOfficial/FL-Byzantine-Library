# Failure-only closure. Never reads upstream metadata or starts a test/interpreter.
$ErrorActionPreference='Stop'
$g13SealClock=[Diagnostics.Stopwatch]::StartNew()
$g13SealRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$g13SealOut=Join-Path $g13SealRoot 'artifacts/direction_a/phaseG1_3_A_v1'
$g13SealUsed=@{read=0L;write=0L;scans=0L}
$g13SealOps=[Collections.Generic.List[object]]::new()
function Reserve-G13Seal([string]$Label,[long]$Read=0,[long]$Write=0,[long]$Scans=0){
    if($g13SealClock.Elapsed.TotalSeconds -gt 25){throw 'Seal deadline; five seconds retained'}
    if($g13SealUsed.read+$Read -gt 1048576 -or $g13SealUsed.write+$Write -gt 1048576 -or $g13SealUsed.scans+$Scans -gt 64){throw 'Seal reservation refused'}
    $g13SealUsed.read+=$Read;$g13SealUsed.write+=$Write;$g13SealUsed.scans+=$Scans
    $g13SealOps.Add(@{label=$Label;read=$Read;write=$Write;scans=$Scans})
}
function Read-G13Seal([string]$Path){
    $g13Length=(Get-Item -LiteralPath $Path).Length
    Reserve-G13Seal -Label "read $Path" -Read $g13Length -Scans 1
    return [IO.File]::ReadAllBytes($Path)
}
function Write-G13Seal([string]$Name,$Value){
    Reserve-G13Seal -Label "serialize $Name (16 MiB graph/buffer reserve)"
    $g13Raw=[Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Depth 40)+"`n")
    if($g13Raw.Length -gt 262144){throw 'Seal serialization cap'}
    Reserve-G13Seal -Label "write $Name" -Write $g13Raw.Length
    [IO.File]::WriteAllBytes((Join-Path $g13SealOut $Name),$g13Raw)
}
$g13PriorBytes=Read-G13Seal (Join-Path $g13SealOut 'resource_ledger.json')
$g13Prior=[Text.Encoding]::UTF8.GetString($g13PriorBytes) | ConvertFrom-Json -AsHashtable
$g13Outer=[Text.Encoding]::UTF8.GetString((Read-G13Seal (Join-Path $g13SealOut 'outer_receipt.json'))) | ConvertFrom-Json -AsHashtable
$g13Prior.used.write+=$g13PriorBytes.Length # prior snapshot preceded its own write
$g13Failure=@{type='MetadataTraversalGuardGap';location='scripts/prepare_direction_a_g1_3.py:schema:list(v.items())';
    root_cause='Full dictionary materialization, including class label_mapping, had no preceding traversal reservation.';
    action='SEALED; no repair, syntax suite or CPU suite launched after detection';
    repetitions=1;new_scientific_results=0;real_probability_calculations=0;real_gradient_reads=0;formal_events=0;real_fee_calculations=0;
    schema_scans_actual=$null;counted_file_reads=15;historical_compliance='not re-certified'}
Write-G13Seal 'failure.json' $g13Failure
Write-G13Seal 'selfchecks.json' @{status='NOT_RUN_ENGINEERING_SEALED';passed=0;failed=0;not_run=@(
    'uniform probabilities','signed source replacement','scale invariance','single/same/near source','zero gradients',
    'target cancellation','nonuniform with zero bias','empty return','illegal N/Z/nonfinite','probability bound',
    'paired three-seed statistic','degenerate all-direction residual','independent rational oracle','resource rejection injection');
    synthetic_seeds_used=@();registered_seed_trajectories=0;syntax_starts=0;cpu_suite_starts=0}
Write-G13Seal 'next_stage_envelope.json' @{stage='B';authorized=$false;candidate_budget_effective=$false;
    status='INCOMPLETE_A_GUARD_FAILURE';read_bytes=$null;write_bytes=$null;scans=$null;operations=$null;temporary_copy_bytes=$null;
    seconds=$null;windows_peak_bytes=$null;cpu_proxy_bytes=$null;
    required_inputs=@('A guarded synthetic acceptance','counts/source traversal bound','complete message locator/identity index',
    'source reference Linf scale or certified norm bound','true-error bound distinct from 2e-6 historical tolerance',
    'per-stage reads/hash/readback/seal costs','bounded blind measurement authorization');
    blind_measurement_proposal=@{enabled=$false;inputs='D/G only; no s/L/p, diagnostics or events';
    steps=@('stat 80 fixed messages','bound one-at-a-time deserialization copies','freeze outer timeout and read/scan/seal envelopes',
    'only after review, measure one bounded read-and-uniform-arithmetic block, charge all failure costs to B');
    numerical_budget=$null};C_entries=0}
$g13Ledger=@{status='SEALED_GUARD_FAILURE';first_run=$g13Prior;outer=$g13Outer;
    limits=@{seconds=120;read=4194304;write=4194304;scans=256;windows=2147483648;cpu_proxy=268435456;CUDA=0};
    fixed_allocations=@{seconds=@(50,40,30);read=@(2097152,1048576,1048576);write=@(2097152,1048576,1048576);scans=@(128,64,64)};
    risk_allocations_are_actual_or_proved_bounds=$false;unknowns=@{schema_traversal_scans=$null;physical_io=$null;implicit_interpreter_io=$null;historical_peak=$null;whole_preparation_wall=$null};
    counters=@{engineering=2;implementation_revisions=2;syntax=0;cpu=0;real_entries=0;real_fee_entries=0};
    counter_explanation='Initial implementation/metadata inspection plus failure-only sealing helper; no repair or verification retry.';
    cumulative_limits=@{engineering=6;implementation_revisions=6;syntax=6;cpu=6};task_allocations=@{engineering=6;implementation_revisions=3;syntax=2;cpu=2};
    remaining_task_counts=@{engineering=4;implementation_revisions=1;syntax=2;cpu=2};
    first_run_time_and_io_scope='Explicit Python actions only; outer covers startup/time; unreserved schema traversals prevent compliance claim.';
    seal_plan=@{seconds=30;read=1048576;write=1048576;scans=64;cpu_proxy=16777216;working_set_sampling='current PowerShell process peak';
    ledger_readback_write_reserve=65536;manifest_read_write_reserve=65536;self_hash='excluded'};
    preparation=@{known_command_wall_seconds=$null;observed_command_seconds=@(0.6352618,0.8746109,0.7665321,0.7492819,0.6466718,0.7383232,0.7203319,0.6505856,0.7037322);known_read_bytes=$null;known_write_bytes=$null;internal_io=$null;wall_target_seconds=1800;
    issue='Fresh-shell variable and two guessed source paths caused bounded preparation command errors; no scientific calculation.';
    source_writes='new A code and closure only; exact final Git blob sizes in manifest';input_content_limit=1048576};
    historical_once=@{D3_used=@(6,6,4,2);formal_entries='2/2 closed';fee_entries='2/2 closed';
    seconds=395.73515180000686;write_bytes=5913736;read_bytes=31328482;scans=1159;payload_bytes=29642603849;historical_FAIL_retained=$true};
    failures=@($g13Failure)}
Write-G13Seal 'resource_ledger.json' $g13Ledger
$g13Readback=[Text.Encoding]::UTF8.GetString((Read-G13Seal (Join-Path $g13SealOut 'resource_ledger.json'))) | ConvertFrom-Json -AsHashtable
if($g13Readback.counters.engineering -ne 2 -or $g13Readback.first_run.used.read -ne $g13Prior.used.read -or $g13Readback.status -ne 'SEALED_GUARD_FAILURE'){throw 'Independent closure readback mismatch'}
$g13Files=@('preregistration.json','input_index.json','selfchecks.json','next_stage_envelope.json','resource_ledger.json','failure.json','outer_receipt.json')
$g13Hashes=[Collections.Generic.List[object]]::new()
foreach($g13Name in $g13Files){
    $g13Bytes=Read-G13Seal (Join-Path $g13SealOut $g13Name)
    $g13Hashes.Add(@{path="artifacts/direction_a/phaseG1_3_A_v1/$g13Name";bytes=$g13Bytes.Length;sha256=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($g13Bytes)).ToLowerInvariant()})
}
foreach($g13Name in @('direction_a/g1_3_preparation.py','scripts/prepare_direction_a_g1_3.py','scripts/prepare_direction_a_g1_3_outer.ps1','scripts/prepare_direction_a_g1_3_seal.ps1')){
    $g13Bytes=Read-G13Seal (Join-Path $g13SealRoot $g13Name)
    $g13Hashes.Add(@{path=$g13Name;bytes=$g13Bytes.Length;sha256=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($g13Bytes)).ToLowerInvariant()})
}
Write-G13Seal 'artifact_hashes.json' @{algorithm='SHA-256 raw bytes of NEW A artifacts only';files=$g13Hashes;
    excluded=@('artifact_hashes.json self','seal_receipt.json terminal receipt');upstream_binary_rehashes=0}
$g13Manifest=[Text.Encoding]::UTF8.GetString((Read-G13Seal (Join-Path $g13SealOut 'artifact_hashes.json'))) | ConvertFrom-Json
if($g13Manifest.files.Count -ne 11){throw 'Closure manifest readback mismatch'}
Reserve-G13Seal -Label 'terminal receipt allowance' -Write 8192
$g13Receipt=@{status='SEALED';ledger_readback_consistent=$true;manifest_entries=11;elapsed_seconds=$g13SealClock.Elapsed.TotalSeconds;
    explicit_operations=$g13SealOps;used_including_terminal_write_allowance=$g13SealUsed;
    terminal_write_allowance_is_actual=$false;physical_io_bytes=$null;implicit_io_bytes=$null;
    working_set_peak_bytes=[Diagnostics.Process]::GetCurrentProcess().PeakWorkingSet64;cpu_known_proxy_upper_bytes=16777216;
    A_scans_compliance='FAIL: unreserved schema traversals unknown';
    missing_files=@('tests/test_direction_a_g1_3_preparation.py','docs/DIRECTION_A_G1_3_IMPLEMENTATION_SPEC_v1.md')}
[IO.File]::WriteAllText((Join-Path $g13SealOut 'seal_receipt.json'),($g13Receipt | ConvertTo-Json -Depth 40),[Text.UTF8Encoding]::new($false))
Write-Output ($g13Receipt | Select-Object status,elapsed_seconds,used_including_terminal_write_allowance,ledger_readback_consistent | ConvertTo-Json)
