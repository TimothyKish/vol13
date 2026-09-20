# ============================================================
# KishLattice Vol 11 - Pre-Flight Lake Validation
# Run from: C:\Users\timot\Downloads\Science\src\Unification\vol11\
# Usage: .\Validate_Vol11_Lakes.ps1
# ============================================================

$ROOT     = "C:\Users\timot\Downloads\Science\src\Unification\vol11"
$VOLUMES  = Join-Path $ROOT "configs\volumes.json"
$OUTFILE  = Join-Path $ROOT "lakes\logs\preflight_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"

# Ensure log directory exists
$logDir = Join-Path $ROOT "lakes\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

function Write-Log {
    param($msg, $color = "White")
    Write-Host $msg -ForegroundColor $color
    Add-Content -Path $OUTFILE -Value $msg
}

Write-Log "============================================================"
Write-Log "  KishLattice Vol 11 Pre-Flight Lake Validation"
Write-Log "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss UTC')"
Write-Log "  Root: $ROOT"
Write-Log "============================================================"
Write-Log ""

# Load and parse volumes.json
if (-not (Test-Path $VOLUMES)) {
    Write-Log "FATAL: volumes.json not found at $VOLUMES" "Red"
    exit 1
}

$raw  = Get-Content $VOLUMES -Raw
$vols = ($raw | ConvertFrom-Json).volumes

# Count enabled lakes
$enabledLakes = $vols.PSObject.Properties | Where-Object { $_.Value.enabled -eq $true }
$totalEnabled = ($enabledLakes | Measure-Object).Count
Write-Log "Enabled lakes to validate: $totalEnabled"
Write-Log ""

# Header
$hdr = "{0,-32} {1,-28} {2,-10} {3}" -f "Lake ID", "Expected Domain", "Status", "File / Domain Check"
Write-Log $hdr
Write-Log ("-" * 100)

$okCount      = 0
$missingCount = 0
$emptyCount   = 0
$mismatchCount = 0
$parseErrCount = 0

$enabledLakes | ForEach-Object {
    $lakeId  = $_.Name
    $meta    = $_.Value
    $domain  = $meta.domain
    $relPath = $meta.path -replace "/", "\"
    $path    = Join-Path $ROOT $relPath

    if (-not (Test-Path $path)) {
        $line = "{0,-32} {1,-28} {2,-10} {3}" -f $lakeId, $domain, "MISSING", "FILE NOT FOUND: $path"
        Write-Log $line "Red"
        $missingCount++
        return
    }

    # Read first line
    $firstLine = $null
    try {
        $firstLine = Get-Content $path -First 1 -ErrorAction Stop
    } catch {
        $line = "{0,-32} {1,-28} {2,-10} {3}" -f $lakeId, $domain, "READ_ERR", $_.Exception.Message
        Write-Log $line "Red"
        $parseErrCount++
        return
    }

    if ([string]::IsNullOrWhiteSpace($firstLine)) {
        $line = "{0,-32} {1,-28} {2,-10} {3}" -f $lakeId, $domain, "EMPTY", "No records in file"
        Write-Log $line "Yellow"
        $emptyCount++
        return
    }

    # Parse JSON record
    try {
        $rec = $firstLine | ConvertFrom-Json -ErrorAction Stop
        $actualDomain = if ($rec.domain) { $rec.domain } else { "NO_DOMAIN_FIELD" }

        if ($actualDomain -eq $domain) {
            $line = "{0,-32} {1,-28} {2,-10} {3}" -f $lakeId, $domain, "OK", "domain matches"
            Write-Log $line "Green"
            $okCount++
        } else {
            $line = "{0,-32} {1,-28} {2,-10} {3}" -f $lakeId, $domain, "MISMATCH", "File has: $actualDomain"
            Write-Log $line "Red"
            $mismatchCount++
        }
    } catch {
        $line = "{0,-32} {1,-28} {2,-10} {3}" -f $lakeId, $domain, "PARSE_ERR", $_.Exception.Message
        Write-Log $line "Red"
        $parseErrCount++
    }
}

# Summary
Write-Log ""
Write-Log "============================================================"
Write-Log "  SUMMARY"
Write-Log "============================================================"
Write-Log "  Total enabled:    $totalEnabled"
Write-Log "  OK (domain match): $okCount"    $(if ($okCount -eq $totalEnabled) { "Green" } else { "White" })
Write-Log "  MISSING files:    $missingCount" $(if ($missingCount -gt 0) { "Red" } else { "White" })
Write-Log "  EMPTY files:      $emptyCount"  $(if ($emptyCount -gt 0) { "Yellow" } else { "White" })
Write-Log "  MISMATCH domain:  $mismatchCount" $(if ($mismatchCount -gt 0) { "Red" } else { "White" })
Write-Log "  PARSE errors:     $parseErrCount" $(if ($parseErrCount -gt 0) { "Red" } else { "White" })
Write-Log ""

if (($missingCount + $emptyCount + $mismatchCount + $parseErrCount) -eq 0) {
    Write-Log "  *** ALL LAKES CLEAR — AUTHORISED FOR GRAND MASTER RUN ***" "Green"
} else {
    Write-Log "  *** ISSUES FOUND — RESOLVE BEFORE RUNNING PIPELINE ***" "Red"
}

Write-Log ""
Write-Log "  Log saved to: $OUTFILE"
Write-Log "============================================================"