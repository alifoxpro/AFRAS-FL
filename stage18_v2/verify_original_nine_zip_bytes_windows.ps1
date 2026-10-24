# AFRAS-FL V2 Chat13: independently verify original nine N-BaIoT ZIP byte identity.
# Requires Windows PowerShell 5.1+ or PowerShell 7+. No Python, packages or network.
# This is DATA ADMISSION EVIDENCE ONLY and does NOT create human research approval.
# powershell -NoProfile -File .\stage18_v2\verify_original_nine_zip_bytes_windows.ps1 -SourceRoot "D:\AFRAS\nine_original_zip" -Manifest ".\stage18_v2\ORIGINAL_NINE_LOCAL_ZIP_HASH_MANIFEST_2026-10-24.json" -Receipt "D:\AFRAS\evidence\original_zip_sha256_receipt.json"
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$SourceRoot,
    [Parameter(Mandatory=$true)][string]$Manifest,
    [Parameter(Mandatory=$true)][string]$Receipt
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Canonical = @(
    "Ennio_Doorbell",
    "Samsung_SNH_1011_N_Webcam",
    "Provision_PT_838_Security_Camera",
    "Ecobee_Thermostat",
    "Provision_PT_737E_Security_Camera",
    "Danmini_Doorbell",
    "Philips_B120N10_Baby_Monitor",
    "SimpleHome_XCS7_1003_WHT_Security_Camera",
    "SimpleHome_XCS7_1002_WHT_Security_Camera"
)
if (-not (Test-Path -LiteralPath $SourceRoot -PathType Container)) {
    throw "Source directory containing original nine ZIP files not found"
}
if (-not (Test-Path -LiteralPath $Manifest -PathType Leaf)) {
    throw "Audited original-nine-ZIP manifest not found"
}
if (Test-Path -LiteralPath $Receipt) {
    throw "Refusing to overwrite an existing admission receipt"
}
$spec = Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
if ($spec.manifest_schema -ne "AFRAS_V2_ORIGINAL_NINE_DEVICE_ZIP_EXPECTED_BYTES_V1") {
    throw "Unknown research-original-ZIP manifest schema"
}
$items = @($spec.local_archives)
if ($items.Count -ne 9) {
    throw "Original research manifest must contain exactly nine device entries"
}
$results = New-Object System.Collections.ArrayList
$seen = @{}
$sum = [int64]0
for ($i=0; $i -lt 9; $i++) {
    $entry = $items[$i]
    $expectedDevice = $Canonical[$i]
    $dev = [string]$entry.device
    $filename = [string]$entry.filename
    $expectedHash = [string]$entry.local_sha256
    $expectedBytes = [int64]$entry.local_bytes
    if (($dev -cne $expectedDevice) -or $seen.ContainsKey($dev)) {
        throw "Non-canonical or duplicated device in manifest at position $i"
    }
    if (($filename -cne ($dev + ".zip")) -or ($expectedHash -cnotmatch "^[0-9a-f]{64}$") -or ($expectedBytes -le 0)) {
        throw "Invalid audited filename/SHA256/length for $dev"
    }
    $seen[$dev] = $true
    $path = Join-Path -Path $SourceRoot -ChildPath $filename
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing original research archive: $filename"
    }
    $stat = Get-Item -LiteralPath $path
    if ([int64]$stat.Length -ne $expectedBytes) {
        throw "Original archive byte-size mismatch: $filename"
    }
    # Hash ACTUAL raw ZIP bytes, without inspecting members, class labels or targets.
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -cne $expectedHash) {
        throw "Original archive SHA-256 mismatch: $filename"
    }
    $sum += $expectedBytes
    [void]$results.Add([pscustomobject]@{
        device = $dev
        filename = $filename
        bytes = $expectedBytes
        sha256 = $actual
        status = "BYTE_IDENTICAL_TO_PREVIOUS_LOCAL_AUDIT"
    })
    Write-Output ("ORIGINAL_ZIP_SHA256_MATCH {0} ({1} bytes)" -f $dev, $expectedBytes)
}
# Total bytes are the sum of the separately SHA-verified manifest entries.
# Its exact nine-source values are bound by the reviewer's manifest SHA-256.
$receiptDir = Split-Path -Path $Receipt -Parent
if ($receiptDir -and (-not (Test-Path -LiteralPath $receiptDir -PathType Container))) {
    New-Item -ItemType Directory -Path $receiptDir -Force | Out-Null
}
$manifestSHA = (Get-FileHash -LiteralPath $Manifest -Algorithm SHA256).Hash.ToLowerInvariant()
$record = [ordered]@{
    status = "ALL_NINE_ORIGINAL_ZIP_BYTES_MATCH_AUDITED_MANIFEST"
    check = "ACTUAL_FILE_BYTE_SHA256_STREAMING_WITH_POWERSHELL"
    original_zips_verified = 9
    original_zips_total_size = $sum
    original_source_manifest_sha256 = $manifestSHA
    verified_utc = [DateTime]::UtcNow.ToString("o")
    member_decompression_performed = $false
    heldout_model_predictions_generated = $false
    human_scientific_approval_created = $false
    supplied_files_byte_hashed = $true
    user_original_zip_provenance_attested_by_scanner = $false
    files = @($results.ToArray())
    limitations = "Verifies present original ZIP bytes against prior local auditor SHA256 values; does not verify source-class truth or substitute for responsible researcher approval."
}
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Receipt -Encoding UTF8 -NoNewline
Write-Output ("NINE_ORIGINAL_ZIP_SHA256_ADMISSION_PASS " + $manifestSHA)
