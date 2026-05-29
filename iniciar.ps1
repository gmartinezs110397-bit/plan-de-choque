Set-Location $PSScriptRoot
if (Test-Path __pycache__) { Remove-Item -Recurse -Force __pycache__ }
Write-Host "Iniciando Plan de Choque..."
python -m streamlit run app.py
