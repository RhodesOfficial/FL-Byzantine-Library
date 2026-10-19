param([ValidateSet('V1','V2','S3')][string]$Run='V1')
$ErrorActionPreference='Stop'
# A00: immutable authorization, time and all six accounts exist before data reads.
$g13Clock=[Diagnostics.Stopwatch]::StartNew()
$g13Root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$g13Base='artifacts/direction_a/phaseG1_3_A_d5_v1'
$g13Rel="$g13Base/$Run"
$g13Out=Join-Path $g13Root $g13Rel
$g13Utf8=[Text.UTF8Encoding]::new($false,$true)
$g13Auth=@{commit='0af98abd746a71530efc1eb644ac963183c66b60';base='451476e68a77481ce8307dc67d51b665a65f1795';decision='docs/DIRECTION_A_G1_3_ADJUDICATION_v4.md';contract='docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md section seven D5';task='docs/workflow/TO_EXECUTOR.md';D5='author approved option A 2026-10-19; bounded synthetic recovery';real_entries=0;old_evidence_commit='81e7be55319e10cb9c5c25b4eb49131886f00fc2';cumulative_limits=@(8,6,6,6);counts_at_authorization=@(5,2,3,3);allocation=@(3,2,2,2)}
$g13Limits=@{}
foreach($g13Name in @('V1','V2')){$g13Limits[$g13Name]=@{seconds=900;read=8388608L;write=4194304L;scans=64000L}}
foreach($g13Name in @('S1','S2','S3')){$g13Limits[$g13Name]=@{seconds=120;read=8388608L;write=4194304L;scans=16384L}}
$g13Limits.I=@{seconds=10;read=524288L;write=0L;scans=12L}
$g13Used=@{};foreach($g13Name in $g13Limits.Keys){$g13Used[$g13Name]=@{read=0L;write=0L;scans=0L;seconds=0.0}}
$g13Reserved=@{};foreach($g13Name in $g13Limits.Keys){$g13Reserved[$g13Name]=@{read=0L;write=0L;scans=0L}}
$g13Phase=if($Run -eq 'S3'){'I'}else{$Run}
$g13PhaseStart=0.0
$g13Cache=@{}
$g13Actions=[Collections.Generic.List[object]]::new()
$g13Failures=[Collections.Generic.List[object]]::new()
$g13Counters=@{engineering=5;implementation_revisions=2;syntax=3;cpu=3}
$g13Syntax='NOT_RUN';$g13CPU='NOT_RUN';$g13Status='NOT_COMPLETED';$g13Lease=$null;$g13LeaseReport=$null
$g13Probe=$null;$g13Inherited=@{};$g13Peak=0L;$g13Frames=0;$g13PipeBytes=0L
$g13Witness=@{};$g13Complete=@();$g13Partial=@();$g13NotStarted=@('A02','A03','A04')
$g13Token=[Guid]::NewGuid().ToString('N')
$g13Sources=@('direction_a/g1_3_preparation.py','scripts/prepare_direction_a_g1_3.py','tests/test_direction_a_g1_3_preparation.py','scripts/prepare_direction_a_g1_3_outer.ps1','scripts/prepare_direction_a_g1_3_seal.ps1')
$g13D5ActionBounds=@{baseline_scan_upper=37641;additional_V_scan_upper=16384;combined_V_scan_upper=54025;new_bootstrap_read=524288;source_read=262144;metadata_read=1048576;output_read=2097152;IPC_read=2097152;combined_read_upper=6029312;output_write=2097152;IPC_write=2097152;combined_write_upper=4194304;oracle_calls=2;oracle_ops_each=32768;oracle_max_bits=1024;oracle_sqrt_steps_upper=1024;additional_scalar_ops_upper=131072;all_primitive_risk_limit=725873600;parser_cases_upper=32;parser_accounts=6;parser_fields=4;parser_string_digits=20;account_test_scans=8192;S_new_validation_scans=2048;S_observer_bytes=4096;S_observer_scans=5;S_graph_and_failure_reserved=16384;auxiliary_risk=33554432;CPU_proxy=244908032;seconds_are_risk=$true;platform_seconds=$null}
$g13Metadata=@(
 'artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR10-N20-v1/counts.json',
 'artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR10-N20-v1/info.json',
 'artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR100-N20-v1/counts.json',
 'artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR100-N20-v1/info.json',
 'artifacts/direction_a/phaseG1_2_full_v1/preregistration.json',
 'artifacts/direction_a/phaseG1_2_full_v1/reference_acceptance.json',
 'artifacts/direction_a/phaseG1_2_full_v1/artifact_hashes.json',
 'artifacts/direction_a/phaseG1_2_full_v1/archive_verification.json',
 'artifacts/direction_a/backbone_preparation_v1/manifest.json',
 'artifacts/direction_a/phaseG1_1_formal_F_resume_v1/mechanism.json',
 'artifacts/direction_a/phaseG1_1_formal_F_resume_v1/input_checks.json',
 'artifacts/direction_a/phaseG1_1_formal_F_resume_v1/preregistration.json',
 'artifacts/direction_a/phaseG1_1_formal_F_resume_v1/replay_checks.json',
 'artifacts/direction_a/phaseG1_1_v1/speed_assignments.json',
 'artifacts/direction_a/phaseG1_1_cost_M_v1/measurements.json')
$g13Objects=@('0f53f6ce8e7f4723f7921947938ba5c419df5b09','fa4370a9ac417f24b93b2996fad1897ee3847398','ab37f8240a71055a1238174176a68d51e465107a','87ef2e4ba79378776975956a91eaaa02e9bb8220','c5bede12ee149329d3a22a24c2985e1bea633932','f6f0457990df506635f1d6a3f597a1f2e445897d','70cb121ab7324f6c170b5cc692165add98c0a175','8b65168715721277b33224d9bc0ad6e0eefd6cec','d56aaef5a6e0ddf6733353edf3653186531b1dea','0c41d16721dea9223e9b9ce6f709c66c2dc100b1','240ed0f20bf8598bb0c207a103cba41040106b50','32a3cf21187f77a92f7af18dd7b8719f8de4116e','eb2eef7e63d07f0cb7ee448a370a9d64fe8664fd','a0eda996ba440382900823463e77c73f497e7700','33d4a3f37d93dfd9f5d13e4fda5f46aeb29c7c23')
$g13Identities=@{};for($g13Index=0;$g13Index -lt 15;$g13Index++){$g13Identities[$g13Metadata[$g13Index]]=$g13Objects[$g13Index]}
# Windows Job Object limits the owner and inherited descendants before Python.
# No BREAKAWAY flag; job total committed memory is capped, and combined working
# sets are additionally inspected. An independent job timer kills all children.
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Diagnostics;
using System.Threading;
public static class G13D4Job {
 [StructLayout(LayoutKind.Sequential)] struct Basic { public long User,Job; public uint Flags; public UIntPtr MinWS,MaxWS; public uint Active; public UIntPtr Affinity; public uint Priority,Scheduling; }
 [StructLayout(LayoutKind.Sequential)] struct IO { public ulong A,B,C,D,E,F; }
 [StructLayout(LayoutKind.Sequential)] struct Extended { public Basic B; public IO IO; public UIntPtr Process,Job,PeakProcess,PeakJob; }
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr CreateJobObject(IntPtr a,string n);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr j,IntPtr p);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool SetInformationJobObject(IntPtr j,int c,ref Extended e,uint n);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool QueryInformationJobObject(IntPtr j,int c,IntPtr b,uint n,out uint used);
 [DllImport("kernel32.dll")] static extern bool TerminateJobObject(IntPtr j,uint code);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool IsProcessInJob(IntPtr p,IntPtr j,out bool value);
 static IntPtr job; static Timer timer; static long deadline; public static long Peak;
 public static void Start(int milliseconds) {
  job=CreateJobObject(IntPtr.Zero,null); if(job==IntPtr.Zero) throw new Exception("CreateJobObject");
  Extended e=new Extended(); e.B.Flags=0x200|0x2000; e.Job=(UIntPtr)2147483648UL;
  if(!SetInformationJobObject(job,9,ref e,(uint)Marshal.SizeOf(e))) throw new Exception("Set Job memory "+Marshal.GetLastWin32Error());
  if(!AssignProcessToJobObject(job,Process.GetCurrentProcess().Handle)) throw new Exception("Assign owner Job "+Marshal.GetLastWin32Error());
  deadline=Environment.TickCount64+milliseconds;
  timer=new Timer(_=>TerminateJobObject(job,124),null,Math.Max(1,milliseconds),Timeout.Infinite);
 }
 public static void Deadline(int seconds) { Interlocked.Exchange(ref deadline,Environment.TickCount64+seconds*1000L); timer.Change(seconds*1000,Timeout.Infinite); }
 public static long Sample() {
  IntPtr b=Marshal.AllocHGlobal(8+64*IntPtr.Size); try {
   uint used; if(!QueryInformationJobObject(job,3,b,(uint)(8+64*IntPtr.Size),out used)) throw new Exception("Job tree query");
   int n=Marshal.ReadInt32(b,4); if(n>64) throw new Exception("Job process count cap");
   long total=0; for(int i=0;i<n;i++) { int id=(int)Marshal.ReadIntPtr(b,8+i*IntPtr.Size); try { using(Process p=Process.GetProcessById(id)) { total+=p.WorkingSet64; } } catch(ArgumentException) {} }
   Peak=Math.Max(Peak,total); if(total>2147483648L) { TerminateJobObject(job,125); throw new Exception("Job working set cap"); } return total;
  } finally { Marshal.FreeHGlobal(b); }
 }
 public static void Finish() { if(timer!=null) timer.Dispose(); }
 public static bool Contains(int id) { bool value; using(Process p=Process.GetProcessById(id)) { if(!IsProcessInJob(p.Handle,job,out value)) throw new Exception("IsProcessInJob"); } return value; }
}
'@
$g13InitialLimit=if($Run -eq 'S3'){10}else{900}
[G13D4Job]::Start([Math]::Max(1,[int][Math]::Floor(($g13InitialLimit-$g13Clock.Elapsed.TotalSeconds)*1000)))

function Check-G13 {
 [void][G13D4Job]::Sample()
 $g13Now=$g13Clock.Elapsed.TotalSeconds-$g13PhaseStart
 $g13Hard=$g13Limits[$g13Phase].seconds
 if($g13Now -ge $g13Hard){throw "hard phase time $g13Phase"}
 if($g13Phase -like 'V*' -and $g13Now -ge 880){throw 'active soft deadline: preserve S'}
 if($g13Phase -like 'S*' -and -not $script:g13Terminal -and $g13Now -ge 100){throw 'S terminal reserve boundary'}
}
function Capacity-G13([long]$Read=0,[long]$Write=0,[long]$Scans=0) {
 Check-G13
 foreach($g13K in @('read','write','scans')){
  $g13D=@{read=$Read;write=$Write;scans=$Scans}[$g13K]
  $g13U=$g13Used[$g13Phase][$g13K];$g13R=$g13Reserved[$g13Phase][$g13K];$g13L=$g13Limits[$g13Phase][$g13K]
  if($g13U -isnot [long] -or $g13R -isnot [long]){throw 'non-long running account'}
  if($g13D -lt 0 -or $g13U -lt 0 -or $g13U -gt $g13L -or $g13R -lt 0 -or $g13R -gt $g13L-$g13U -or $g13D -gt $g13L-$g13U-$g13R){throw "quota before access $g13Phase/$g13K"}
 }
}
function Charge-G13([string]$Label,[long]$Read=0,[long]$Write=0,[long]$Scans=0) {
 Capacity-G13 -Read $Read -Write $Write -Scans $Scans
 $g13Used[$g13Phase].read=Add-G13 $g13Used[$g13Phase].read $Read $g13Limits[$g13Phase].read
 $g13Used[$g13Phase].write=Add-G13 $g13Used[$g13Phase].write $Write $g13Limits[$g13Phase].write
 $g13Used[$g13Phase].scans=Add-G13 $g13Used[$g13Phase].scans $Scans $g13Limits[$g13Phase].scans
 if($g13Actions.Count -ge 480){throw 'operation record capacity'}
 $g13Actions.Add(@{action=$Label;phase=$g13Phase;read=$Read;write=$Write;scans=$Scans})
}
function Integer-G13($Value,[long]$Limit,[string]$Field) {
 if($Value -is [string]){
  if($Value -cnotmatch '\A[0-9]{20}\z'){throw "account integer format $Field"}
 } elseif($Value -isnot [int] -and $Value -isnot [long] -and $Value -isnot [System.Numerics.BigInteger]){throw "account integer type $Field"}
 $g13Wide=[System.Numerics.BigInteger]::Parse([string]$Value,[Globalization.CultureInfo]::InvariantCulture)
 if($g13Wide -lt 0 -or $g13Wide -gt [long]::MaxValue -or $g13Wide -gt $Limit){throw "account integer range $Field"}
 return [long]$g13Wide
}
function Add-G13([long]$Used,[long]$Delta,[long]$Limit) {
 if($Used -lt 0 -or $Used -gt $Limit -or $Delta -lt 0 -or $Delta -gt $Limit-$Used){throw 'checked remaining before addition'}
 return [long]($Used+$Delta)
}
function Accounts-G13($Ledger,[string]$Source) {
 # Return a completely validated candidate. Callers install only after success.
 if($Source -ne $g13Auth.commit -or $Ledger.schema -ne 'G13-D5-ledger' -or $Ledger.authorization.commit -ne $Source){throw 'account source/schema refused'}
 if($Ledger.accounts.Count -ne 6 -or $Ledger.reserved.Count -ne 6 -or $Ledger.limits.Count -ne 6){throw 'account set refused'}
 $g13Candidate=@{};$g13Totals=@{read=0L;write=0L;scans=0L}
 foreach($g13N in $g13Limits.Keys){
  if(-not $Ledger.accounts.Contains($g13N) -or -not $Ledger.reserved.Contains($g13N) -or -not $Ledger.limits.Contains($g13N)){throw 'missing account'}
  $g13A=$Ledger.accounts[$g13N];$g13R=$Ledger.reserved[$g13N]
  if($g13A.Count -ne 4 -or $g13R.Count -ne 3){throw 'account field set refused'}
  $g13Candidate[$g13N]=@{}
  foreach($g13K in @('read','write','scans')){
   if(-not $g13A.Contains($g13K) -or -not $g13R.Contains($g13K)){throw 'missing account field'}
   $g13Limit=$g13Limits[$g13N][$g13K]
   if((Integer-G13 $Ledger.limits[$g13N][$g13K] $g13Limit 'limit') -ne $g13Limit){throw 'foreign account limit'}
   $g13Value=Integer-G13 $g13A[$g13K] $g13Limit "$g13N/$g13K"
   $g13Reservation=Integer-G13 $g13R[$g13K] $g13Limit 'reserved'
   if($g13Reservation -gt $g13Limit-$g13Value){throw 'reservation exceeds remaining'}
   $g13Candidate[$g13N][$g13K]=$g13Value
   $g13Totals[$g13K]=Add-G13 $g13Totals[$g13K] $g13Value ([long]::MaxValue)
  }
  $g13Seconds=$g13A.seconds
  if(($g13Seconds -isnot [double] -and $g13Seconds -isnot [int] -and $g13Seconds -isnot [long]) -or -not [double]::IsFinite([double]$g13Seconds) -or $g13Seconds -lt 0 -or $g13Seconds -gt $g13Limits[$g13N].seconds -or $Ledger.limits[$g13N].seconds -ne $g13Limits[$g13N].seconds){throw 'account seconds refused'}
  $g13Candidate[$g13N].seconds=[double]$g13Seconds
 }
 foreach($g13K in @('read','write','scans')){if((Integer-G13 $Ledger.used[$g13K] ([long]::MaxValue) 'total') -ne $g13Totals[$g13K]){throw 'account total mismatch'}}
 return $g13Candidate
}
function AccountTests-G13 {
 # Bound all cases and graph copies before constructing or parsing fixtures.
 Charge-G13 'D5 strict account tests <=32 cases, six accounts and copies' -Scans 8192
 $g13Fixture=@{schema='G13-D5-ledger';authorization=@{commit=$g13Auth.commit};accounts=@{};reserved=$g13Reserved;limits=$g13Limits;used=@{read=0L;write=0L;scans=0L}}
 foreach($g13N in $g13Limits.Keys){$g13Fixture.accounts[$g13N]=@{read=('0'*20);write=('0'*20);scans=('0'*20);seconds=0.0}}
 $g13JSON=ConvertTo-Json $g13Fixture -Depth 10 -Compress
 $g13F=ConvertFrom-Json $g13JSON -AsHashtable
 $g13Z=Accounts-G13 $g13F $g13Auth.commit
 $g13Zero=Add-G13 $g13Z.S2.read 214680 $g13Limits.S2.read
 if($g13Zero -isnot [long] -or $g13Zero -ne 214680){throw 'D20 zero addition failed'}
 $g13F.accounts.S2.read='00000000000000000017';$g13F.used.read=17L
 $g13NZ=Accounts-G13 $g13F $g13Auth.commit
 $g13Nonzero=Add-G13 $g13NZ.S2.read 214680 $g13Limits.S2.read
 if($g13Nonzero -ne 214697 -or $g13Nonzero -isnot [long]){throw 'D20 nonzero addition failed'}
 $g13Snapshot=@{};foreach($g13K in @('read','write','scans')){$g13Snapshot[$g13K]=$g13NZ.S2[$g13K].ToString('D20')}
 if($g13NZ.S2.read -isnot [long]){throw 'snapshot mutated runtime'}
 $g13F=ConvertFrom-Json $g13JSON -AsHashtable;$g13F.accounts.S2.read=214680L;$g13F.used.read=214680L
 $g13JSONInteger=Accounts-G13 $g13F $g13Auth.commit
 if($g13JSONInteger.S2.read -isnot [long] -or $g13JSONInteger.S2.read -ne 214680){throw 'legal JSON integer refused'}
 $g13Rejected=0;$g13Cases=0;$g13Accesses=0
 foreach($g13Text in @('null','true','-1','1.5','1e0','"+0000000000000000001"','" 0000000000000000000"','"0000000000000000000 "','"0000000000000000000"','"000000000000000000000"','"０００００００００００００００００００００００"','9223372036854775808','"99999999999999999999"','8388609')){
  $g13Cases++
  $g13F=ConvertFrom-Json $g13JSON -AsHashtable
  $g13F.accounts.S2.read=ConvertFrom-Json $g13Text -AsHashtable
  try{[void](Accounts-G13 $g13F $g13Auth.commit);$g13Accesses++}catch{$g13Rejected++}
 }
 foreach($g13Case in @('missing','schema','source','account','total','reservation','seconds','pollution')){
  $g13Cases++;$g13F=ConvertFrom-Json $g13JSON -AsHashtable;$g13Origin=$g13Auth.commit
  switch($g13Case){
   missing {$g13F.accounts.S2.Remove('write')}
   schema {$g13F.schema='unknown'}
   source {$g13Origin=$g13Auth.old_evidence_commit}
   account {$g13F.accounts.X=$g13F.accounts.S2}
   total {$g13F.used.read=1L}
   reservation {$g13F.reserved.S2.read=8388609L}
   seconds {$g13F.accounts.S2.seconds=121.0}
   pollution {$g13F.accounts.S2.read='0000000000000000000021468000'}
  }
  try{[void](Accounts-G13 $g13F $g13Origin);$g13Accesses++}catch{$g13Rejected++}
 }
 try{[void](Add-G13 ([long]::MaxValue) 1 ([long]::MaxValue));$g13Accesses++}catch{$g13Rejected++};$g13Cases++
 if($g13Rejected -ne $g13Cases -or $g13Accesses -ne 0){throw "account illegal case accepted $g13Rejected/$g13Cases"}
 $script:g13Witness.account_types=@{status='PASS';expected_rejections=$g13Rejected;zero_accesses=$g13Accesses;zero_plus_214680=$g13Zero;nonzero17_plus_214680=$g13Nonzero;legal_JSON_integer=$g13JSONInteger.S2.read;runtime_type=$g13NZ.S2.read.GetType().Name;snapshot='separate D20 dictionary';invalids='null/bool/negative/fraction/exponent/sign/space/length/Unicode/Int64/quota/missing/schema/source/total/reservation/seconds/pollution';arithmetic='remaining then Int64 add, including terminal'}
}
function Raw-G13([string]$Path,[long]$Max=2097152) {
 # Paths are admitted by callers before stat/open, never discovered by scanning.
 Check-G13
 $g13Length=(Get-Item -LiteralPath (Join-Path $g13Root $Path)).Length
 if($g13Length -gt $Max){throw 'file length cap'}
 Charge-G13 "read $Path" -Read $g13Length -Scans 1
 $g13Raw=[IO.File]::ReadAllBytes((Join-Path $g13Root $Path))
 if($g13Raw.Length -ne $g13Length){throw 'file length changed'}
 $g13Cache[$Path]=$g13Raw
 return ,$g13Raw
}
function Hash-G13([byte[]]$Raw,[string]$Label) {
 Charge-G13 "hash $Label" -Scans 1
 return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($Raw)).ToLowerInvariant()
}
function GitIdentity-G13([byte[]]$Raw,[string]$Expected) {
 Charge-G13 'A00 LF Git object hash' -Scans 1
 $g13Normalized=$g13Utf8.GetBytes($g13Utf8.GetString($Raw).Replace("`r`n","`n").Replace("`r","`n"))
 $g13Header=$g13Utf8.GetBytes("blob $($g13Normalized.Length)"+[char]0)
 $g13Blob=[byte[]]::new($g13Header.Length+$g13Normalized.Length)
 [Array]::Copy($g13Header,0,$g13Blob,0,$g13Header.Length);[Array]::Copy($g13Normalized,0,$g13Blob,$g13Header.Length,$g13Normalized.Length)
 $g13Actual=[Convert]::ToHexString([Security.Cryptography.SHA1]::HashData($g13Blob)).ToLowerInvariant()
 if($g13Actual -ne $Expected){throw 'frozen predecessor Git identity mismatch'}
}
function Containers-G13($Value,[int]$Depth=0) {
 if($Depth -gt 16){throw 'output depth cap'}
 $g13N=0
 if($Value -is [Collections.IDictionary]){
  $g13N=1;foreach($g13V in $Value.Values){$g13N+=Containers-G13 $g13V ($Depth+1)}
 } elseif($Value -is [Collections.IList]){
  $g13N=1;foreach($g13V in $Value){$g13N+=Containers-G13 $g13V ($Depth+1)}
 } elseif($Value -is [string] -and $g13Utf8.GetByteCount($Value) -gt 8192){throw 'output scalar cap'}
 if($g13N -gt 2048){throw 'container cap'}
 return $g13N
}
function Encode-G13($Value,[long]$Max=2097152) {
 Capacity-G13 -Scans 2048
 $g13Nodes=Containers-G13 $Value
 Charge-G13 'bounded serialization graph' -Scans $g13Nodes
 $g13Raw=$g13Utf8.GetBytes((ConvertTo-Json -InputObject $Value -Depth 20 -Compress)+"`n")
 if($g13Raw.Length -gt $Max){throw 'serialization byte cap'}
 return ,$g13Raw
}
function Write-G13([string]$Name,$Value,[long]$Max=2097152) {
 $g13Raw=Encode-G13 $Value $Max
 Charge-G13 "write $Name" -Write $g13Raw.Length
 [IO.File]::WriteAllBytes((Join-Path $g13Out $Name),$g13Raw)
 $g13Cache["$g13Rel/$Name"]=$g13Raw
}
function Snapshot-G13 {
 $g13Available=@{};foreach($g13K in @('read','write','scans')){$g13Available[$g13K]=[long]$g13Limits[$g13Phase][$g13K]-[long]$g13Used[$g13Phase][$g13K]-[long]$g13Reserved[$g13Phase][$g13K]}
 return @{phase=$g13Phase;used=@{read=$g13Used[$g13Phase].read;write=$g13Used[$g13Phase].write;scans=$g13Used[$g13Phase].scans};reserved=$g13Reserved[$g13Phase];available=$g13Available;job='inherited non-breakaway 2GiB';counts=$g13Counters}
}
function Pipe-G13([string]$Text,[bool]$Send) {
 $g13Length=$g13Utf8.GetByteCount($Text)+1
 if($g13Length -gt 16384 -or $g13Frames -ge 128 -or $g13PipeBytes+2*$g13Length -gt 2097152){throw 'IPC length/frame/aggregate limit'}
 # Both endpoints charged explicitly: sender write, receiver read.
 Charge-G13 'IPC both endpoints receive/send/copies' -Read $g13Length -Write $g13Length -Scans 3
 $script:g13Frames++;$script:g13PipeBytes+=2*$g13Length
}
function Admit-G13($Request) {
 if($Request.token -ne $g13Token){throw 'unauthorized before any file access'}
 if($Request.action -eq 'source' -and ($Request.path -notin $g13Sources[0..2] -or $Request.index -lt 0 -or $Request.index -ge 24)){throw 'source whitelist before access'}
 if($Request.action -eq 'cache_chunk' -and $Request.path -notin $g13Metadata){throw 'metadata whitelist before access'}
}
function LeaseAvailable-G13 {
 if($null -ne $g13Lease){throw 'kernel lease cannot renew'}
}
function SettlementAvailable-G13 {
 if($null -eq $g13Lease -or $null -ne $g13LeaseReport){throw 'invalid lease settlement'}
}
function Child-G13([string]$Mode) {
 Check-G13
 $g13Info=[Diagnostics.ProcessStartInfo]::new()
 $g13Info.FileName='E:\anaconda3\python.exe';$g13Info.WorkingDirectory=$g13Root
 $g13Info.ArgumentList.Add('-B');$g13Info.ArgumentList.Add('-c')
 $g13Info.ArgumentList.Add('import sys,json,base64; p=json.loads(sys.stdin.readline(16385)); exec(compile(base64.b64decode(p["runner"]),"scripts/prepare_direction_a_g1_3.py","exec"),{"__name__":"__main__"})')
 $g13Info.UseShellExecute=$false;$g13Info.CreateNoWindow=$true
 $g13Info.RedirectStandardInput=$true;$g13Info.RedirectStandardOutput=$true;$g13Info.RedirectStandardError=$true
 $g13Info.StandardInputEncoding=$g13Utf8;$g13Info.StandardOutputEncoding=$g13Utf8;$g13Info.StandardErrorEncoding=$g13Utf8
 $g13Info.Environment['G13_RPC_ACTIVE']='D4-v1';$g13Info.Environment['G13_CHILD_MODE']=$Mode
 $g13Info.Environment['G13_TOKEN']=$g13Token;$g13Info.Environment['G13_OUT']=$g13Out
 $g13Proc=[Diagnostics.Process]::new();$g13Proc.StartInfo=$g13Info
 # Owner is already a Job member: children inherit before their first instruction.
 [void]$g13Proc.Start()
 if(-not [G13D4Job]::Contains($g13Proc.Id)){$g13Proc.Kill($true);throw 'child absent from enforced Job tree'}
 $g13Inherited[$Mode]=@{pid=$g13Proc.Id;job_member=$true;verified_before_bootstrap=$true}
 $g13Err=$g13Proc.StandardError.ReadToEndAsync()
 $g13Boot=ConvertTo-Json -InputObject @{runner=[Convert]::ToBase64String($g13Cache[$g13Sources[1]])} -Compress
 Pipe-G13 $g13Boot $true;$g13Proc.StandardInput.WriteLine($g13Boot);$g13Proc.StandardInput.Flush()
 Capacity-G13 -Read 16384 -Write 16384 -Scans 3
 $g13Line=$g13Proc.StandardOutput.ReadLineAsync()
 try {
  while($true){
   Check-G13
   if(-not $g13Line.IsCompleted){Start-Sleep -Milliseconds 4;continue}
   $g13Text=$g13Line.GetAwaiter().GetResult()
   if($null -eq $g13Text){break}
   Pipe-G13 $g13Text $false
   $g13Req=ConvertFrom-Json -InputObject $g13Text -AsHashtable
   Admit-G13 $g13Req
   $g13Value=$null
   switch($g13Req.action){
    source {
     if($g13Req.path -notin $g13Sources[0..2] -or $g13Req.index -lt 0 -or $g13Req.index -ge 24){throw 'source whitelist before access'}
     $g13Raw=$g13Cache[$g13Req.path];$g13Offset=11000*[int]$g13Req.index
     $g13Count=[Math]::Min(11000,$g13Raw.Length-$g13Offset)
     if($g13Count -lt 0){throw 'chunk offset'}
     $g13Value=@{data=[Convert]::ToBase64String($g13Raw,$g13Offset,$g13Count);last=($g13Offset+$g13Count -eq $g13Raw.Length)}
    }
    syntax_start {if($g13Syntax -ne 'IN_PROGRESS'){throw 'syntax must use owner reservation'}}
    syntax_pass {$script:g13Syntax='PASS'}
    cpu_start {$script:g13CPU='IN_PROGRESS';$g13Counters.cpu++}
    identities {$g13Value=$g13Identities}
    lease {
     LeaseAvailable-G13
     Capacity-G13 -Read 1048576 -Write 2097152 -Scans 40000
     $script:g13Lease=@{limits=@{read=1048576L;write=2097152L;scans=40000L};seconds=[Math]::Max(1,875-($g13Clock.Elapsed.TotalSeconds-$g13PhaseStart))}
     foreach($g13K in @('read','write','scans')){$g13Reserved[$g13Phase][$g13K]=$g13Lease.limits[$g13K]}
     $g13LeaseAccess=0;$g13LeaseRefused=$false
     $g13OwnerSnapshot=Snapshot-G13
     try {Capacity-G13 -Read ([long]$g13OwnerSnapshot.available.read+1);$g13LeaseAccess++}catch{if($_.Exception.Message -notlike 'quota before access*'){throw};$g13LeaseRefused=$true}
     if(-not $g13LeaseRefused -or $g13LeaseAccess -ne 0){throw 'owner reserved lease accessible to IPC'}
     Charge-G13 'owner reserved lease refusal witness' -Scans 1
     $g13Witness.owner_reservation=@{status='PASS';zero_accesses=$g13LeaseAccess;reserved_read=$g13Reserved[$g13Phase].read;available_read_before_probe=$g13OwnerSnapshot.available.read;settlement='one report only; reservations retained on missing report'}
     $g13DuplicateDenied=$false
     try{LeaseAvailable-G13}catch{if($_.Exception.Message -ne 'kernel lease cannot renew'){throw};$g13DuplicateDenied=$true}
     if(-not $g13DuplicateDenied){throw 'duplicate reservation accepted'}
     $g13Witness.owner_reservation.duplicate_expected_refusal=$true
     $g13Value=$g13Lease
    }
    cache_chunk {
     if($g13Req.path -notin $g13Metadata){throw 'metadata cache path outside whitelist'}
     $g13Raw=[Convert]::FromBase64String($g13Req.data)
     if(-not $g13Cache.ContainsKey($g13Req.path)){$g13Cache[$g13Req.path]=[Collections.Generic.List[byte]]::new()}
     if($g13Cache[$g13Req.path].Count+$g13Raw.Length -gt 1048576){throw 'metadata cache cap'}
     $g13Cache[$g13Req.path].AddRange([byte[]]$g13Raw)
    }
    settle {
     SettlementAvailable-G13
     $g13Settlement=@{}
     foreach($g13K in @('read','write','scans')){$g13Settlement[$g13K]=Integer-G13 $g13Req.report.used[$g13K] $g13Lease.limits[$g13K] 'lease usage'}
     foreach($g13K in @('read','write','scans')){$g13Reserved[$g13Phase][$g13K]=0L}
     Charge-G13 'kernel settled explicit read/write/traversal debits' -Read $g13Settlement.read -Write $g13Settlement.write -Scans $g13Settlement.scans
     $script:g13LeaseReport=$g13Req.report;$script:g13Status=$g13Req.status
     $script:g13Complete=$g13Req.completed;$script:g13Partial=$g13Req.partial;$script:g13NotStarted=$g13Req.not_started
     foreach($g13Failure in $g13Req.failures){$g13Failures.Add($g13Failure)}
     $script:g13CPU=if($g13Status -eq 'PASS'){'PASS'}else{'FAIL'}
     $g13BeforeDuplicate=Snapshot-G13;$g13DuplicateDenied=$false
     try{SettlementAvailable-G13}catch{if($_.Exception.Message -ne 'invalid lease settlement'){throw};$g13DuplicateDenied=$true}
     if(-not $g13DuplicateDenied -or (Snapshot-G13).used.read -ne $g13BeforeDuplicate.used.read){throw 'duplicate settlement charged'}
     $g13Witness.owner_reservation.duplicate_settlement_expected_refusal=$true
     $g13Witness.owner_reservation.settlements=1
    }
    snapshot {$g13Value=Snapshot-G13;$script:g13ProbeBefore=$g13Value.used.scans}
    continuation {if($g13Req.expected -ne $g13ProbeBefore -or $g13Req.expected -le 0){throw 'probe ledger inheritance'};Charge-G13 'second child continuation witness' -Scans 1;$g13Value=Snapshot-G13}
    probe {$script:g13Probe=$g13Req.value}
    default {throw 'unknown child operation'}
   }
   $g13Reply=ConvertTo-Json -InputObject @{ok=$true;value=$g13Value} -Depth 15 -Compress
   Pipe-G13 $g13Reply $true;$g13Proc.StandardInput.WriteLine($g13Reply);$g13Proc.StandardInput.Flush()
   Capacity-G13 -Read 16384 -Write 16384 -Scans 3
   $g13Line=$g13Proc.StandardOutput.ReadLineAsync()
  }
  $g13Proc.WaitForExit()
  $g13Error=$g13Err.GetAwaiter().GetResult()
  if($g13Error.Length){Pipe-G13 $g13Error $false}
  if($g13Proc.ExitCode -ne 0){throw "child $Mode exit $($g13Proc.ExitCode): $($g13Error.Substring(0,[Math]::Min(512,$g13Error.Length)))"}
 } finally {if(-not $g13Proc.HasExited){$g13Proc.Kill($true);$g13Proc.WaitForExit()};$g13Proc.Dispose()}
}

$g13Carry=$null;$g13Plan=$null;$g13Ready=$false;$g13Terminal=$false
try {
 if(Test-Path -LiteralPath $g13Out){throw 'output round exists: no overwrite/no renewed tail'}
 [void][IO.Directory]::CreateDirectory($g13Out)
 # The complete cycle and failure tails are allocated before the first read.
 $g13Ready=$true
 $g13Counters.engineering++
 if($Run -ne 'S3'){$g13Counters.implementation_revisions++}
 $g13CountsBefore=@(5,2,3,3)
 $g13Names=@('plan.json','resource_ledger.json','receipt.json','artifact_hashes.json')
 $g13PriorDir=if($Run -eq 'V1'){'artifacts/direction_a/phaseG1_3_A_d4_v1'}elseif($Run -eq 'V2'){"$g13Base/V1"}else{"$g13Base/V2"}
 $g13D4Inputs=@('V1/resource_ledger.json','V2/plan.json','V2/authorization.json','V2/carry.json','V2/bundle.json')
 $g13D4Objects=@('2602f910301252ebc2f7fe1cb045ca0090c12275','1e15781180cec85c5e68a25855f2f2679319080a','77f757590c2316782ef447d49e065a0a1629d41d','c74f0efded69e8e6329d2f7079e405d6b6d768bc','1a77b4d4c726729f0fe966692953e7cdb1be9444')
 if($Run -eq 'V1'){$g13Names=$g13D4Inputs}
 $g13Prior=@{};$g13BootstrapBytes=0L
 Capacity-G13 -Read 524288 -Scans $(if($Run -eq 'S3'){12}else{8192})
 for($g13Index=0;$g13Index -lt $g13Names.Count;$g13Index++){
  $g13Path="$g13PriorDir/$($g13Names[$g13Index])"
  $g13Raw=Raw-G13 $g13Path 262144
  $g13BootstrapBytes+=$g13Raw.Length
  if($g13BootstrapBytes -gt 524288){throw 'A00 bootstrap bytes'}
  if($Run -eq 'V1'){
   GitIdentity-G13 $g13Raw $g13D4Objects[$g13Index]
  }else{[void](Hash-G13 $g13Raw $g13Path)}
  Charge-G13 'A00 predecessor bounded parse/account traversal' -Scans $(if($Run -eq 'S3'){1}else{1024})
  $g13Prior[$g13Names[$g13Index]]=ConvertFrom-Json -InputObject $g13Utf8.GetString($g13Raw) -AsHashtable
 }
 if($Run -eq 'V1'){
  if($g13Prior['V1/resource_ledger.json'].schema -ne 'G13-D4-ledger' -or $g13Prior['V2/carry.json'].times_carried -ne 1 -or $g13Prior['V2/bundle.json'].assertions.Count -ne 37){throw 'old historical identity/partial inventory mismatch'}
  $g13Carry=@{commit=$g13Auth.old_evidence_commit;times_carried=1;old_block_limit=@{seconds=2290;read=46661632;write=25165824;scans=177420};known_read_lower=2403093;known_recorded_write=1535965;known_recorded_scans=13042;old_total_seconds=$null;old_S2_complete=$null;old_peak=$null;old_FAIL='preserved';old_accounts_installed=$false;identities=$g13D4Objects;inventory=@{complete=@('V2/A02','V2/A04');partial_A03=@{pass=36;interrupted=1;not_started=55};missing=@('V2/failure.json','V2/state_checkpoint.json','V2/resource_ledger.json','V2/receipt.json','V2/artifact_hashes.json');not_started=@('second child','old I/S3')};old_V1_ledger='81e7be5:artifacts/direction_a/phaseG1_3_A_d4_v1/V1/resource_ledger.json';old_V2_four_files='81e7be5:artifacts/direction_a/phaseG1_3_A_d4_v1/V2/';old_S2_polluted_values='original evidence only; never parsed as actual usage';historical_total=$null}
 } else {
  $g13Prev=$g13Prior['resource_ledger.json']
  $g13CountsBefore=@([int]$g13Prev.counters.engineering,[int]$g13Prev.counters.implementation_revisions,[int]$g13Prev.counters.syntax,[int]$g13Prev.counters.cpu)
  if(-not $g13Prior['receipt.json'].terminal_readback_required -or $g13Prev.carry_once.times_carried -ne 1){throw 'foreign/incomplete predecessor'}
  if($g13Prior['plan.json'].authorization.commit -ne $g13Auth.commit -or $g13Prev.authorization.commit -ne $g13Auth.commit -or $g13Prev.process_tree.job_memory_limit -ne 2147483648L){throw 'foreign D5 predecessor'}
  if($Run -eq 'V2' -and ($g13CountsBefore[0] -ne 6 -or $g13CountsBefore[1] -ne 3 -or $g13CountsBefore[2] -notin @(3,4) -or $g13CountsBefore[3] -notin @(3,4) -or $g13Prev.status -eq 'PASS')){throw 'V2 requires one completed failing validation, not a successful rerun'}
  if($g13Prev.kernel_reserved -and -not $g13Prev.kernel){throw 'unsettled predecessor cannot resume'}
  foreach($g13K in @('read','write','scans')){if($g13Prev.used[$g13K] -ne $g13Prior['receipt.json'].used[$g13K]){throw 'prior ledger/receipt totals mismatch'}}
  $g13Carry=$g13Prev.carry_once
  $g13Validated=Accounts-G13 $g13Prev $g13Auth.commit
  foreach($g13K in $g13Prev.counters.Keys){$g13Counters[$g13K]=[int]$g13Prev.counters[$g13K]}
  $g13Counters.engineering++;if($Run -eq 'V2'){$g13Counters.implementation_revisions++}
  foreach($g13Name in $g13Validated.Keys){if($g13Name -ne $g13Phase){$g13Used[$g13Name]=$g13Validated[$g13Name]}}
  $g13PriorManifest=$g13Prior['artifact_hashes.json']
  foreach($g13Pair in @(@('resource_ledger.json','ledger'),@('receipt.json','receipt'))){if((Hash-G13 $g13Cache["$g13PriorDir/$($g13Pair[0])"] 'D5 predecessor terminal identity') -ne $g13PriorManifest.terminal[$g13Pair[1]]){throw 'predecessor manifest identity mismatch'}}
 }
 if($g13Counters.engineering -gt 8 -or $g13Counters.implementation_revisions -gt 4){throw 'cumulative attempt/revision cap'}
 if($Run -eq 'V1'){$g13BaselineBundle=$g13Prior['V2/bundle.json']}
 elseif($Run -eq 'V2'){
  $g13BaselineRaw=Raw-G13 'artifacts/direction_a/phaseG1_3_A_d4_v1/V2/bundle.json' 262144
  GitIdentity-G13 $g13BaselineRaw '1a77b4d4c726729f0fe966692953e7cdb1be9444'
  Charge-G13 'fixed old A02/A04 regression reference parse' -Scans 1024
  $g13BaselineBundle=ConvertFrom-Json $g13Utf8.GetString($g13BaselineRaw) -AsHashtable
 }
 $g13Plan=@{schema='G13-D4-plan-v1';authorization=$g13Auth;run=$Run;limits=$g13Limits;predecessor=$g13PriorDir;counts_before=$g13CountsBefore;two_rounds_and_independent_seal_frozen=@{seconds=2170;read=42467328;write=20971520;scans=177164};this_round_frozen=@{seconds=1020;read=16777216;write=8388608;scans=80384};independent_seal_untouched=@{seconds=130;read=8912896;write=4194304;scans=16396};operation_derivation='A_BUDGET_PROPOSAL sections 2-4; additional radius graph <= 32h per M/Pj; detailed actual named events separate from conservative scan debits';real_entries=0;unknowns=@{physical_io=$null;implicit_interpreter_io=$null;platform_completion_seconds=$null;platform_peak_proof=$null};lease='A02-A05 nonrenewable; owner reserves atomically, IPC sees available only, settle once';bootstrap_bytes=$g13BootstrapBytes;bootstrap_scans=12;V_absolute_seconds=900;V_startup_seconds_included=$true;S_active_seconds=100;S_terminal_seconds=20}
 $g13Plan.schema='G13-D5-plan-v1'
 $g13Plan.namespace='D5'
 $g13Plan.cumulative=@{before=@(5,2,3,3);limits=@(8,6,6,6);allocation=@(3,2,2,2)}
 $g13Plan.d5_action_bounds=$g13D5ActionBounds
 if($g13Plan.d5_action_bounds.combined_V_scan_upper -gt $g13Limits.V1.scans){throw 'D5 static scan bound'}
 Write-G13 'plan.json' $g13Plan 65536
 Write-G13 'authorization.json' $g13Auth 16384
 Write-G13 'carry.json' @{predecessor=$g13PriorDir;times_carried=1;old_block='2290-second D4/history entirely isolated';full_record='resource_ledger.json/carry_once';new_namespace='D5';new_accounts_from_old=$false} 65536
 $g13Ready=$true
 if($Run -ne 'S3'){
  $g13Syntax='IN_PROGRESS';$g13Counters.syntax++
  $g13SourceBytes=0L
  foreach($g13Path in $g13Sources){
   $g13Raw=Raw-G13 $g13Path 262144;$g13SourceBytes+=$g13Raw.Length
   if($g13SourceBytes -gt 262144){throw 'five-source aggregate cap'}
   [void](Hash-G13 $g13Raw $g13Path)
   Charge-G13 'A01 compile/transfer source scan' -Scans 1
   if($g13Path.EndsWith('.ps1')){
    $g13Tokens=$null;$g13Errors=$null
    [void][Management.Automation.Language.Parser]::ParseInput($g13Utf8.GetString($g13Raw),[ref]$g13Tokens,[ref]$g13Errors)
    if($g13Errors.Count){throw "PS syntax: $($g13Errors[0].Message)"}
   }
  }
  # Changed authorization and byte-cap entry checks: refusal happens before stat.
  $g13Access=0;$g13Rejections=0
  foreach($g13Invalid in @(@{token='invalid';action='source';path=$g13Sources[0];index=0},@{token=$g13Token;action='source';path='../forbidden';index=0})){
   try {Admit-G13 $g13Invalid;$g13Access++} catch {$g13Rejections++}
  }
  try {Pipe-G13 ('x'*16384) $false;$g13Access++} catch {$g13Rejections++}
  Charge-G13 'changed interface actual refusal witnesses' -Scans 3
  if($g13Access -ne 0 -or $g13Rejections -ne 3){throw 'changed interface accepted forbidden access'}
  $g13Witness=@{authorization_refusal_zero_access=$g13Access;byte_cap_refusal_zero_access=$g13Access;actual_rejections=$g13Rejections;status='PASS';dispatch='same Admit-G13 and Pipe-G13 as actual child requests'}
  AccountTests-G13
  # An actual injected failure with a finally read, separately from happy-path S2.
  $g13TinyPath="$g13Rel/_finally_probe.json";$g13TinyBytes=[byte[]]@(123,125)
  $g13TinyFinally=$false;$g13TinyCaught=$false
  try {
   try {
    Charge-G13 'small-byte fault witness write' -Write 2 -Scans 1
    [IO.File]::WriteAllBytes((Join-Path $g13Root $g13TinyPath),$g13TinyBytes)
    throw 'INJECTED_SMALL_BYTE_FAULT'
   } finally {
    $g13TinyRead=Raw-G13 $g13TinyPath 2
    Charge-G13 'small-byte finally byte comparison/hash' -Scans 2
    $g13TinyHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($g13TinyRead)).ToLowerInvariant()
    if(-not [Linq.Enumerable]::SequenceEqual[byte]($g13TinyRead,$g13TinyBytes)){throw 'small-byte finally mismatch'}
    $g13TinyFinally=$true
   }
  }catch{if($_.Exception.Message -ne 'INJECTED_SMALL_BYTE_FAULT'){throw};$g13TinyCaught=$true}
  if(-not $g13TinyFinally -or -not $g13TinyCaught){throw 'fault did not execute finally'}
  Charge-G13 'small-byte witness cleanup' -Scans 1
  [IO.File]::Delete((Join-Path $g13Root $g13TinyPath));$g13Cache.Remove($g13TinyPath)
  $g13Witness.small_byte_seal=@{status='PASS';injected='INJECTED_SMALL_BYTE_FAULT';finally_executed=$g13TinyFinally;independent_readback='PASS';sha256=$g13TinyHash;read=2;write=2;scans=5;scientific_results=0}
  Child-G13 'validate'
  Child-G13 'probe'
  if($g13Probe.status -ne 'PASS'){throw 'second subprocess inheritance witness missing'}
  Capacity-G13 -Read 2097152 -Scans 2048
  $g13AuditRaw=Raw-G13 "$g13Rel/bundle.json"
  Charge-G13 'D5 independent bundle audit and fixed-input regression graphs' -Scans 1024
  $g13Audit=ConvertFrom-Json $g13Utf8.GetString($g13AuditRaw) -AsHashtable
  if($g13Audit.assertions.Count -ne 92 -or $g13Audit.inputs.Count -ne 15 -or $g13Audit.bindings.Count -ne 4 -or $g13Audit.B_requirements.Count -ne 220){throw 'D5 independent bundle cardinality'}
  $g13AuditDims=@{};$g13AuditGroups=@{}
  foreach($g13A in $g13Audit.assertions){
   if($g13A.status -ne 'PASS' -or $g13A.h -notin @(1290,12900) -or $g13A.checks -match '=FAIL'){throw 'D5 independent assertion incomplete'}
   if(-not $g13AuditDims.ContainsKey([string]$g13A.h)){$g13AuditDims[[string]$g13A.h]=0}
   $g13AuditDims[[string]$g13A.h]++;$g13AuditGroups[$g13A.group]=$true
  }
  if($g13AuditDims['1290'] -ne 46 -or $g13AuditDims['12900'] -ne 46 -or $g13AuditGroups.Count -ne 14 -or -not $g13Audit.assertions[-1].precision_witness){throw 'D5 independent dimensions/groups/precision witness'}
  $g13OracleRows=@($g13Audit.assertions | Where-Object {$_.Contains('independent_error_oracle')})
  if($g13OracleRows.Count -ne 2){throw 'D5 independent error oracle records missing'}
  foreach($g13A in $g13OracleRows){if($g13A.independent_error_oracle.outer_margin_q -ne 32 -or -not $g13A.independent_error_oracle.independent){throw 'D5 frozen independent margin changed'}}
  foreach($g13Value in $g13Audit.counters.Values){if($g13Value -ne 0){throw 'new scientific result or real entry: stop'}}
  if($Run -ne 'S3'){
   foreach($g13Field in @('inputs','bindings','B_requirements')){
    $g13NewField=ConvertTo-Json -InputObject $g13Audit[$g13Field] -Depth 20 -Compress
    $g13OldField=ConvertTo-Json -InputObject $g13BaselineBundle[$g13Field] -Depth 20 -Compress
    if($g13NewField -cne $g13OldField){throw "frozen A02/A04 regression changed $g13Field"}
   }
  }
  $g13Witness.fixed_input_regression=@{status='PASS';source='81e7be5:D4/V2/bundle.json';fields=@('inputs','bindings','B_requirements');semantic_equality=$true;new_scientific_results=0}
  Write-G13 'independent_acceptance.json' @{status='PASS';dimensions=$g13AuditDims;groups=14;calls=92;error_oracle_rows=2;frozen_margin_q=32;runtime_accounts=$g13Witness.account_types;fixed_input_regression=$g13Witness.fixed_input_regression;inherited_processes=$g13Inherited;old_history_compliance='NOT_RETROACTIVELY_APPROVED';complete_A='NOT_PASSED'} 16384
 } else {$g13Status='SEALED_ONLY'}
} catch {
 $g13Failures.Add(@{type=$_.Exception.GetType().Name;location='outer/'+$g13Phase;root_cause=$_.Exception.Message.Substring(0,[Math]::Min(512,$_.Exception.Message.Length));new_scientific_results=0})
 $g13Status='NOT_COMPLETED'
} finally {
 if($g13Ready){
  $g13Used[$g13Phase].seconds=$g13Clock.Elapsed.TotalSeconds-$g13PhaseStart
  $g13Phase=if($Run -eq 'V1'){'S1'}elseif($Run -eq 'V2'){'S2'}else{'S3'}
  $g13PhaseStart=$g13Clock.Elapsed.TotalSeconds
  [G13D4Job]::Deadline(120)
  try {
   if($null -ne $g13Lease -and $null -eq $g13LeaseReport){$g13Partial+=,'unsettled kernel lease: actual cost unknown';$g13Status='NOT_COMPLETED'}
   if(Test-Path -LiteralPath (Join-Path $g13Out 'bundle.json')){
    $g13BundleRaw=Raw-G13 "$g13Rel/bundle.json"
    Capacity-G13 -Scans 2048
    $g13Bundle=ConvertFrom-Json -InputObject $g13Utf8.GetString($g13BundleRaw) -AsHashtable
    Charge-G13 'S bundle parse graph' -Scans (Containers-G13 $g13Bundle)
   } else {
    $g13Bundle=@{schema='G13-D5-v1';status='NOT_RUN';inputs=@();bindings=@();assertions=@();B_requirements=@();not_started=@('A02','A03','A04');failures=@()}
    Write-G13 'bundle.json' $g13Bundle
    $g13BundleRaw=Raw-G13 "$g13Rel/bundle.json"
   }
   Write-G13 'failure.json' @{failures=@($g13Failures.ToArray());new_scientific_results=0} 16384
   Write-G13 'state_checkpoint.json' @{schema='G13-D5-checkpoint';run=$Run;status=$g13Status;counters=$g13Counters;complete=$g13Complete;partial=$g13Partial;not_started=$g13NotStarted;accounts=$g13Used;never_renew_tail=$true} 131072
   foreach($g13Name in @('state_checkpoint.json','failure.json')){
    $g13Expected=$g13Cache["$g13Rel/$g13Name"];$g13Read=Raw-G13 "$g13Rel/$g13Name"
    if(-not [Linq.Enumerable]::SequenceEqual[byte]($g13Read,$g13Expected)){throw 'S checkpoint/failure independent read mismatch'}
   }
   $g13Rows=[Collections.Generic.List[object]]::new()
   foreach($g13Path in @($g13Cache.Keys)){
    $g13Raw=[byte[]]$g13Cache[$g13Path]
    $g13Rows.Add(@{path=$g13Path;bytes=$g13Raw.Length;sha256=(Hash-G13 $g13Raw $g13Path)})
   }
   if($g13Rows.Count -gt 64){throw 'manifest file cap'}
   $g13Manifest=@{schema='G13-D4-manifest';files=$g13Rows;excluded=@('artifact_hashes.json self');terminal=@{ledger=('0'*64);receipt=('0'*64)}}
   $g13Manifest.schema='G13-D5-manifest'
   $g13Manifest.excluded+=,'terminal_observation.json: post-terminal 4096-byte record; detached SHA256 in final stdout'
   Charge-G13 'D5 independent terminal account/manifest/receipt validation graphs' -Scans 2048
   Charge-G13 'D5 fixed post-terminal observation write/read/hash and graph' -Read 4096 -Write 4096 -Scans 5
   $g13FinalUsed=@{};foreach($g13K in @('read','write','scans')){$g13FinalUsed[$g13K]='0'*20}
   $g13Ledger=@{schema='G13-D4-ledger';run=$Run;status=$g13Status;authorization=$g13Auth;carry_once=$g13Carry;accounts=$g13Used;reserved=$g13Reserved;limits=$g13Limits;counters=$g13Counters;actions=$g13Actions;kernel=$g13LeaseReport;kernel_reserved=$g13Lease;failures=$g13Failures;used=$g13FinalUsed;old_history_FAIL_null='preserved';unknowns=@{physical_io=$null;implicit_interpreter_io=$null;startup_total_io=$null;startup_whole_wall=$null;historical_peak=$null;external_kill_tail=$null;actual_total_scans=$null};process_tree=@{job_memory_limit=2147483648L;peak_combined_working_set=[G13D4Job]::Peak;CPU_proxy_limit=268435456;CUDA=0;V_absolute_limit_seconds=900;startup_included=$true;independent_timer='one-shot Job termination timer, reset only at transition to S'};cost_quality='file/IPC logical bytes counted; scan/operation upper debits distinct from named event actuals; exact total traversal/primitive count remains null';terminal=@{fixed_width=20;readback_required=$true;seconds_used_before_terminal=0.0;tail_seconds_reserved=20;seconds_after_final_readback=$null;observation_boundary='ledger serialized before final writes/readbacks; tool stdout observes later total; no exact end-to-end terminal seconds persisted'}}
   $g13Receipt=@{schema='G13-D4-receipt';run=$Run;status=$g13Status;counters=$g13Counters;used=$g13FinalUsed;syntax=$g13Syntax;cpu=$g13CPU;probe=$g13Probe;changed_interfaces=$g13Witness;terminal_readback_required=$true;closure='success exit after byte, semantic, hash checks';unsettled_kernel=($null -ne $g13Lease -and $null -eq $g13LeaseReport);ipc_frames=$g13Frames;ipc_both_endpoint_bytes=$g13PipeBytes}
   $g13Ledger.schema='G13-D5-ledger';$g13Ledger.namespace='D5'
   $g13Receipt.schema='G13-D5-receipt';$g13Receipt.namespace='D5';$g13Receipt.authorization=$g13Auth;$g13Receipt.inherited_processes=$g13Inherited
   $g13Ledger.terminal.observation_boundary='ledger seconds are pre-terminal lower observations; terminal_observation.json records last terminal readback; observation write/read and exit remainder remain null, bounded by unchanged 120s S limit'
   $g13Ledger.terminal.seconds_used_before_terminal=$g13Clock.Elapsed.TotalSeconds-$g13PhaseStart
   $g13Used[$g13Phase].seconds=$g13Ledger.terminal.seconds_used_before_terminal
   # Three terminal graphs are measured BEFORE the fixed, two serializations.
   Capacity-G13 -Scans 8192
   $g13Nodes=(Containers-G13 $g13Ledger)+(Containers-G13 $g13Receipt)+(Containers-G13 $g13Manifest)
   if($g13Nodes+(Containers-G13 $g13Bundle) -gt 2048){throw 'whole-package containers >2048'}
   Charge-G13 'terminal two serializations/readback/copy graphs' -Scans (6*$g13Nodes)
   $g13TerminalRow=@{action='terminal file writes/readbacks + ledger/receipt independent hashes';phase=$g13Phase;read=('0'*20);write=('0'*20);scans=7}
   $g13Actions.Add($g13TerminalRow)
   foreach($g13K in @('read','write','scans')){
    $g13Total=0L;foreach($g13Name in $g13Used.Keys){$g13Total=Add-G13 $g13Total $g13Used[$g13Name][$g13K] ([long]::MaxValue)}
    $g13FinalUsed[$g13K]=$g13Total.ToString('D20')
   }
   # account values also fixed-width, so reserving the final writes cannot alter lengths.
   $g13AccountSnapshot=@{};foreach($g13Name in $g13Used.Keys){$g13AccountSnapshot[$g13Name]=@{read=([long]$g13Used[$g13Name].read).ToString('D20');write=([long]$g13Used[$g13Name].write).ToString('D20');scans=([long]$g13Used[$g13Name].scans).ToString('D20');seconds=$g13Used[$g13Name].seconds}}
   $g13Ledger.accounts=$g13AccountSnapshot
   $g13LedgerRaw=$g13Utf8.GetBytes((ConvertTo-Json -InputObject $g13Ledger -Depth 20 -Compress)+"`n")
   $g13ReceiptRaw=$g13Utf8.GetBytes((ConvertTo-Json -InputObject $g13Receipt -Depth 20 -Compress)+"`n")
   $g13ManifestRaw=$g13Utf8.GetBytes((ConvertTo-Json -InputObject $g13Manifest -Depth 20 -Compress)+"`n")
   $g13Total=$g13LedgerRaw.Length+$g13ReceiptRaw.Length+$g13ManifestRaw.Length
   Capacity-G13 -Read $g13Total -Write $g13Total -Scans 7
   $g13Used[$g13Phase].read=Add-G13 $g13Used[$g13Phase].read $g13Total $g13Limits[$g13Phase].read
   $g13Used[$g13Phase].write=Add-G13 $g13Used[$g13Phase].write $g13Total $g13Limits[$g13Phase].write
   $g13Used[$g13Phase].scans=Add-G13 $g13Used[$g13Phase].scans 7 $g13Limits[$g13Phase].scans
   $g13TerminalRow.read=$g13Total.ToString('D20');$g13TerminalRow.write=$g13Total.ToString('D20')
   foreach($g13K in @('read','write','scans')){
    $g13AccountSnapshot[$g13Phase][$g13K]=([long]$g13Used[$g13Phase][$g13K]).ToString('D20')
    $g13Sum=0L;foreach($g13Name in $g13Used.Keys){$g13Sum=Add-G13 $g13Sum $g13Used[$g13Name][$g13K] ([long]::MaxValue)}
    $g13FinalUsed[$g13K]=$g13Sum.ToString('D20')
   }
   $g13LedgerRaw=$g13Utf8.GetBytes((ConvertTo-Json -InputObject $g13Ledger -Depth 20 -Compress)+"`n")
   $g13ReceiptRaw=$g13Utf8.GetBytes((ConvertTo-Json -InputObject $g13Receipt -Depth 20 -Compress)+"`n")
   $g13Manifest.terminal.ledger=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($g13LedgerRaw)).ToLowerInvariant()
   $g13Manifest.terminal.receipt=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($g13ReceiptRaw)).ToLowerInvariant()
   $g13ManifestRaw=$g13Utf8.GetBytes((ConvertTo-Json -InputObject $g13Manifest -Depth 20 -Compress)+"`n")
   if($g13Total -ne $g13LedgerRaw.Length+$g13ReceiptRaw.Length+$g13ManifestRaw.Length){throw 'fixed-width terminal size changed'}
   if($g13LedgerRaw.Length -gt 262144 -or $g13ReceiptRaw.Length -gt 16384 -or $g13ManifestRaw.Length -gt 32768){throw 'terminal individual byte cap'}
   $g13Terminal=$true
   $g13FinalNames=@('resource_ledger.json','receipt.json','artifact_hashes.json')
   $g13FinalRaw=@($g13LedgerRaw,$g13ReceiptRaw,$g13ManifestRaw)
   $g13Readback=@{}
   for($g13Index=0;$g13Index -lt 3;$g13Index++){
    Check-G13;[IO.File]::WriteAllBytes((Join-Path $g13Out $g13FinalNames[$g13Index]),$g13FinalRaw[$g13Index])
   }
   for($g13Index=0;$g13Index -lt 3;$g13Index++){
    Check-G13
    $g13Read=[IO.File]::ReadAllBytes((Join-Path $g13Out $g13FinalNames[$g13Index]))
    if(-not [Linq.Enumerable]::SequenceEqual[byte]($g13Read,$g13FinalRaw[$g13Index])){throw 'terminal independent byte mismatch'}
    $g13Parsed=ConvertFrom-Json -InputObject $g13Utf8.GetString($g13Read) -AsHashtable
    $g13Readback[$g13FinalNames[$g13Index]]=$g13Read
    if($g13Index -lt 2){foreach($g13K in @('read','write','scans')){if($g13Parsed.used[$g13K] -ne $g13FinalUsed[$g13K]){throw 'ledger/receipt total mismatch'}}}
    if($g13Index -eq 0){$g13ParsedAccounts=Accounts-G13 $g13Parsed $g13Auth.commit;foreach($g13N in $g13Used.Keys){foreach($g13K in @('read','write','scans')){if($g13Used[$g13N][$g13K] -isnot [long] -or $g13ParsedAccounts[$g13N][$g13K] -ne $g13Used[$g13N][$g13K]){throw 'independent account readback mismatch'}}}}
    if($g13Index -eq 2){
     foreach($g13Pair in @(@('resource_ledger.json','ledger'),@('receipt.json','receipt'))){$g13ActualHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([byte[]]$g13Readback[$g13Pair[0]])).ToLowerInvariant();if($g13ActualHash -ne $g13Parsed.terminal[$g13Pair[1]]){throw 'independent terminal manifest hash mismatch'}}
     foreach($g13Row in $g13Parsed.files){$g13Cached=[byte[]]$g13Cache[$g13Row.path];if($g13Cached.Length -ne $g13Row.bytes -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($g13Cached)).ToLowerInvariant() -ne $g13Row.sha256){throw 'independent manifest entry mismatch'}}
    }
   }
   $g13Observation=@{schema='G13-D5-terminal-observation';run=$Run;status=$g13Status;authorization=$g13Auth.commit;used=$g13FinalUsed;counts=$g13Counters;seconds_observed=$g13Clock.Elapsed.TotalSeconds;S_seconds_observed=$g13Clock.Elapsed.TotalSeconds-$g13PhaseStart;terminal_readback='PASS';independent_accounts_and_hashes='PASS';job_peak=[G13D4Job]::Peak;observation_write_read_exit_remainder_seconds=$null;S_hard_limit=120;observation_bytes_reserved=4096;boundary='last observation after terminal file reads, account validation, SHA256 checks; fixed observation own write/read follows'}
   $g13ObservationText=ConvertTo-Json $g13Observation -Depth 8 -Compress
   $g13ObservationRaw=$g13Utf8.GetBytes($g13ObservationText)
   if($g13ObservationRaw.Length -gt 4096){throw 'observation cap'}
   $g13ObservationRaw=$g13Utf8.GetBytes($g13ObservationText+(' '*(4096-$g13ObservationRaw.Length)))
   Check-G13;[IO.File]::WriteAllBytes((Join-Path $g13Out 'terminal_observation.json'),$g13ObservationRaw)
   Check-G13;$g13ObservationRead=[IO.File]::ReadAllBytes((Join-Path $g13Out 'terminal_observation.json'))
   if(-not [Linq.Enumerable]::SequenceEqual[byte]($g13ObservationRead,$g13ObservationRaw)){throw 'observation readback'}
   $g13Observation.detached_sha256=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($g13ObservationRead)).ToLowerInvariant()
   Write-Output (ConvertTo-Json -InputObject $g13Observation -Depth 8 -Compress)
  } catch {
   # Do not reopen a tail or silently declare a failed finalizer complete.
 Write-Output (ConvertTo-Json -InputObject @{run=$Run;status='SEAL_INCOMPLETE';signature=$_.Exception.Message;known_used=$g13Used;counters=$g13Counters;unknown_terminal_tail=$true} -Depth 6 -Compress)
   $g13Status='SEAL_INCOMPLETE'
  }
 }
 [G13D4Job]::Finish()
}
if($g13Status -notin @('PASS','SEALED_ONLY')){exit 1}
