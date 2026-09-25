[CmdletBinding()]
param(
    [string]$Target = 'local',
    [string]$ComposeFile,
    [int]$WebPort = 3000,
    [int]$BackendPort = 8000
)

$ErrorActionPreference = 'Stop'
$RepositoryRoot = Split-Path -Parent $PSScriptRoot

function Test-HttpHealth {
    param([string]$Name, [string]$Uri)

    Write-Host "Memeriksa $Name ... " -NoNewline
    $Response = Invoke-WebRequest -Uri $Uri -TimeoutSec 5 -UseBasicParsing
    if ($Response.StatusCode -lt 200 -or $Response.StatusCode -ge 400) {
        throw "$Name mengembalikan HTTP $($Response.StatusCode)."
    }
    Write-Host 'sehat'
}

switch ($Target.ToLowerInvariant()) {
    'local' {
        if (-not $ComposeFile) { $ComposeFile = Join-Path $RepositoryRoot 'environments/local/compose.yaml' }
        $ComposeFile = (Resolve-Path -LiteralPath $ComposeFile).Path

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
    }

    'app' {
        if (-not $ComposeFile) { $ComposeFile = Join-Path $RepositoryRoot 'environments/production/app/compose.yaml' }
        $ComposeFile = (Resolve-Path -LiteralPath $ComposeFile).Path
        Write-Host 'Memeriksa node VPS 1 APP ...'

        & docker compose -f $ComposeFile exec -T web node -e `
            "fetch('http://127.0.0.1:3000').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Health check alos-web gagal.' }
        Write-Host 'alos-web: sehat'

        & docker compose -f $ComposeFile exec -T backend python -c `
            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Health check alos-backend gagal.' }
        Write-Host 'alos-backend: sehat'

        Write-Host 'Semua service VPS 1 APP sehat.'
    }

    'genesis' {
        if (-not $ComposeFile) { $ComposeFile = Join-Path $RepositoryRoot 'environments/production/genesis/compose.yaml' }
        $ComposeFile = (Resolve-Path -LiteralPath $ComposeFile).Path
        Write-Host 'Memeriksa node VPS 2 GENESIS ...'

        & docker compose -f $ComposeFile exec -T genesis python -c `
            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/health', timeout=5)" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Health check genesis-ai gagal.' }
        Write-Host 'genesis-ai: sehat'
        Write-Host 'Semua service VPS 2 GENESIS sehat.'
    }

    'data' {
        if (-not $ComposeFile) { $ComposeFile = Join-Path $RepositoryRoot 'environments/production/data/compose.yaml' }
        $ComposeFile = (Resolve-Path -LiteralPath $ComposeFile).Path
        Write-Host 'Memeriksa node VPS 3 DATA ...'

        & docker compose -f $ComposeFile exec -T postgres sh -c `
            'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Health check PostgreSQL gagal.' }
        Write-Host 'postgres: sehat'
        Write-Host 'Semua service VPS 3 DATA sehat.'
    }

    'staging' {
        if (-not $ComposeFile) { $ComposeFile = Join-Path $RepositoryRoot 'environments/staging/compose.yaml' }
        $ComposeFile = (Resolve-Path -LiteralPath $ComposeFile).Path
        Write-Host 'Memeriksa node VPS 4 STAGING ...'

        & docker compose -f $ComposeFile exec -T web node -e `
            "fetch('http://127.0.0.1:3000').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Health check alos-web gagal.' }
        Write-Host 'alos-web: sehat'

        & docker compose -f $ComposeFile exec -T backend python -c `
            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Health check alos-backend gagal.' }
        Write-Host 'alos-backend: sehat'

        & docker compose -f $ComposeFile exec -T genesis python -c `
            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/health', timeout=5)" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Health check genesis-ai gagal.' }
        Write-Host 'genesis-ai: sehat'

        & docker compose -f $ComposeFile exec -T postgres sh -c `
            'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Health check PostgreSQL gagal.' }
        Write-Host 'postgres: sehat'
        Write-Host 'Semua service VPS 4 STAGING sehat.'
    }

    default {
        throw "Target tidak dikenal: $Target (pilihan: local, app, genesis, data, staging)"
    }
}
