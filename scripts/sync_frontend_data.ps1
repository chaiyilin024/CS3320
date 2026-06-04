# 同步 artifacts → frontend/public/data（Windows PowerShell）
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$Python = if ($env:PYTHON) { $env:PYTHON } elseif (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
& $Python scripts/sync_frontend_data.py @args
