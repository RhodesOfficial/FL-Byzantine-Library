param([ValidateSet('V1','V2','S3')][string]$Run='V1')
$ErrorActionPreference='Stop'
# A00: immutable authorization, time and all six accounts exist before data reads.
$g13Clock=[Diagnostics.Stopwatch]::StartNew()
$g13Root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$g13Base='artifacts/direction_a/phaseG1_3_A_d4_v1'
$g13Rel="$g13Base/$Run"
$g13Out=Join-Path $g13Root $g13Rel
$g13Utf8=[Text.UTF8Encoding]::new($false,$true)
$g13Auth=@{commit='aeef05f773f4bc6884ac243272bfff4189eb4703';base='b60af37456c70ea12028f996489380ba827d1323';decision='docs/DIRECTION_A_G1_3_ADJUDICATION_v3.md';contract='docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md section seven D4';task='docs/workflow/TO_EXECUTOR.md';D4='author approved option A 2026-10-19';real_entries=0}
$g13Limits=@{}
foreach($g13Name in @('V1','V2')){$g13Limits[$g13Name]=@{seconds=900;read=8388608L;write=4194304L;scans=64000L}}
foreach($g13Name in @('S1','S2','S3')){$g13Limits[$g13Name]=@{seconds=120;read=8388608L;write=4194304L;scans=16384L}}
$g13Limits.I=@{seconds=10;read=524288L;write=0L;scans=12L}
$g13Used=@{};foreach($g13Name in $g13Limits.Keys){$g13Used[$g13Name]=@{read=0L;write=0L;scans=0L;seconds=0.0}}
$g13Phase=if($Run -eq 'S3'){'I'}else{$Run}
$g13PhaseStart=0.0
$g13Cache=@{}
$g13Actions=[Collections.Generic.List[object]]::new()
$g13Failures=[Collections.Generic.List[object]]::new()
$g13Counters=@{engineering=3;implementation_revisions=1;syntax=1;cpu=1}
$g13Syntax='NOT_RUN';$g13CPU='NOT_RUN';$g13Status='NOT_COMPLETED';$g13Lease=$null;$g13LeaseReport=$null
$g13Probe=$null;$g13Inherited=@{};$g13Peak=0L;$g13Frames=0;$g13PipeBytes=0L
$g13Witness=@{};$g13Complete=@();$g13Partial=@();$g13NotStarted=@('A02','A03','A04')
$g13Token=[Guid]::NewGuid().ToString('N')
$g13Sources=@('direction_a/g1_3_preparation.py','scripts/prepare_direction_a_g1_3.py','tests/test_direction_a_g1_3_preparation.py','scripts/prepare_direction_a_g1_3_outer.ps1','scripts/prepare_direction_a_g1_3_seal.ps1')
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
 public static void Start(int seconds) {
  job=CreateJobObject(IntPtr.Zero,null); if(job==IntPtr.Zero) throw new Exception("CreateJobObject");
  Extended e=new Extended(); e.B.Flags=0x200|0x2000; e.Job=(UIntPtr)2147483648UL;
  if(!SetInformationJobObject(job,9,ref e,(uint)Marshal.SizeOf(e))) throw new Exception("Set Job memory "+Marshal.GetLastWin32Error());
  if(!AssignProcessToJobObject(job,Process.GetCurrentProcess().Handle)) throw new Exception("Assign owner Job "+Marshal.GetLastWin32Error());
  Deadline(seconds);
  timer=new Timer(_=> { if(Environment.TickCount64>Interlocked.Read(ref deadline)) TerminateJobObject(job,124); },null,100,100);
 }
 public static void Deadline(int seconds) { Interlocked.Exchange(ref deadline,Environment.TickCount64+seconds*1000L); }
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
[G13D4Job]::Start($(if($Run -eq 'S3'){130}else{1020}))

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
  if($g13D -lt 0 -or $g13Used[$g13Phase][$g13K]+$g13D -gt $g13Limits[$g13Phase][$g13K]){throw "quota before access $g13Phase/$g13K"}
 }
}
function Charge-G13([string]$Label,[long]$Read=0,[long]$Write=0,[long]$Scans=0) {
 Capacity-G13 -Read $Read -Write $Write -Scans $Scans
 $g13Used[$g13Phase].read+=$Read;$g13Used[$g13Phase].write+=$Write;$g13Used[$g13Phase].scans+=$Scans
 if($g13Actions.Count -ge 480){throw 'operation record capacity'}
 $g13Actions.Add(@{action=$Label;phase=$g13Phase;read=$Read;write=$Write;scans=$Scans})
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
 return @{phase=$g13Phase;used=@{read=$g13Used[$g13Phase].read;write=$g13Used[$g13Phase].write;scans=$g13Used[$g13Phase].scans};job='inherited non-breakaway 2GiB';counts=$g13Counters}
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
    syntax_start {$script:g13Syntax='IN_PROGRESS';$g13Counters.syntax++}
    syntax_pass {$script:g13Syntax='PASS'}
    cpu_start {$script:g13CPU='IN_PROGRESS';$g13Counters.cpu++}
    identities {$g13Value=$g13Identities}
    lease {
     if($null -ne $g13Lease){throw 'kernel lease cannot renew'}
     Capacity-G13 -Read 1048576 -Write 2097152 -Scans 40000
     $script:g13Lease=@{limits=@{read=1048576L;write=2097152L;scans=40000L};seconds=[Math]::Max(1,875-($g13Clock.Elapsed.TotalSeconds-$g13PhaseStart))}
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
     if($null -eq $g13Lease -or $null -ne $g13LeaseReport){throw 'invalid lease settlement'}
     foreach($g13K in @('read','write','scans')){if($g13Req.report.used[$g13K] -gt $g13Lease.limits[$g13K]){throw 'lease exceeded'}}
     Charge-G13 'kernel settled explicit read/write/traversal debits' -Read $g13Req.report.used.read -Write $g13Req.report.used.write -Scans $g13Req.report.used.scans
     $script:g13LeaseReport=$g13Req.report;$script:g13Status=$g13Req.status
     $script:g13Complete=$g13Req.completed;$script:g13Partial=$g13Req.partial;$script:g13NotStarted=$g13Req.not_started
     foreach($g13Failure in $g13Req.failures){$g13Failures.Add($g13Failure)}
     $script:g13CPU=if($g13Status -eq 'PASS'){'PASS'}else{'FAIL'}
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
 $g13Names=@('plan.json','resource_ledger.json','receipt.json','artifact_hashes.json')
 $g13OldObjects=@('72d647acd2e532a721c4e26ba09d1dd06934b242','5eb7833e561afdff0b06ea1f32e6fba25db2a20c','92e743d044ca6fcbc7ff2a888eb5399ff2ecf6e1','817c47cb833030cf4229399503107fe10409e2c1')
 $g13PriorDir=if($Run -eq 'V1'){'artifacts/direction_a/phaseG1_3_A_guard_v1'}elseif($Run -eq 'V2'){"$g13Base/V1"}else{"$g13Base/V2"}
 $g13Prior=@{};$g13BootstrapBytes=0L
 for($g13Index=0;$g13Index -lt 4;$g13Index++){
  $g13Path="$g13PriorDir/$($g13Names[$g13Index])"
  $g13Raw=Raw-G13 $g13Path 262144
  $g13BootstrapBytes+=$g13Raw.Length
  if($g13BootstrapBytes -gt 524288){throw 'A00 bootstrap bytes'}
  if($Run -eq 'V1'){GitIdentity-G13 $g13Raw $g13OldObjects[$g13Index]}else{[void](Hash-G13 $g13Raw $g13Path)}
  Charge-G13 'A00 predecessor parse/account traversal' -Scans 1
  $g13Prior[$g13Names[$g13Index]]=ConvertFrom-Json -InputObject $g13Utf8.GetString($g13Raw) -AsHashtable
 }
 if($Run -eq 'V1'){
  if($g13Prior['resource_ledger.json'].new_work.counters.engineering -ne 3 -or $g13Prior['receipt.json'].status -ne 'PASS'){throw 'predecessor ledger/receipt identity'}
  $g13Carry=@{commit='c35ae78';complete_predecessor=$g13Prior;old_block_limit=@{seconds=120;read=4194304;write=4194304;scans=256};old_risk=@{seconds=80;read=3145728;write=3145728;scans=192};old_guard_recorded=@{seconds_upper=2.6099713;read=46589;write=15184;scans=27};isolated_unused=@{seconds=37.3900287;read=1001987;write=1033392;scans=37};time_discrepancy=0.0007893;old_schema_scans=$null;old_FAIL='preserved';times_carried=1}
 } else {
  $g13Prev=$g13Prior['resource_ledger.json']
  if(-not $g13Prior['receipt.json'].terminal_readback_required -or $g13Prev.status -eq 'PASS' -or $g13Prev.carry_once.times_carried -ne 1){throw 'closed/foreign/incomplete predecessor'}
  $g13Carry=$g13Prev.carry_once
  foreach($g13K in $g13Prev.counters.Keys){$g13Counters[$g13K]=[int]$g13Prev.counters[$g13K]}
  foreach($g13Name in $g13Prev.accounts.Keys){if($g13Name -ne $g13Phase){$g13Used[$g13Name]=$g13Prev.accounts[$g13Name]}}
  foreach($g13Failure in $g13Prev.failures){$g13Failures.Add($g13Failure)}
  if($Run -eq 'V2'){$g13Counters.implementation_revisions++}
 }
 $g13Counters.engineering++
 if($g13Counters.engineering -gt 6 -or $g13Counters.implementation_revisions -gt 3){throw 'cumulative attempt/revision cap'}
 $g13Plan=@{schema='G13-D4-plan-v1';authorization=$g13Auth;run=$Run;limits=$g13Limits;predecessor=$g13PriorDir;counts_before=@(3,1,1,1);two_rounds_and_independent_seal_frozen=@{seconds=2170;read=42467328;write=20971520;scans=177164};real_entries=0;unknowns=@{physical_io=$null;implicit_interpreter_io=$null;platform_completion_seconds=$null;platform_peak_proof=$null};lease='A02-A05 nonrenewable; unused reservation is not used';bootstrap_bytes=$g13BootstrapBytes}
 Write-G13 'plan.json' $g13Plan 65536
 Write-G13 'authorization.json' $g13Auth 16384
 Write-G13 'carry.json' @{predecessor=$g13PriorDir;times_carried=1;old_block='isolated';full_record='resource_ledger.json/carry_once/complete_predecessor'} 65536
 $g13Ready=$true
 if($Run -ne 'S3'){
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
  $g13Witness=@{authorization_refusal_zero_access=$g13Access;byte_cap_refusal_zero_access=$g13Access;actual_rejections=$g13Rejections;status='PASS';dispatch='same Admit-G13 and Pipe-G13 as actual child requests';small_byte_seal='see terminal readback'}
  Child-G13 'validate'
  Child-G13 'probe'
  if($g13Probe.status -ne 'PASS'){throw 'second subprocess inheritance witness missing'}
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
    $g13Bundle=@{schema='G13-D4-v1';status='NOT_RUN';inputs=@();bindings=@();assertions=@();B_requirements=@();not_started=@('A02','A03','A04');failures=@()}
    Write-G13 'bundle.json' $g13Bundle
    $g13BundleRaw=Raw-G13 "$g13Rel/bundle.json"
   }
   Write-G13 'failure.json' @{failures=@($g13Failures.ToArray());new_scientific_results=0} 16384
   Write-G13 'state_checkpoint.json' @{schema='G13-D4-checkpoint';run=$Run;status=$g13Status;counters=$g13Counters;complete=$g13Complete;partial=$g13Partial;not_started=$g13NotStarted;accounts=$g13Used;never_renew_tail=$true} 131072
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
   $g13FinalUsed=@{};foreach($g13K in @('read','write','scans')){$g13FinalUsed[$g13K]='0'*20}
   $g13Ledger=@{schema='G13-D4-ledger';run=$Run;status=$g13Status;authorization=$g13Auth;carry_once=$g13Carry;accounts=$g13Used;limits=$g13Limits;counters=$g13Counters;actions=$g13Actions;kernel=$g13LeaseReport;kernel_reserved=$g13Lease;failures=$g13Failures;used=$g13FinalUsed;old_history_FAIL_null='preserved';unknowns=@{physical_io=$null;implicit_interpreter_io=$null;startup_total_io=$null;startup_whole_wall=$null;historical_peak=$null;external_kill_tail=$null};process_tree=@{job_memory_limit=2147483648L;peak_combined_working_set=[G13D4Job]::Peak;CPU_proxy_limit=268435456;CUDA=0};cost_quality='kernel declared scan/operation envelopes are upper debits; exact primitive count not proved';terminal=@{fixed_width=20;readback_required=$true;seconds_used_before_terminal=0.0;tail_seconds_reserved=20}}
   $g13Receipt=@{schema='G13-D4-receipt';run=$Run;status=$g13Status;counters=$g13Counters;used=$g13FinalUsed;syntax=$g13Syntax;cpu=$g13CPU;probe=$g13Probe;changed_interfaces=$g13Witness;terminal_readback_required=$true;closure='success exit after byte, semantic, hash checks';unsettled_kernel=($null -ne $g13Lease -and $null -eq $g13LeaseReport);ipc_frames=$g13Frames;ipc_both_endpoint_bytes=$g13PipeBytes}
   $g13Ledger.terminal.seconds_used_before_terminal=$g13Clock.Elapsed.TotalSeconds-$g13PhaseStart
   $g13Used[$g13Phase].seconds=$g13Ledger.terminal.seconds_used_before_terminal
   # Three terminal graphs are measured BEFORE the fixed, two serializations.
   Capacity-G13 -Scans 8192
   $g13Nodes=(Containers-G13 $g13Ledger)+(Containers-G13 $g13Receipt)+(Containers-G13 $g13Manifest)
   if($g13Nodes+(Containers-G13 $g13Bundle) -gt 2048){throw 'whole-package containers >2048'}
   Charge-G13 'terminal two serializations/readback/copy graphs' -Scans (6*$g13Nodes)
   $g13TerminalRow=@{action='terminal file writes/readbacks + ledger/receipt hash';phase=$g13Phase;read=('0'*20);write=('0'*20);scans=5}
   $g13Actions.Add($g13TerminalRow)
   foreach($g13K in @('read','write','scans')){
    $g13Total=0L;foreach($g13Name in $g13Used.Keys){$g13Total+=[long]$g13Used[$g13Name][$g13K]}
    $g13FinalUsed[$g13K]=$g13Total.ToString('D20')
   }
   # account values also fixed-width, so reserving the final writes cannot alter lengths.
   $g13AccountSnapshot=@{};foreach($g13Name in $g13Used.Keys){$g13AccountSnapshot[$g13Name]=@{read=([long]$g13Used[$g13Name].read).ToString('D20');write=([long]$g13Used[$g13Name].write).ToString('D20');scans=([long]$g13Used[$g13Name].scans).ToString('D20');seconds=$g13Used[$g13Name].seconds}}
   $g13Ledger.accounts=$g13AccountSnapshot
   $g13LedgerRaw=$g13Utf8.GetBytes((ConvertTo-Json -InputObject $g13Ledger -Depth 20 -Compress)+"`n")
   $g13ReceiptRaw=$g13Utf8.GetBytes((ConvertTo-Json -InputObject $g13Receipt -Depth 20 -Compress)+"`n")
   $g13ManifestRaw=$g13Utf8.GetBytes((ConvertTo-Json -InputObject $g13Manifest -Depth 20 -Compress)+"`n")
   $g13Total=$g13LedgerRaw.Length+$g13ReceiptRaw.Length+$g13ManifestRaw.Length
   Capacity-G13 -Read $g13Total -Write $g13Total -Scans 5
   $g13Used[$g13Phase].read+=$g13Total;$g13Used[$g13Phase].write+=$g13Total;$g13Used[$g13Phase].scans+=5
   $g13TerminalRow.read=$g13Total.ToString('D20');$g13TerminalRow.write=$g13Total.ToString('D20')
   foreach($g13K in @('read','write','scans')){
    $g13AccountSnapshot[$g13Phase][$g13K]=([long]$g13Used[$g13Phase][$g13K]).ToString('D20')
    $g13Sum=0L;foreach($g13Name in $g13Used.Keys){$g13Sum+=[long]$g13Used[$g13Name][$g13K]}
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
   for($g13Index=0;$g13Index -lt 3;$g13Index++){
    Check-G13;[IO.File]::WriteAllBytes((Join-Path $g13Out $g13FinalNames[$g13Index]),$g13FinalRaw[$g13Index])
   }
   for($g13Index=0;$g13Index -lt 3;$g13Index++){
    Check-G13
    $g13Read=[IO.File]::ReadAllBytes((Join-Path $g13Out $g13FinalNames[$g13Index]))
    if(-not [Linq.Enumerable]::SequenceEqual[byte]($g13Read,$g13FinalRaw[$g13Index])){throw 'terminal independent byte mismatch'}
    $g13Parsed=ConvertFrom-Json -InputObject $g13Utf8.GetString($g13Read) -AsHashtable
    if($g13Index -lt 2){foreach($g13K in @('read','write','scans')){if($g13Parsed.used[$g13K] -ne $g13FinalUsed[$g13K]){throw 'ledger/receipt total mismatch'}}}
   }
   Write-Output (ConvertTo-Json -InputObject @{run=$Run;status=$g13Status;used=$g13FinalUsed;counts=$g13Counters;seconds_observed=$g13Clock.Elapsed.TotalSeconds;terminal_readback='PASS';job_peak=[G13D4Job]::Peak} -Compress)
  } catch {
   # Do not reopen a tail or silently declare a failed finalizer complete.
   Write-Output (ConvertTo-Json -InputObject @{run=$Run;status='SEAL_INCOMPLETE';signature=$_.Exception.Message;known_used=$g13Used;counters=$g13Counters;unknown_terminal_tail=$true} -Depth 6 -Compress)
   $g13Status='SEAL_INCOMPLETE'
  }
 }
 [G13D4Job]::Finish()
}
if($g13Status -notin @('PASS','SEALED_ONLY')){exit 1}
