# Entornos: prueba vs publicación oficial

## Versión de respaldo (backup local en Git)

Si algo sale mal, puede volver a la versión estable del **3 jun 2025** (F5 ~2 s, consolidación y sesión liviana):

```powershell
cd "C:\Users\f1rac\OneDrive\Documents\Plan de choque"
git fetch --tags
git checkout v1.0-estable-2025-06-03
```

Para seguir trabajando desde ese punto en una rama:

```powershell
git checkout -b recuperacion-desde-estable v1.0-estable-2025-06-03
```

Para volver al desarrollo normal en `main`:

```powershell
git checkout main
```

Listar backups etiquetados:

```powershell
git tag -l "v*"
```

---

## Cómo tener ventana de prueba y app oficial

Streamlit Cloud permite **dos apps** con el **mismo repositorio** y **ramas distintas**:

| Entorno | Rama Git | URL típica | Uso |
|---------|----------|------------|-----|
| **Prueba** | `prueba` | `plan-de-choque-prueba.streamlit.app` (la elige al crear la app) | Probar cambios antes de publicar |
| **Oficial** | `main` | [plan-de-choque.streamlit.app](https://plan-de-choque.streamlit.app/) | Usuarios finales |

### Configuración única en Streamlit Cloud

1. Entre a [share.streamlit.io](https://share.streamlit.io) con su cuenta GitHub.
2. **App oficial** (ya existe): repositorio `plan-de-choque`, rama **`main`**, archivo `app.py`.
3. **App de prueba** (nueva):
   - **Create app** → mismo repositorio.
   - **Branch:** `prueba` (no `main`).
   - **Main file:** `app.py`.
   - Nombre sugerido: `plan-de-choque-prueba`.
4. **Secrets:** no se requiere contraseña de acceso ni de Matriz. Puede dejar Secrets vacío en oficial y prueba.

   La **Matriz** debe subirse **sin protección por contraseña** (desbloqueada en Excel).

Solo la app enlazada a `main` es la “oficial”; la de `prueba` no se actualiza hasta que usted suba cambios a esa rama.

### Flujo de trabajo recomendado

```text
Cambios en el PC
      │
      ▼
.\subir-a-prueba.ps1 "Describe el cambio"
      │  (sube a rama prueba → redeploy app de prueba)
      ▼
Probar en la URL de prueba (consolidación, F5, descargas)
      │
      ▼ ¿Todo bien?
.\subir-cambios.ps1 "Mismo cambio ya validado"
      │  (sube a main → redeploy app oficial)
      ▼
App pública actualizada (1–2 min)
```

### Crear la rama `prueba` en GitHub (una vez)

Si la rama aún no existe en el remoto:

```powershell
cd "C:\Users\f1rac\OneDrive\Documents\Plan de choque"
git push -u origin prueba
```

### Local

- Oficial local: `.\iniciar.ps1` (rama `main`).
- Probar otra rama: `git checkout prueba` y luego `.\iniciar.ps1`.

---

## Resumen

- **Backup:** etiqueta Git `v1.0-estable-2025-06-03` (punto seguro en el historial).
- **Prueba:** rama `prueba` + segunda app en Streamlit Cloud.
- **Oficial:** rama `main` + app actual en streamlit.app.

No hace falta duplicar el proyecto en carpetas; Git y dos despliegues en Cloud bastan.
