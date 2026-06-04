# Sube el estado actual a la rama "prueba" (ensayo en Streamlit Cloud; no toca main)
Set-Location $PSScriptRoot

$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git no esta instalado. Instalelo desde https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}

$msg = $args[0]
if (-not $msg) {
    $msg = "Prueba $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
}

$rama = git branch --show-current

git add .
$status = git status --porcelain
if ($status) {
    Write-Host "Archivos a confirmar:" -ForegroundColor Cyan
    git status -s
    $env:GIT_AUTHOR_NAME = "gmartinezs110397-bit"
    $env:GIT_AUTHOR_EMAIL = "gmartinezs110397-bit@users.noreply.github.com"
    $env:GIT_COMMITTER_NAME = $env:GIT_AUTHOR_NAME
    $env:GIT_COMMITTER_EMAIL = $env:GIT_AUTHOR_EMAIL
    git commit -m $msg
    if ($LASTEXITCODE -ne 0) { exit 1 }
} else {
    Write-Host "Sin cambios nuevos; se actualiza rama prueba al commit actual." -ForegroundColor Yellow
}

git branch -f prueba HEAD
git push -u origin prueba

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Listo. Rama 'prueba' en GitHub = commit actual." -ForegroundColor Green
    Write-Host "Rama local activa: $rama (sin cambiar)." -ForegroundColor Gray
    Write-Host "App OFICIAL (main): solo cambia con .\subir-cambios.ps1" -ForegroundColor Yellow
    Write-Host "Cree la app de ensayo en share.streamlit.io con rama 'prueba' (ver ENTORNOS.md)." -ForegroundColor Gray
} else {
    Write-Host "Error al subir. Revise su sesion en GitHub." -ForegroundColor Red
}
