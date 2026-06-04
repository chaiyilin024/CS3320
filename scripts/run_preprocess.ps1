# 预处理示例（Windows PowerShell）
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$Python = if ($env:PYTHON) { $env:PYTHON } elseif (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

pip install -r backend/requirements.txt -q

& $Python backend/preprocessing/run_pipeline.py `
  --pdf example/01001012_黄鹤楼.pdf `
  --collection-id 01000000

$samples = Join-Path "artifacts" "samples" "cleaned"
New-Item -ItemType Directory -Force -Path $samples | Out-Null

$catalog = Join-Path "artifacts" "cleaned" "catalog.json"
if (Test-Path $catalog) {
  Copy-Item -Path $catalog -Destination $samples -Force
}
$plays = Join-Path "artifacts" "cleaned" "plays"
if (Test-Path $plays) {
  Copy-Item -Path $plays -Destination $samples -Recurse -Force
}

Write-Host "Done. Output: artifacts/cleaned/"
