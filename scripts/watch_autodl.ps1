# Watch an AutoDL experiment from Windows PowerShell over SSH.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9.-]+$')]
    [string]$SshHost,

    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 65535)]
    [int]$Port,

    [ValidatePattern('^[A-Za-z0-9_-]+$')]
    [string]$User = 'root',

    [ValidatePattern('^/[A-Za-z0-9_./-]+$')]
    [string]$ProjectDir = '/root/autodl-tmp/FL-Byzantine-Library',

    [ValidateSet('follow', 'status', 'gpu', 'summary', 'login')]
    [string]$Action = 'follow'
)

$target = '{0}@{1}' -f $User, $SshHost
$sshOptions = @('-p', [string]$Port, '-o', 'ServerAliveInterval=30',
                '-o', 'ServerAliveCountMax=3')
$runner = "$ProjectDir/scripts/autodl_experiment.sh"

switch ($Action) {
    'follow'  { $remoteCommand = "tail -n 80 -F $ProjectDir/outputs/d1_3b/run.log" }
    'status'  { $remoteCommand = "bash $runner status" }
    'gpu'     { $remoteCommand = 'nvidia-smi' }
    'summary' { $remoteCommand = "bash $runner summary-d1" }
    'login'   { $remoteCommand = $null }
}

if ($null -eq $remoteCommand) {
    & ssh @sshOptions $target
} else {
    & ssh @sshOptions $target $remoteCommand
}
exit $LASTEXITCODE
