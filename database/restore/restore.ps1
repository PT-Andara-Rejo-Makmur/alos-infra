[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$BackupFile,
    [string]$ComposeFile
)

$ErrorActionPreference = 'Stop'
if ($env:CONFIRM_DATABASE_RESTORE -ne 'YES') {
    throw 'Set CONFIRM_DATABASE_RESTORE=YES setelah approval untuk menjalankan restore.'
}
$BackupFile = (Resolve-Path -LiteralPath $BackupFile).Path
if ((Get-Item -LiteralPath $BackupFile).Length -eq 0) { throw 'Backup kosong.' }
$ChecksumFile = "$BackupFile.sha256"
if (-not (Test-Path -LiteralPath $ChecksumFile -PathType Leaf)) {
    throw "Checksum sidecar tidak ditemukan: $ChecksumFile"
}
$ChecksumLine = (Get-Content -LiteralPath $ChecksumFile -TotalCount 1).Trim()
$ExpectedChecksum = ($ChecksumLine -split '\s+')[0].ToLowerInvariant()
if ($ExpectedChecksum -notmatch '^[0-9a-f]{64}$') { throw 'Format checksum tidak valid.' }
$ActualChecksum = (Get-FileHash -LiteralPath $BackupFile -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ExpectedChecksum -ne $ActualChecksum) { throw 'Checksum backup tidak cocok. Restore dibatalkan.' }

$RepositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
if (-not $ComposeFile) { $ComposeFile = Join-Path $RepositoryRoot 'environments/local/compose.yaml' }
$ComposeFile = (Resolve-Path -LiteralPath $ComposeFile).Path
$ContainerFile = '/tmp/alos-controlled-restore.dump'

try {
    & docker compose -f $ComposeFile cp $BackupFile "postgres:$ContainerFile"
    if ($LASTEXITCODE -ne 0) { throw 'Penyalinan backup ke container gagal.' }
    & docker compose -f $ComposeFile exec -T postgres sh -c `
        'pg_restore --clean --if-exists --exit-on-error --no-owner --no-privileges --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" "$1"' `
        sh $ContainerFile
    if ($LASTEXITCODE -ne 0) { throw 'pg_restore gagal.' }
    & docker compose -f $ComposeFile exec -T postgres sh -c `
        'psql --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --tuples-only --command="SELECT 1; SELECT extname FROM pg_extension WHERE extname = '\''vector'\'';"'
    if ($LASTEXITCODE -ne 0) { throw 'Verification query gagal.' }
}
finally {
    & docker compose -f $ComposeFile exec -T postgres rm -f $ContainerFile 2>$null
}

Write-Host 'Restore selesai. Jalankan application smoke test dan verification checklist sebelum membuka traffic.'
