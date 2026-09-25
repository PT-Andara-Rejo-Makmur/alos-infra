[CmdletBinding()]
param(
    [string]$ComposeFile,
    [string]$BackupDirectory
)

$ErrorActionPreference = 'Stop'
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

if (-not $BackupDirectory) {
    if ($env:BACKUP_DIR) {
        $BackupDirectory = $env:BACKUP_DIR
    } else {
        $BackupDirectory = Join-Path $RepositoryRoot 'backups'
    }
}
$BackupDirectory = [System.IO.Path]::GetFullPath($BackupDirectory)
New-Item -ItemType Directory -Path $BackupDirectory -Force | Out-Null

# Extract database identity safely
$DbName = (& docker compose -f $ComposeFile exec -T postgres sh -c 'echo "$POSTGRES_DB"' 2>$null).Trim()
if (-not $DbName) { $DbName = 'alos' }

$Timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$ContainerFile = "/tmp/alos-$DbName-$Timestamp.dump"
$BackupFile = Join-Path $BackupDirectory "alos-$DbName-$Timestamp.dump"
$ChecksumFile = "$BackupFile.sha256"

# Overwrite guard
if (Test-Path -LiteralPath $BackupFile) {
    throw "ERROR: File backup sasaran sudah ada: $BackupFile"
}

try {
    Write-Host "Memulai backup database [$DbName]..."
    & docker compose -f $ComposeFile exec -T postgres sh -c `
        'pg_dump --format=custom --no-owner --no-privileges --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --file="$1"' `
        sh $ContainerFile
    if ($LASTEXITCODE -ne 0) { throw 'ERROR: pg_dump gagal dijalankan di dalam container postgres.' }

    & docker compose -f $ComposeFile cp "postgres:$ContainerFile" $BackupFile
    if ($LASTEXITCODE -ne 0) { throw 'ERROR: Gagal menyalin backup file dari container ke host.' }
}
finally {
    & docker compose -f $ComposeFile exec -T postgres rm -f $ContainerFile 2>$null
}

if (-not (Test-Path -LiteralPath $BackupFile) -or (Get-Item -LiteralPath $BackupFile).Length -eq 0) {
    if (Test-Path -LiteralPath $BackupFile) { Remove-Item -LiteralPath $BackupFile -Force }
    throw 'ERROR: Backup tidak ditemukan atau berukuran 0 byte.'
}

$Checksum = (Get-FileHash -LiteralPath $BackupFile -Algorithm SHA256).Hash.ToLowerInvariant()
if (-not $Checksum -or $Checksum.Length -ne 64) {
    if (Test-Path -LiteralPath $BackupFile) { Remove-Item -LiteralPath $BackupFile -Force }
    throw 'ERROR: Gagal membuat checksum SHA-256 yang valid.'
}

"$Checksum  $([System.IO.Path]::GetFileName($BackupFile))" | Set-Content -LiteralPath $ChecksumFile -Encoding ascii

Write-Host "`n=================================================="
Write-Host 'BACKUP BERHASIL DIBUAT DENGAN AMAN!'
Write-Host "Database Identity : $DbName"
Write-Host "Backup File       : $BackupFile ($((Get-Item -LiteralPath $BackupFile).Length) bytes)"
Write-Host "SHA-256 Checksum  : $Checksum"
Write-Host "Checksum File     : $ChecksumFile"
Write-Host '=================================================='
Write-Host 'Rekomendasi Operasional:'
Write-Host '1. Salin file dump dan checksum ke off-site object storage (mis. Cloudflare R2 / S3).'
Write-Host '2. Jalankan rotasi retensi (database/backup/retention.ps1).'
Write-Host '3. Jangan bergantung pada satu node VPS yang sama untuk disaster recovery.'
