param([ValidateSet('V1','V2')][string]$Run='V1')
$ErrorActionPreference='Stop'
$bClock=[Diagnostics.Stopwatch]::StartNew()
$bRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$bAuth='182e5e60556a020c52effb2e7eccfa071b45b980'
$bUtf8=[Text.UTF8Encoding]::new($false,$true)
$bOut=Join-Path $bRoot "artifacts/direction_a/phaseG1_3_B_d6_v1/$Run"
$bUsed=@{read=0L;write=0L;scans=0L;ops=0L}
$bLimits=@{read=167772160L;write=8388608L;scans=6100000L;ops=100000000000L}
$bPhase=$Run;$bSClock=$null;$bProc=$null;$bPeak=0L;$bDone=$null;$bInheritance=$null
$bHashes=@{};$bRecords=[Collections.Generic.List[object]]::new()
$bSourcePaths=@('scripts/measure_direction_a_g1_3_blind.py','tests/test_direction_a_g1_3_blind.py','scripts/measure_direction_a_g1_3_blind_outer.ps1')
# This C# definition installs the owner Job before any restricted file read or
# child process. Descendants inherit it without a BREAKAWAY flag. Python waits
# for an owner token before reading its source. Limits remain active through S.
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Diagnostics;
using System.Threading;
public static class G13BJob {
 [StructLayout(LayoutKind.Sequential)] struct Basic { public long User,Job; public uint Flags; public UIntPtr MinWS,MaxWS; public uint Active; public UIntPtr Affinity; public uint Priority,Scheduling; }
 [StructLayout(LayoutKind.Sequential)] struct IO { public ulong A,B,C,D,E,F; }
 [StructLayout(LayoutKind.Sequential)] struct Extended { public Basic B; public IO IO; public UIntPtr Process,Job,PeakProcess,PeakJob; }
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr CreateJobObject(IntPtr a,string n);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr j,IntPtr p);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool SetInformationJobObject(IntPtr j,int c,ref Extended e,uint n);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool QueryInformationJobObject(IntPtr j,int c,IntPtr b,uint n,out uint used);
 [DllImport("kernel32.dll")] static extern bool TerminateJobObject(IntPtr j,uint code);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool IsProcessInJob(IntPtr p,IntPtr j,out bool value);
 static IntPtr job; static Timer timer; public static long Peak;
 public static void Start(int milliseconds) {
  job=CreateJobObject(IntPtr.Zero,null); if(job==IntPtr.Zero) throw new Exception("CreateJobObject");
  Extended e=new Extended(); e.B.Flags=0x200|0x2000; e.Job=(UIntPtr)2147483648UL;
  if(!SetInformationJobObject(job,9,ref e,(uint)Marshal.SizeOf(e))) throw new Exception("Set Job memory "+Marshal.GetLastWin32Error());
  if(!AssignProcessToJobObject(job,Process.GetCurrentProcess().Handle)) throw new Exception("Assign owner Job "+Marshal.GetLastWin32Error());
  timer=new Timer(_=>TerminateJobObject(job,124),null,Math.Max(1,milliseconds),Timeout.Infinite);
 }
 public static void Deadline(int seconds) { timer.Change(seconds*1000,Timeout.Infinite); }
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
[G13BJob]::Start([Math]::Max(1,[int][Math]::Floor((300-$bClock.Elapsed.TotalSeconds)*1000)))
function BCheck {
 [void][G13BJob]::Sample()
 if($bPhase -like 'S*') {if($bSClock.Elapsed.TotalSeconds -ge 100){throw 'S active boundary; terminal reserve'}}
 elseif($bClock.Elapsed.TotalSeconds -ge 280){throw 'V soft boundary preserve S'}
}
function BCharge([long]$Read=0,[long]$Write=0,[long]$Scans=0,[long]$Ops=0) {
 BCheck
 $d=@{read=$Read;write=$Write;scans=$Scans;ops=$Ops}
 foreach($k in $d.Keys){if($d[$k] -lt 0 -or $d[$k] -gt $bLimits[$k]-$bUsed[$k]){throw "owner quota before access $k"}}
 foreach($k in $d.Keys){$bUsed[$k]+=$d[$k]}
}
function BHash([byte[]]$Raw){return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($Raw)).ToLowerInvariant()}
function BRead([string]$Path,[long]$Max,[string]$Blob='') {
 $p=[IO.Path]::GetFullPath((Join-Path $bRoot $Path))
 if(-not $p.StartsWith($bRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'owner path escape'}
 $size=([IO.FileInfo]$p).Length
 if($size -lt 0 -or $size -gt $Max){throw 'owner frozen input size'}
 BCharge -Read $size -Scans 8 -Ops (64*$size)
 $raw=[IO.File]::ReadAllBytes($p)
 if($raw.Length -ne $size){throw 'owner size changed'}
 if($Blob){
  $norm=$bUtf8.GetBytes($bUtf8.GetString($raw).Replace("`r`n","`n").Replace("`r","`n"))
  $header=[Text.Encoding]::ASCII.GetBytes("blob $($norm.Length)"+[char]0)
  $gitRaw=[byte[]]::new($header.Length+$norm.Length)
  [Array]::Copy($header,0,$gitRaw,0,$header.Length);[Array]::Copy($norm,0,$gitRaw,$header.Length,$norm.Length)
  if([Convert]::ToHexString([Security.Cryptography.SHA1]::HashData($gitRaw)).ToLowerInvariant() -ne $Blob){throw 'owner frozen Git identity'}
 }
 if($bRecords.Count -gt 32){throw 'owner cache record cap'}
 $bRecords.Add(@{path=$Path;bytes=$size;sha256=(BHash $raw);git_object=$Blob})
 return ,$raw
}
function BWrite([string]$Name,$Value,[int]$Cap=262144) {
 BCharge -Scans 8 -Ops (8L*$Cap)
 $raw=$bUtf8.GetBytes((ConvertTo-Json -InputObject $Value -Depth 32 -Compress)+"`n")
 if($raw.Length -gt $Cap){throw 'owner output cap'}
 $path=Join-Path $bOut $Name
 if([IO.File]::Exists($path)){throw 'owner output overwrite'}
 BCharge -Write $raw.Length -Read $raw.Length
 [IO.File]::WriteAllBytes($path,$raw)
 $check=[IO.File]::ReadAllBytes($path)
 if((BHash $raw) -ne (BHash $check)){throw 'owner output readback'}
 $bHashes[$Name]=@{sha256=(BHash $raw);bytes=$raw.Length;readback='PASS'}
}
function BSealPhase {
 if($bPhase -like 'S*'){throw 'duplicate S lease'}
 $script:bPhase='S'+$Run.Substring(1)
 $script:bSClock=[Diagnostics.Stopwatch]::StartNew()
 $script:bLimits=@{read=16777216L;write=12582912L;scans=16384L;ops=100000000L}
 $script:bUsed=@{read=0L;write=0L;scans=0L;ops=0L}
 [G13BJob]::Deadline(120)
}
try {
 if(Test-Path -LiteralPath $bOut){throw 'new round directory must not exist'}
 [void][IO.Directory]::CreateDirectory($bOut)
 $authPaths=@('docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md','docs/workflow/ROLE_EXECUTOR.md','docs/workflow/ROLE_REVIEWER.md','docs/DIRECTION_A_G1_3_ADJUDICATION_v5.md','docs/workflow/TO_EXECUTOR.md')
 $authBlobs=@('e87d045133cf16ea140dfc2dd1ab57257e49bc6e','f5a5ee43cc69415026aee45e6393b576ea2a55a5','a5d218725e6cab38d72a48e3e1934e9292b9ca55','44a4eb7a64e3a33228732bd474ee530b7057fb51','18cf15ae249e8949cba5b46ddd9e94c172f6f18a')
 $bootstrap=0L
 for($i=0;$i -lt 5;$i++){ $raw=BRead $authPaths[$i] (524288-$bootstrap) $authBlobs[$i];$bootstrap+=$raw.Length }
 $d5='artifacts/direction_a/phaseG1_3_A_d5_v1/V1/'
 $names=@('plan.json','receipt.json','resource_ledger.json','bundle.json')
 $blobs=@('464b7e91d3d126079be1ed27eed23c6bc2c65070','1f7a7226721eb329d5158b88ffe543c08503175b','c1faaaa34782288db0d71b22642e2f479fdaf900','d6c974e3ff7eb8d72959a9e7f3e068ec8dd34b52')
 $prior=@{}
 for($i=0;$i -lt 4;$i++){
  $raw=BRead ($d5+$names[$i]) (524288-$bootstrap) $blobs[$i];$bootstrap+=$raw.Length
  BCharge -Scans 4096 -Ops (32*$raw.Length)
  $prior[$names[$i]]=ConvertFrom-Json -InputObject $bUtf8.GetString($raw) -AsHashtable
 }
 $l=$prior['resource_ledger.json'];$r=$prior['receipt.json']
 if($l.schema -ne 'G13-D5-ledger' -or $r.counters.engineering -ne 6 -or $r.counters.implementation_revisions -ne 3 -or $r.counters.syntax -ne 4 -or $r.counters.cpu -ne 4){throw 'D5 counters/schema mismatch'}
 # Never copy prior usage or nulls into fresh accounts. Keep one immutable,
 # identified historical block, and only explicit integers in new B accounts.
 $bInheritance=@{times_carried=1;old_limit=@{seconds=4460;read=89128960;write=46137344;scans=354584};old_2290_isolated=$true;old_FAIL_null='preserved';old_accounts_installed=$false;D5_used_risk=@{seconds=1020;read=16777216;write=8388608;scans=80384};D5_unused_exclusive=@{seconds=1150;read=25690112;write=12582912;scans=96780};B_transfer=0;D5_used_known=$l.used;D5_unknowns=$l.unknowns;D5_carry=$l.carry_once;identities=@($bRecords)}
 $projection=@{schema='G13-B-input-v1';authorization_commit=$bAuth;bindings=$prior['bundle.json'].bindings;B_requirements=$prior['bundle.json'].B_requirements;error_objects=$prior['bundle.json'].error_objects;inheritance=$bInheritance}
 BWrite 'blind_input.json' $projection 262144
 # The whole A bundle is released in the owner and is never sent to Python.
 $prior=$null;$l=$null;$r=$null;$projection=$null;$raw=$null
 $countsBefore=@(6,3,4,4);$predecessor=$false
 if($Run -eq 'V2'){
  $priorDir='artifacts/direction_a/phaseG1_3_B_d6_v1/V1/'
  $pr=ConvertFrom-Json -InputObject $bUtf8.GetString((BRead ($priorDir+'receipt.json') 16384)) -AsHashtable
  $mf=ConvertFrom-Json -InputObject $bUtf8.GetString((BRead ($priorDir+'artifact_hashes.json') 32768)) -AsHashtable
  foreach($key in @('resource_ledger.json','state_checkpoint.json','failure.json','synthetic_acceptance.json')){
   $rr=BRead ($priorDir+$key) 262144
   if((BHash $rr) -ne $mf.files[$key].sha256){throw 'B predecessor hash mismatch'}
  }
  if($pr.authorization_commit -ne $bAuth -or $pr.scientific_results -ne 0 -or $pr.status -eq 'PASS'){throw 'B predecessor does not permit repair'}
  $countsBefore=@($pr.counts);$predecessor=$true
 }
 $sourceRaw=BRead $bSourcePaths[0] 262144
 $sourceSize=$sourceRaw.Length;$sourceHash=BHash $sourceRaw
 # Charge the child bootstrap file read before releasing its stdin handshake.
 BCharge -Read $sourceSize -Scans 2 -Ops (64*$sourceSize)
 $p=[Diagnostics.ProcessStartInfo]::new();$p.FileName='E:\anaconda3\python.exe';$p.WorkingDirectory=$bRoot
 foreach($arg in @('-B','-I','-S','-c',"import sys; p=sys.stdin.readline(16385).strip(); globals()['__file__']=p; exec(compile(open(p,'rb').read(),p,'exec'),globals())")){$p.ArgumentList.Add($arg)}
 $p.UseShellExecute=$false;$p.CreateNoWindow=$true;$p.RedirectStandardInput=$true;$p.RedirectStandardOutput=$true;$p.RedirectStandardError=$true
 $p.StandardInputEncoding=$bUtf8;$p.StandardOutputEncoding=$bUtf8;$p.StandardErrorEncoding=$bUtf8
 $p.Environment['G13_B_AUTH']=$bAuth;$p.Environment['G13_B_JOB_VERIFIED']='1';$p.Environment['G13_B_RUN']=$Run
 # Fixed 8 KiB covers both endpoints of bootstrap/seal/done IPC including a
 # bounded stderr refusal. No vectors/whole bundle cross this channel.
 BCharge -Read 8192 -Write 8192 -Scans 32 -Ops 100000
 $boot=@{debits=$bUsed;projection_path="artifacts/direction_a/phaseG1_3_B_d6_v1/$Run/blind_input.json";projection_sha256=$bHashes['blind_input.json'].sha256;counts_before=$countsBefore;predecessor_verified=$predecessor;source_sha256=$sourceHash;active_elapsed=$bClock.Elapsed.TotalSeconds;inheritance=$bInheritance}
 $p.Environment['G13_B_BOOT']=ConvertTo-Json -InputObject $boot -Depth 16 -Compress
 if($bUtf8.GetByteCount($p.Environment['G13_B_BOOT']) -gt 16384){throw 'bootstrap env frame cap'}
 if(-not [G13BJob]::Contains($PID)){throw 'owner not in inherited Job before child'}
 $bProc=[Diagnostics.Process]::new();$bProc.StartInfo=$p;[void]$bProc.Start()
 if(-not [G13BJob]::Contains($bProc.Id)){$bProc.Kill($true);throw 'child absent from inherited Job'}
 $bPid=$bProc.Id;$bErr=$bProc.StandardError.ReadToEndAsync()
 $bProc.StandardInput.WriteLine((Join-Path $bRoot $bSourcePaths[0]));$bProc.StandardInput.Flush()
 $line=$bProc.StandardOutput.ReadLineAsync();$frames=0
 while($true){
  BCheck
  if(-not $line.IsCompleted){Start-Sleep -Milliseconds 10;continue}
  $value=$line.GetAwaiter().GetResult()
  if($null -eq $value){break}
  if($bUtf8.GetByteCount($value) -gt 16384 -or ++$frames -gt 2){throw 'IPC frame count/size'}
  $message=ConvertFrom-Json -InputObject $value -AsHashtable
  if($message.action -eq 'seal'){
   if($message.auth -ne $bAuth -or $message.run -ne $Run){throw 'S lease authorization'}
   BSealPhase
   $bProc.StandardInput.WriteLine('S_GRANTED');$bProc.StandardInput.Flush()
  }elseif($message.action -eq 'done'){
   $bDone=$message
   foreach($k in @($bUsed.Keys)){
    $v=$message.S[$k]
    if(($v -isnot [int] -and $v -isnot [long]) -or $v -lt 0 -or $v -gt $bLimits[$k]){throw 'child S settlement type/range'}
    $bUsed[$k]=[long]$v
   }
  }else{throw 'unregistered IPC action'}
  $line=$bProc.StandardOutput.ReadLineAsync()
 }
 $bProc.WaitForExit();$errorText=$bErr.GetAwaiter().GetResult()
 if($bUtf8.GetByteCount($errorText) -gt 4096){throw 'stderr frame cap'}
 if($null -eq $bDone){throw "worker exited without closure: $errorText"}
 BCharge -Read 32768 -Write 16384 -Scans 16 -Ops 100000
 $manifestRaw=[IO.File]::ReadAllBytes((Join-Path $bOut 'artifact_hashes.json'))
 if($manifestRaw.Length -gt 32768){throw 'manifest cap'}
 $terminal=@{schema='G13-B-owner-terminal-v1';authorization_commit=$bAuth;run=$Run;pid=$bPid;inherited_job=$true;verified_before_bootstrap=$true;owner_membership_verified_before_start=$true;job_limit=2147483648;observed_job_peak=[G13BJob]::Peak;full_peak=$null;clock_seconds_observed=$bClock.Elapsed.TotalSeconds;exit_code=$bProc.ExitCode;worker=$bDone;manifest_sha256=(BHash $manifestRaw);projection=$bHashes['blind_input.json'];outer_explicit_bootstrap=$bRecords;IPC_both_endpoint_upper=8192;owner_terminal_reservation=@{read=32768;write=16384;scans=16;ops=100000};exit_tail_after_this_observation=$null;implicit_io=$null}
 BWrite 'terminal_observation.json' $terminal 16384
 Write-Output (ConvertTo-Json -InputObject @{status=$bDone.status;counts=$bDone.counts;science=$bDone.science;seconds=$bClock.Elapsed.TotalSeconds;peak=[G13BJob]::Peak} -Compress)
 $bExit=if($bDone.status -eq 'PASS'){0}else{1}
} catch {
 $bProblem=$_.Exception.Message
 if($null -ne $bProc -and -not $bProc.HasExited){$bProc.Kill($true);$bProc.WaitForExit()}
 if($bPhase -notlike 'S*'){BSealPhase}
 # A bootstrap failure has no scientific result. Partial worker outputs, if any,
 # are preserved rather than overwritten; this same-round emergency seal is not
 # an independent I/S3 launch and cannot manufacture a missing worker result.
 if(-not (Test-Path -LiteralPath $bOut)){[void][IO.Directory]::CreateDirectory($bOut)}
 foreach($name in @('plan.json','qualification.json','synthetic_acceptance.json','blind_results.json')){
  if(-not [IO.File]::Exists((Join-Path $bOut $name))){BWrite $name @{status='NOT_RUN';reason=$bProblem;authorization_commit=$bAuth} 16384}
 }
 if(-not [IO.File]::Exists((Join-Path $bOut 'failure.json'))){BWrite 'failure.json' @{status='FAIL';type='OwnerBootstrap';location='B00/owner';cause=$bProblem;signature="OwnerBootstrap|B00|$bProblem"} 16384}
 if(-not [IO.File]::Exists((Join-Path $bOut 'state_checkpoint.json'))){BWrite 'state_checkpoint.json' @{status='NOT_COMPLETED';completed=@();partial=@('B00');not_started=@('B01','B02','B03','B04','B05');scientific_results=0;real_entries=0;counts=@(7,3,4,4)} 16384}
 if(-not [IO.File]::Exists((Join-Path $bOut 'resource_ledger.json'))){BWrite 'resource_ledger.json' @{schema='G13-B-owner-partial-ledger';accounts=$bUsed;old_history=$bInheritance;whole_V=$null;whole_S=$null;counts=@(7,3,4,4);implicit_io=$null;full_peak=$null} 262144}
 if(-not [IO.File]::Exists((Join-Path $bOut 'receipt.json'))){BWrite 'receipt.json' @{status='NOT_COMPLETED_ENGINEERING_BLOCKED';authorization_commit=$bAuth;scientific_results=0;real_entries=0;counts=@(7,3,4,4);failure=$bProblem;whole_account_unknown=$true} 16384}
 if(-not [IO.File]::Exists((Join-Path $bOut 'artifact_hashes.json'))){BWrite 'artifact_hashes.json' @{files=$bHashes;status='PARTIAL';authorization_commit=$bAuth} 32768}
 Write-Output (ConvertTo-Json -InputObject @{status='FAIL';owner_error=$bProblem;seconds=$bClock.Elapsed.TotalSeconds} -Compress)
 $bExit=1
} finally {[G13BJob]::Finish()}
exit $bExit
