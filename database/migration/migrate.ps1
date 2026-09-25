[CmdletBinding()]
param(
    [string]$ComposeFile,
    [string]$EnvFile,
    [switch]$SkipBackup
)

$ErrorActionPreference = 'Stop'

if ($env:CONFIRM_MIGRATION -ne 'YES') {
    throw 'ERROR: Migrasi database production memerlukan konfirmasi eksplisit: set CONFIRM_MIGRATION=YES'
}

$RepositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
if (-not $ComposeFile) {
    if (Test-Path (Join-Path $RepositoryRoot 'environments/production/app/compose.yaml')) {
        $ComposeFile = Join-Path $RepositoryRoot 'environments/production/app/compose.yaml'
    } elseif (Test-Path (Join-Path $RepositoryRoot 'environments/staging/compose.yaml')) {
        $ComposeFile = Join-Path $RepositoryRoot 'environments/staging/compose.yaml'
    } else {
        $ComposeFile = Join-Path $RepositoryRoot 'environments/local/compose.yaml'
    }
}
$ComposeFile = (Resolve-Path -LiteralPath $ComposeFile).Path

$CmdArgs = @('-f', $ComposeFile)
if ($EnvFile) {
    if (-not (Test-Path -LiteralPath $EnvFile)) {
        throw "ERROR: File environment tidak ditemukan: $EnvFile"
    }
    $EnvFile = (Resolve-Path -LiteralPath $EnvFile).Path
    $CmdArgs = @('--env-file', $EnvFile) + $CmdArgs
}

Write-Host '=================================================='
Write-Host 'ALOS DATABASE MIGRATION RUNNER'
Write-Host "Target compose: $ComposeFile"
Write-Host '=================================================='

# 1. Pre-migration backup check
if (-not $SkipBackup) {
    Write-Host "`n[1/4] Memeriksa status backup sebelum migrasi..."
    if ($env:PRE_MIGRATION_BACKUP_VERIFIED -ne 'YES') {
        throw 'PERINGATAN: Pastikan Anda telah mengambil snapshot database terkini di VPS 3 (DATA). Set PRE_MIGRATION_BACKUP_VERIFIED=YES atau gunakan -SkipBackup jika non-prod.'
    }
    Write-Host '  -> Pre-migration backup terverifikasi (PRE_MIGRATION_BACKUP_VERIFIED=YES)'
} else {
    Write-Host "`n[1/4] Pre-migration backup dilewati (-SkipBackup aktif)"
}

# 2. Preflight schema inspection
Write-Host "`n[2/4] Memeriksa revisi skema database saat ini (alembic current)..."
& docker compose @CmdArgs run --rm --no-deps backend alembic current
if ($LASTEXITCODE -ne 0) {
    throw 'ERROR: Gagal membaca revisi skema database saat ini. Periksa konektivitas DB.'
}

# 3. Execute migration single-run
Write-Host "`n[3/4] Menjalankan migrasi skema tunggal (alembic upgrade head)..."
& docker compose @CmdArgs run --rm --no-deps backend alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    throw 'ERROR: Eksekusi migrasi database GAGAL! Segera rujuk runbooks/rollback.md untuk mitigasi.'
}

# 4. Verify post-migration schema head
Write-Host "`n[4/4] Verifikasi revisi skema setelah migrasi..."
& docker compose @CmdArgs run --rm --no-deps backend alembic current
if ($LASTEXITCODE -ne 0) {
    throw 'ERROR: Verifikasi revisi skema setelah migrasi gagal.'
}

Write-Host "`n=================================================="
Write-Host 'MIGRASI BERHASIL DISELESAIKAN SECARA AMAN!'
Write-Host 'Lanjutkan dengan rilis/start container backend di VPS 1 (APP).'
Write-Host '=================================================='
