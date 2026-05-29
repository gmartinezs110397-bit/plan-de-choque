# Plan de Choque

Consolidación **Matriz OXP** + **Contratos plan de choque** por localidad (Bogotá).

## Publicar para compartir un enlace (Streamlit Cloud)

1. Suba este proyecto a GitHub (repositorio **público**).
2. Entre en [share.streamlit.io](https://share.streamlit.io) con su cuenta de GitHub.
3. **Create app** → elija el repositorio → archivo principal: `app.py` → **Deploy**.
4. Copie el enlace que termina en `.streamlit.app` y envíelo; quien lo abra solo necesita el navegador.

La contraseña de la Matriz se ingresa en la app al consolidar; no se guarda en GitHub.

## Actualizar el link publico (despues de cambios en Cursor)

```powershell
cd "C:\Users\f1rac\OneDrive\Documents\Plan de choque"
.\subir-cambios.ps1 "Descripcion del cambio"
```

GitHub se actualiza y Streamlit Cloud redeploya en 1-2 min (mismo enlace `.streamlit.app`).

## Uso local

```powershell
cd "ruta\al\proyecto"
.\iniciar.ps1
```

Abre `http://localhost:8501` en su PC.
