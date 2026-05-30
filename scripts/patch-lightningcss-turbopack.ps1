# Patch lightningcss module resolution for Turbopack on Windows ARM64.
$ErrorActionPreference = "Stop"
$index = Join-Path $PSScriptRoot "..\frontend\node_modules\lightningcss\node\index.js"
if (-not (Test-Path $index)) { exit 0 }
$content = Get-Content $index -Raw
if ($content -match 'process\.cwd\(\)') { exit 0 }
$old = @'
let native;
try {
  native = require(`lightningcss-${parts.join('-')}`);
} catch (err) {
  native = require(`../lightningcss.${parts.join('-')}.node`);
}
'@
$new = @'
let native;
const path = require('path');
const pkgName = `lightningcss-${parts.join('-')}`;
try {
  native = require(pkgName);
} catch (err) {
  try {
    native = require(path.join(process.cwd(), 'node_modules', pkgName));
  } catch (err2) {
    native = require(path.join(__dirname, '..', `lightningcss.${parts.join('-')}.node`));
  }
}
'@
if ($content.Contains($old.Trim())) {
    Set-Content -Path $index -Value ($content.Replace($old.Trim(), $new.Trim())) -NoNewline
    Write-Host "Patched lightningcss for Turbopack (ARM64)."
}
