$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
if (-not (Test-Path data)) { New-Item -ItemType Directory data | Out-Null }
python -m uvicorn main:app --host 127.0.0.1 --port 8000
