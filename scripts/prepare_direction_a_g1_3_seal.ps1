# No new owner, local Budget, timeout or tail grant: reopen only through shared supervisor.
& (Join-Path $PSScriptRoot 'prepare_direction_a_g1_3_outer.ps1') -Mode seal
exit $LASTEXITCODE
