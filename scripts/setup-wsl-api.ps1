# Run from Windows PowerShell AFTER reboot (WSL features enabled).
# Installs Ubuntu if missing, then runs API setup inside WSL.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Sh = Join-Path $ProjectRoot "scripts\setup-wsl-api.sh"

Write-Host "Checking WSL..."
wsl --status 2>&1 | Out-Host

$distros = wsl -l -q 2>&1
if ($distros -notmatch "Ubuntu") {
    Write-Host "Installing Ubuntu..."
    wsl --install -d Ubuntu --no-launch
    Write-Host "Complete Ubuntu first-run in the new window (username/password), then run this script again."
    wsl -d Ubuntu
    exit 0
}

# Stop Windows-native API on :8000 so WSL can bind the port
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

$wslSh = "/mnt/c/Users/Umerm/Desktop/Bit.camp/qbridge-os/scripts/setup-wsl-api.sh"
Write-Host "Running API setup in Ubuntu (WSL2) — leave that WSL window open..."
wsl -d Ubuntu -e bash -lc "sed -i 's/\r$//' '$wslSh' && bash '$wslSh'"
