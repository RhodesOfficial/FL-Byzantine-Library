# The single preauthorized I/S3 account; no syntax, CPU, or numerical recomputation.
# Only invoke after V2 has started and a closure gap is recorded; a complete S2
# or a hard limit/protection failure never authorizes this entry.
& (Join-Path $PSScriptRoot 'prepare_direction_a_g1_3_outer.ps1') -Run S3
exit $LASTEXITCODE
