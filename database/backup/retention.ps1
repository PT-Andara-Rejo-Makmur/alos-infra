[CmdletBinding()]
param(
    [string]$BackupDirectory,
    [int]$DailyKeep = 7,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$RepositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path

if (-not $BackupDirectory) {
    if ($env:BACKUP_DIR) {
        $BackupDirectory = $env:BACKUP_DIR
    } else {
        $BackupDirectory = Join-Path $RepositoryRoot 'backups'
    }
}

if (-not (Test-Path -LiteralPath $BackupDirectory)) {
    Write-Host "Direktori backup tidak ditemukan: $BackupDirectory"
    return
}

$BackupDirectory = (Resolve-Path -LiteralPath $BackupDirectory).Path
$DumpFiles = Get-ChildItem -LiteralPath $BackupDirectory -Filter "alos-*.dump" -File | Sort-Object LastWriteTime -Descending

$TotalDumps = $DumpFiles.Count
Write-Host "Total file backup ditemukan: $TotalDumps (di $BackupDirectory)"
Write-Host "Kebijakan retensi harian: simpan $DailyKeep file terbaru"

if ($TotalDumps -le $DailyKeep) {
    Write-Host "Jumlah backup ($TotalDumps) tidak melebihi batas retensi ($DailyKeep). Tidak ada file yang dihapus."
    return
}

$DeleteCount = 0
for ($i = $DailyKeep; $i -lt $TotalDumps; $i++) {
    $DumpToDelete = $DumpFiles[$i].FullName
    $ChecksumToDelete = "$DumpToDelete.sha256"

    if ($DryRun) {
        Write-Host "[DRY-RUN] Akan menghapus: $DumpToDelete"
        if (Test-Path -LiteralPath $ChecksumToDelete) {
            Write-Host "[DRY-RUN] Akan menghapus: $ChecksumToDelete"
        }
    } else {
        Write-Host "Menghapus backup kedaluwarsa: $DumpToDelete"
        Remove-Item -LiteralPath $DumpToDelete -Force
        if (Test-Path -LiteralPath $ChecksumToDelete) {
            Remove-Item -LiteralPath $ChecksumToDelete -Force
        }
    }
    $DeleteCount++
}

Write-Host "Selesai: $DeleteCount file backup diproses untuk rotasi (DryRun=$DryRun)."
