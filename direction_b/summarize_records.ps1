# Read-only derivation from sealed R01 records. Does not invoke the vector runner.
$ErrorActionPreference = "Stop"
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskOut = Join-Path $taskRoot "artifacts\direction_b\r01_v1"
function Read-Record([string]$relative) {
    Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $taskOut $relative) | ConvertFrom-Json -AsHashtable
}
$fields = @("bytes", "frames", "up_bytes", "down_bytes", "payload_bytes", "residual_metadata_bytes")
function Empty-Wire { return @{} }
function Add-Wire($target, $source, [int]$sign = 1) {
    foreach ($purpose in $source.Keys) {
        if (-not $target.ContainsKey($purpose)) {
            $target[$purpose] = @{}
            foreach ($field in $fields) { $target[$purpose][$field] = 0L }
        }
        foreach ($field in $fields) { $target[$purpose][$field] += $sign * $source[$purpose][$field] }
    }
}
function Wire-Total($wire, [string]$field = "bytes") {
    $total = 0L
    foreach ($row in $wire.Values) { $total += $row[$field] }
    return $total
}
$summary = Read-Record "summary.json"
$controls = Read-Record "controls.json"
$recovery = Read-Record "recovery\cross_process_result.json"
$parts = [ordered]@{}
$parts["matrix_including_reused_representative_once"] = $summary.matrix_wire
$controlWire = Empty-Wire
Add-Wire $controlWire $controls.top1_tracking.wire
foreach ($case in $controls.cases.Values) { Add-Wire $controlWire $case.wire }
$parts["tracking_and_fixed_controls"] = $controlWire
# Six snapshots share one executed reference prefix; never add each inherited total.
$parts["recovery_uninterrupted_reference_once"] = $controls.serialization_boundaries[5].wire_before
$boundaryIncrements = Empty-Wire
foreach ($boundary in $controls.serialization_boundaries) {
    Add-Wire $boundaryIncrements $boundary.wire_after
    Add-Wire $boundaryIncrements $boundary.wire_before -1
}
$parts["six_restorations_own_increments_only"] = $boundaryIncrements
$crossIncrement = Empty-Wire
Add-Wire $crossIncrement $recovery.wire_after
Add-Wire $crossIncrement $recovery.wire_before -1
$parts["cross_process_continuation_own_increment_only"] = $crossIncrement
$totalWire = Empty-Wire
foreach ($part in $parts.Values) { Add-Wire $totalWire $part }
foreach ($row in $totalWire.Values) {
    if ($row.bytes -ne $row.up_bytes + $row.down_bytes) { throw "Wire conservation failed." }
    foreach ($value in $row.Values) { if ($value -lt 0) { throw "Negative cost increment." } }
}
$invocations = @("representative", "resume", "formal") | ForEach-Object { Read-Record "invocation_$_.json" }
$processes = @("representative", "resume", "formal") | ForEach-Object { Read-Record "process_$_.json" }
$elapsed = ($invocations | ForEach-Object { $_.external_seconds } | Measure-Object -Sum).Sum
$peak = ($processes | ForEach-Object { $_.peak_working_set_bytes } | Measure-Object -Maximum).Maximum
$partTotals = [ordered]@{}
foreach ($name in $parts.Keys) { $partTotals[$name] = Wire-Total $parts[$name] }
$matrixBytes = Wire-Total $summary.matrix_wire
$metadataSaving = Wire-Total $summary.matrix_wire "residual_metadata_bytes"
$ledger = [ordered]@{
    input_implementation_commit = "59c55f8"
    remaining_plan_commit = "1080b39"
    phase_external_seconds = @($invocations | ForEach-Object { [ordered]@{phase=$_.phase; seconds=$_.external_seconds} })
    cumulative_external_seconds = $elapsed
    maximum_peak_working_set_bytes = $peak
    repairs = 0
    unique_scientific_cells = 24
    unique_scientific_buffers = 480
    unique_formal_returns = 1440
    matrix_application_bytes = $matrixBytes
    matrix_C_if_only_unused_residual_metadata_removed_bytes = $matrixBytes - $metadataSaving
    matrix_residual_metadata_bytes = $metadataSaving
    all_executed_protocol_application_bytes = Wire-Total $totalWire
    disjoint_execution_part_bytes = $partTotals
    all_wire_by_disjoint_purpose = $totalWire
    execution_part_wire = $parts
    limitations = @(
        "Encoded application frames, not a real network trace; no TCP/IP cost.",
        "Natural-C estimate removes only residual_norm; not a fully optimized baseline deployment.",
        "Each matrix buffer independently pays warm initialization; the matrix is not one temporal run.",
        "U is an evaluation diagnostic with source values; not an uncharged deployable algorithm.",
        "Manual work and read-only PowerShell postprocessing are outside the Python wall-clock scope.",
        "Artifact storage is measured separately in the delivery document after this ledger is saved."
    )
}
$target = Join-Path $taskOut "ledger.json"
if (Test-Path -LiteralPath $target) { throw "Ledger exists; do not overwrite sealed evidence." }
$ledger | ConvertTo-Json -Depth 15 | Set-Content -Encoding UTF8 -LiteralPath $target
[PSCustomObject]$ledger | Select-Object cumulative_external_seconds,maximum_peak_working_set_bytes,matrix_application_bytes,
    matrix_C_if_only_unused_residual_metadata_removed_bytes,all_executed_protocol_application_bytes,
    disjoint_execution_part_bytes | ConvertTo-Json -Depth 5
$files = Get-ChildItem -LiteralPath $taskOut -Recurse -File
$bytes = ($files | Measure-Object Length -Sum).Sum
if ($bytes -gt 4*1024*1024 -or $elapsed -gt 120 -or $peak -gt 256*1024*1024) { throw "Resource cap exceeded." }
Write-Output "artifact_files=$($files.Count) artifact_bytes=$bytes"
foreach ($name in ($summary.cells.Keys | Sort-Object)) {
    $s = $summary.cells[$name]
    Write-Output ("|{0}|{1:F8}|{2:F8}|{3:F8}|{4:F8}|{5:F8}|{6:F8}|{7:F8}|" -f
        $name,$s.algorithms.C.mean,$s.algorithms.R.mean,$s.algorithms.ABS.mean,
        $s.algorithms.CACHE.mean,$s.algorithms.MSG.mean,$s.algorithms.ID.mean,$s.algorithms.U.mean)
}
