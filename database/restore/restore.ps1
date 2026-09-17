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

$RepositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
if (-not $ComposeFile) { $ComposeFile = Join-Path $RepositoryRoot 'environments/local/compose.yaml' }
$ComposeFile = (Resolve-Path -LiteralPath $ComposeFile).Path
$ContainerFile = '/tmp/alos-controlled-restore.dump'

& docker compose -f $ComposeFile cp $BackupFile "postgres:$ContainerFile"
if ($LASTEXITCODE -ne 0) { throw 'Penyalinan backup ke container gagal.' }
& docker compose -f $ComposeFile exec -T postgres sh -c `
    'pg_restore --clean --if-exists --exit-on-error --no-owner --no-privileges --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" "$1"' `
    sh $ContainerFile
if ($LASTEXITCODE -ne 0) { throw 'pg_restore gagal.' }
& docker compose -f $ComposeFile exec -T postgres rm -f $ContainerFile
& docker compose -f $ComposeFile exec -T postgres sh -c `
    'psql --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --tuples-only --command="SELECT 1; SELECT extname FROM pg_extension WHERE extname = '\''vector'\'';"'
if ($LASTEXITCODE -ne 0) { throw 'Verification query gagal.' }

Write-Host 'Restore selesai. Jalankan application smoke test dan verification checklist sebelum membuka traffic.'
