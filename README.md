# Plan de Choque

Consolidación **Matriz OXP** + **Contratos plan de choque** por localidad (Bogotá).

**App publicada:** [plan-de-choque.streamlit.app](https://plan-de-choque.streamlit.app/)

## Qué hace

1. Valida nombres de archivos y que la localidad coincida con la Matriz.
2. Cruza cada contrato con la Matriz y escribe el saldo del mes en Contratos y hojas de seguimiento.
3. Bloquea descargas si quedan contratos **sin resolver** (desempate manual obligatorio).

## Reglas de saldo (resumen)

| Situación | Comportamiento |
|-----------|----------------|
| Saldo del mes | Columna **Saldo Final (V)** en Matriz |
| Sin fila o saldo vacío en Matriz | Celda vacía (no 0) |
| Pestaña vacía / «NO TIENE» | No se modifica |
| Cruce principal | Nombre + contrato + año + apropiación |
| Si falla | Desempate por **Saldo Final** |

## Pantalla de resultados

- **Tarjetas:** localidades, contratos cruzados, CXP del mes, sin resolver.
- **Tabla por localidad:** una fila por localidad (asignados, pendientes, CXP).
- **Detalle:** solo localidades con sin resolver, fallback por Saldo Final o avisos en Suspendidos.
- **Desempate:** tabla y asistente cuando hay pendientes.

## Archivos de salida

- **Contratos actualizados** (ZIP, uno por localidad).
- **Globales:** consolidado, avance, tabla de resumen (cuando sin resolver = 0).

## Publicar (Streamlit Cloud)

1. Repositorio público en GitHub → [share.streamlit.io](https://share.streamlit.io) → `app.py` → Deploy.
2. No hace falta configurar Secrets de contraseña.
3. La **Matriz** debe subirse **sin contraseña** (desbloqueada en Excel antes de cargar).

## Prueba vs app oficial

- **Backup / volver atrás:** etiqueta Git `v1.0-estable-2025-06-03` (ver [ENTORNOS.md](ENTORNOS.md)).
- **Ventana de prueba:** segunda app en Streamlit Cloud con rama `prueba`; subir con `.\subir-a-prueba.ps1`.
- **Publicar oficial:** rama `main` con `.\subir-cambios.ps1` cuando la prueba esté validada.

## Actualizar el link publicado

```powershell
cd "C:\Users\f1rac\OneDrive\Documents\Plan de choque"
.\subir-cambios.ps1 "Descripcion del cambio"
```

## Uso local

```powershell
cd "ruta\al\proyecto"
.\iniciar.ps1
```

Abre `http://localhost:8501`.
