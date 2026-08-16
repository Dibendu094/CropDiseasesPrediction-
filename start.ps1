# ============================================================
#  AgriCare - start the app (backend + frontend, one server)
#  Run:  .\start.ps1          or   .\start.ps1 -Port 5055
# ============================================================
param(
    [int]$Port = 5000
)

Set-Location -LiteralPath $PSScriptRoot

$py = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
    Write-Host ""
    Write-Host "[!] No virtual environment found." -ForegroundColor Yellow
    Write-Host "    Run these once, then start again:"
    Write-Host ""
    Write-Host "      python -m venv venv"
    Write-Host "      venv\Scripts\Activate.ps1"
    Write-Host "      pip install -r backend\requirements.txt"
    Write-Host ""
    exit 1
}

# If the port is already taken, say so clearly instead of failing obscurely.
$busy = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($busy) {
    $owner = Get-Process -Id $busy[0].OwningProcess -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "[!] Port $Port is already in use by PID $($busy[0].OwningProcess) ($($owner.ProcessName))." -ForegroundColor Yellow
    Write-Host "    It may already be AgriCare - try opening http://localhost:$Port first."
    Write-Host "    Or start on another port:   .\start.ps1 -Port 5055"
    Write-Host ""
    exit 1
}

$env:PORT = "$Port"

Write-Host ""
Write-Host "  Starting AgriCare on http://localhost:$Port" -ForegroundColor Green
Write-Host "  First start takes 40-60 seconds (loading the models)..."
Write-Host "  Press Ctrl+C to stop."
Write-Host ""

& $py (Join-Path $PSScriptRoot 'backend\app.py')
