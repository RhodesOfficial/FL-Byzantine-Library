# The single preauthorized I/S3 account; no syntax, CPU, or numerical recomputation.
& (Join-Path $PSScriptRoot 'prepare_direction_a_g1_3_outer.ps1') -Run S3
exit $LASTEXITCODE
