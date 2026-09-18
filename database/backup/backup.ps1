[CmdletBinding()]
param(
    [string]$ComposeFile,
    [string]$BackupDirectory
)

$ErrorActionPreference = 'Stop'
$RepositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
if (-not $ComposeFile) { $ComposeFile = Join-Path $RepositoryRoot 'environments/local/compose.yaml' }
if (-not $BackupDirectory) { $BackupDirectory = Join-Path $RepositoryRoot 'backups' }
$ComposeFile = (Resolve-Path -LiteralPath $ComposeFile).Path
$BackupDirectory = [System.IO.Path]::GetFullPath($BackupDirectory)
New-Item -ItemType Directory -Path $BackupDirectory -Force | Out-Null

$Timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$ContainerFile = "/tmp/alos-$Timestamp.dump"
$BackupFile = Join-Path $BackupDirectory "alos-$Timestamp.dump"
$ChecksumFile = "$BackupFile.sha256"

try {
    & docker compose -f $ComposeFile exec -T postgres sh -c `
        'pg_dump --format=custom --no-owner --no-privileges --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --file="$1"' `
        sh $ContainerFile
    if ($LASTEXITCODE -ne 0) { throw 'pg_dump gagal.' }

    & docker compose -f $ComposeFile cp "postgres:$ContainerFile" $BackupFile
    if ($LASTEXITCODE -ne 0) { throw 'Penyalinan backup dari container gagal.' }
}
finally {
    & docker compose -f $ComposeFile exec -T postgres rm -f $ContainerFile 2>$null
}

if (-not (Test-Path -LiteralPath $BackupFile) -or (Get-Item -LiteralPath $BackupFile).Length -eq 0) {
    throw 'Backup tidak ditemukan atau kosong.'
}
$Checksum = (Get-FileHash -LiteralPath $BackupFile -Algorithm SHA256).Hash.ToLowerInvariant()
"$Checksum  $([System.IO.Path]::GetFileName($BackupFile))" | Set-Content -LiteralPath $ChecksumFile -Encoding ascii

Write-Host "Backup dibuat: $BackupFile"
Write-Host "Checksum dibuat: $ChecksumFile"
Write-Host 'Lanjutkan dengan off-site copy, retention, dan restore test sesuai operator policy.'
