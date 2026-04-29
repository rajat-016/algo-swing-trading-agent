param(
    [switch]$NoDocker,
    [switch]$Full,
    [string]$Mode = "paper"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$envFile = Join-Path $scriptDir "backend\.env"
$displayMode = "paper"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    if ($envContent -match 'TRADING_MODE=(\w+)') {
        $displayMode = $Matches[1]
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Algo Swing Trading Agent" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$dockerAvailable = $false

if (-not $NoDocker) {
    try {
        $null = Get-Command docker -ErrorAction Stop
        $dockerStatus = docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            $dockerAvailable = $true
        }
    } catch {
        $dockerAvailable = $false
    }

    if (-not $dockerAvailable) {
        Write-Host "Docker not found or not running." -ForegroundColor Yellow
        Write-Host "Running in local mode (SQLite)" -ForegroundColor Yellow
    }
}

if ($dockerAvailable) {
    Write-Host "Starting Docker services..." -ForegroundColor Cyan
    docker compose up -d 2>$null
    Start-Sleep 2
}

Set-Location "$scriptDir\backend"

if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
}

Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& ".\venv\Scripts\Activate.ps1" | Out-Null

$pipCheck = pip show loguru 2>$null
if (-not $pipCheck) {
    Write-Host "Installing dependencies..." -ForegroundColor Cyan
    pip install -r requirements.txt
}

if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" -Force | Out-Null
}

if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file..." -ForegroundColor Cyan
    Copy-Item ".env.example" ".env"
}

if ($Full) {
    Write-Host ""
    Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan

    Set-Location "$scriptDir\frontend"

    if (-not (Test-Path "node_modules")) {
        npm install
    }

    Write-Host "Starting frontend..." -ForegroundColor Green
    
    cd $scriptDir\frontend
    npm start 2>&1 &
    cd $scriptDir\backend
    
    Start-Sleep -Seconds 3
}

Write-Host ""
Write-Host "Starting API server..." -ForegroundColor Green

try {
    $ip = (Invoke-WebRequest -URI "https://api.ipify.org" -UseBasicParsing -TimeoutSec 5).Content
    Write-Host "  Your IP: $ip (allow in Kite console for live trading)" -ForegroundColor Yellow
} catch {
    Write-Host "  IP detection failed" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Frontend URL: http://localhost:3000" -ForegroundColor Green
Write-Host "  Backend URL: http://localhost:8000" -ForegroundColor Green
Write-Host "  API Docs:    http://localhost:8000/docs" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

& ".\venv\Scripts\python.exe" main.py

Write-Host ""
Write-Host "Server stopped." -ForegroundColor Yellow