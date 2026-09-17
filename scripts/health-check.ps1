[CmdletBinding()]
param(
    [string]$ComposeFile,
    [int]$WebPort = 3000,
    [int]$BackendPort = 8000
)

$ErrorActionPreference = 'Stop'
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
if (-not $ComposeFile) {
    $ComposeFile = Join-Path $RepositoryRoot 'environments/local/compose.yaml'
}
$ComposeFile = (Resolve-Path -LiteralPath $ComposeFile).Path

function Test-HttpHealth {
    param([string]$Name, [string]$Uri)

    Write-Host "Memeriksa $Name ... " -NoNewline
    $Response = Invoke-WebRequest -Uri $Uri -TimeoutSec 5
    if ($Response.StatusCode -lt 200 -or $Response.StatusCode -ge 400) {
        throw "$Name mengembalikan HTTP $($Response.StatusCode)."
    }
    Write-Host 'sehat'
}

Test-HttpHealth -Name 'alos-web' -Uri "http://127.0.0.1:$WebPort/"
Test-HttpHealth -Name 'alos-backend' -Uri "http://127.0.0.1:$BackendPort/health"

Write-Host 'Memeriksa genesis-ai (internal) ... ' -NoNewline
& docker compose -f $ComposeFile exec -T genesis python -c `
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/health', timeout=5)" | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Health check genesis-ai gagal.' }
Write-Host 'sehat'

Write-Host 'Memeriksa postgres (internal) ... ' -NoNewline
& docker compose -f $ComposeFile exec -T postgres sh -c `
    'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Health check PostgreSQL gagal.' }
Write-Host 'sehat'

Write-Host 'Semua service local sehat.'
