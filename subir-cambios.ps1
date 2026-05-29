# Sube los cambios locales a GitHub (Streamlit Cloud se actualiza solo en 1-2 min)
Set-Location $PSScriptRoot

$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git no esta instalado. Instalelo desde https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}

$msg = $args[0]
if (-not $msg) {
    $msg = "Actualizacion $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
}

git add .
$status = git status --porcelain
if (-not $status) {
    Write-Host "No hay cambios para subir." -ForegroundColor Yellow
    exit 0
}

Write-Host "Archivos a subir:" -ForegroundColor Cyan
git status -s

$env:GIT_AUTHOR_NAME = "gmartinezs110397-bit"
$env:GIT_AUTHOR_EMAIL = "gmartinezs110397-bit@users.noreply.github.com"
$env:GIT_COMMITTER_NAME = $env:GIT_AUTHOR_NAME
$env:GIT_COMMITTER_EMAIL = $env:GIT_AUTHOR_EMAIL

git commit -m $msg
git push origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Listo. GitHub actualizado. Streamlit Cloud redeploya en 1-2 minutos." -ForegroundColor Green
    Write-Host "Repo: https://github.com/gmartinezs110397-bit/plan-de-choque" -ForegroundColor Gray
} else {
    Write-Host "Error al subir. Revise su sesion en GitHub." -ForegroundColor Red
}
