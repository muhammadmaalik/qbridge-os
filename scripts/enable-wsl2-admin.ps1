# Run this script in an elevated PowerShell (Run as Administrator).
# Repairs WSL (DISM features + latest Microsoft.WSL package), then reboot.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "Repairing / upgrading Windows Subsystem for Linux (winget)..."
winget install --id Microsoft.WSL -e --accept-source-agreements --accept-package-agreements

Write-Host "Enabling Windows Subsystem for Linux..."
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

Write-Host "Enabling Virtual Machine Platform..."
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

Write-Host "Queueing Ubuntu (effective after reboot)..."
wsl --install -d Ubuntu --no-launch

Write-Host ""
Write-Host "REBOOT required. After reboot:"
Write-Host "  1) Finish Ubuntu first-run if a window opens (username + password)"
Write-Host "  2) cd $Root"
Write-Host "  3) .\scripts\setup-wsl-api.ps1"
$reboot = Read-Host "Reboot now? (y/N)"
if ($reboot -eq "y" -or $reboot -eq "Y") {
    Restart-Computer -Force
}
