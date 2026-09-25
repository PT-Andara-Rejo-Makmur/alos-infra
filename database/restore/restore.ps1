[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$BackupFile,
    [string]$TargetDatabase = 'alos_restore_verify',
    [string]$ComposeFile,
    [switch]$ConfirmProduction
)

$ErrorActionPreference = 'Stop'

if ($env:CONFIRM_DATABASE_RESTORE -ne 'YES') {
    throw 'ERROR: Restore database memerlukan konfirmasi eksplisit: set CONFIRM_DATABASE_RESTORE=YES'
}

$BackupFile = (Resolve-Path -LiteralPath $BackupFile).Path
if (-not (Test-Path -LiteralPath $BackupFile) -or (Get-Item -LiteralPath $BackupFile).Length -eq 0) {
    throw "ERROR: Backup tidak ditemukan atau kosong: $BackupFile"
}

$ChecksumFile = "$BackupFile.sha256"
if (-not (Test-Path -LiteralPath $ChecksumFile -PathType Leaf)) {
    throw "ERROR: Checksum sidecar tidak ditemukan: $ChecksumFile"
}

$ChecksumLine = (Get-Content -LiteralPath $ChecksumFile -TotalCount 1).Trim()
$ExpectedChecksum = ($ChecksumLine -split '\s+')[0].ToLowerInvariant()
if ($ExpectedChecksum -notmatch '^[0-9a-f]{64}$') {
    throw "ERROR: Format checksum tidak valid: $ChecksumFile"
}

$ActualChecksum = (Get-FileHash -LiteralPath $BackupFile -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ExpectedChecksum -ne $ActualChecksum) {
    throw "ERROR: Checksum backup tidak cocok! Expected: $ExpectedChecksum, Actual: $ActualChecksum. Restore DIBATALKAN."
}

$RepositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
if (-not $ComposeFile) {
    if ($env:COMPOSE_FILE) {
        $ComposeFile = $env:COMPOSE_FILE
    } elseif (Test-Path (Join-Path $RepositoryRoot 'environments/production/data/compose.yaml')) {
        $ComposeFile = Join-Path $RepositoryRoot 'environments/production/data/compose.yaml'
    } elseif (Test-Path (Join-Path $RepositoryRoot 'environments/staging/compose.yaml')) {
        $ComposeFile = Join-Path $RepositoryRoot 'environments/staging/compose.yaml'
    } else {
        $ComposeFile = Join-Path $RepositoryRoot 'environments/local/compose.yaml'
    }
}
$ComposeFile = (Resolve-Path -LiteralPath $ComposeFile).Path

# Detect production database from compose environment
$ConfiguredProdDb = (& docker compose -f $ComposeFile exec -T postgres sh -c 'echo "$POSTGRES_DB"' 2>$null).Trim()
if ($ConfiguredProdDb -and ($TargetDatabase -eq $ConfiguredProdDb)) {
    if (-not $ConfirmProduction -and ($env:CONFIRM_PRODUCTION -ne 'YES')) {
        Write-Error "SAFETY GUARD AKTIF: Target restore [$TargetDatabase] adalah DATABASE PRODUKSI AKTIF! Tindakan ini membutuhkan flag -ConfirmProduction atau env var CONFIRM_PRODUCTION=YES."
        exit 3
    }
    Write-Warning "PERINGATAN TINGGI: Menjalankan restore ke DATABASE PRODUKSI AKTIF [$TargetDatabase]."
}

$ContainerFile = "/tmp/alos-controlled-restore-$PID.dump"

try {
    Write-Host "Memulai controlled restore ke database [$TargetDatabase]..."

    # Ensure target database exists
    & docker compose -f $ComposeFile exec -T postgres sh -c `
        "psql --username=`"`$POSTGRES_USER`" -d template1 -tc `"SELECT 1 FROM pg_database WHERE datname = '$TargetDatabase'`" | grep -q 1 || psql --username=`"`$POSTGRES_USER`" -d template1 -c `"CREATE DATABASE \`"$TargetDatabase\`" WITH TEMPLATE template1;`"" 2>$null

    & docker compose -f $ComposeFile cp $BackupFile "postgres:$ContainerFile"
    if ($LASTEXITCODE -ne 0) { throw 'ERROR: Penyalinan backup ke container gagal.' }

    & docker compose -f $ComposeFile exec -T postgres sh -c `
        "pg_restore --clean --if-exists --exit-on-error --no-owner --no-privileges --username=`"`$POSTGRES_USER`" --dbname=`"$TargetDatabase`" `"$ContainerFile`""
    if ($LASTEXITCODE -ne 0) { throw "ERROR: pg_restore gagal pada database [$TargetDatabase]." }

    & docker compose -f $ComposeFile exec -T postgres sh -c `
        "psql --username=`"`$POSTGRES_USER`" --dbname=`"$TargetDatabase`" --tuples-only --command=`"SELECT 1; SELECT extname FROM pg_extension WHERE extname = 'vector';`""
    if ($LASTEXITCODE -ne 0) { throw 'ERROR: Verification query gagal.' }
}
finally {
    & docker compose -f $ComposeFile exec -T postgres rm -f $ContainerFile 2>$null
}

Write-Host "`n=================================================="
Write-Host 'RESTORE DATABASE BERHASIL DISELESAIKAN SECARA AMAN!'
Write-Host "Target Database : $TargetDatabase"
Write-Host "Source Backup   : $BackupFile"
Write-Host "Checksum Verified: $ActualChecksum (SHA-256 MATCH)"
Write-Host '=================================================='
