# Install optional native npm packages missing on Windows ARM64 (no npm in PATH).
$ErrorActionPreference = "Stop"
$Frontend = Join-Path $PSScriptRoot "..\frontend"
$nodeModules = Join-Path $Frontend "node_modules"

function Install-NpmTarball {
    param([string]$Name, [string]$Version)
    $dest = Join-Path $nodeModules $Name
    if (Test-Path (Join-Path $dest "package.json")) {
        Write-Host "  skip $Name (exists)"
        return
    }
    Write-Host "  install $Name@$Version"
    $meta = Invoke-RestMethod "https://registry.npmjs.org/$([uri]::EscapeDataString($Name))/$Version"
    $tmp = Join-Path $env:TEMP "$($Name -replace '/','-').tgz"
    Invoke-WebRequest -Uri $meta.dist.tarball -OutFile $tmp
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    tar -xzf $tmp -C $dest --strip-components=1
}

Write-Host "Installing ARM64 native frontend binaries..."
Install-NpmTarball "@next/swc-win32-arm64-msvc" "16.2.4"
Install-NpmTarball "lightningcss-win32-arm64-msvc" "1.32.0"
Install-NpmTarball "@tailwindcss/oxide-win32-arm64-msvc" "4.2.4"

$lcSrc = Join-Path $nodeModules "lightningcss-win32-arm64-msvc\lightningcss.win32-arm64-msvc.node"
$lcDst = Join-Path $nodeModules "lightningcss\lightningcss.win32-arm64-msvc.node"
if (Test-Path $lcSrc) { Copy-Item $lcSrc $lcDst -Force }

Write-Host "Done."
