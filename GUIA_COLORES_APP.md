# Guia de colores de la app

Fecha de referencia: 2026-06-05

Esta guia documenta solamente la apariencia de la app Streamlit (`app.py`).
No aplica a colores, estilos ni formatos de archivos Excel generados por la app.

## Version anterior: azul / neutral

Esta era la linea visual antes del cambio rosa/fucsia. Sirve como respaldo si algun dia se quiere regresar a un estilo mas institucional.

| Uso | Color |
| --- | --- |
| Texto principal | `#0f172a` |
| Texto secundario | `#64748b` |
| Labels / texto medio | `#475569` |
| Texto de archivos en cola | `#334155` |
| Bordes suaves | `#e2e8f0` |
| Bordes de inputs | `#cbd5e1` |
| Fondo uploaders | `#f8fafc` |
| Fondo hover uploaders | `#f9fbff` |
| Hover uploader / foco suave | `#93c5fd` |
| Accion primaria | `#2563eb` |
| Accion primaria hover | `#1d4ed8` |
| Accion primaria activa / indicador | `#1e40af` |
| Hover de select | `#dbeafe` |
| Opcion seleccionada select | `#eff6ff` |
| Descargas | `#059669` |
| Descargas hover | `#047857` |
| Archivo cargado correcto | `#16a34a` |
| Boton quitar texto | `#b91c1c` |
| Boton quitar borde | `#fecaca` |
| Boton quitar hover | `#fef2f2` |

## Version actual: rosa / fucsia

La version actual busca sentirse mas personal, femenina y calida, sin hacer la app menos legible. El fondo principal se mantiene blanco para que la interfaz no se vea cargada.

| Variable / uso | Color |
| --- | --- |
| Rosa muy suave para acentos | `#fff9fc` |
| Rosa suave para acentos | `#fff1f8` |
| Rosa claro | `#ffe4f1` |
| Borde rosa | `#fbcfe8` |
| Rosa medio | `#f9a8d4` |
| Fucsia principal | `#e0218a` |
| Fucsia hover | `#c2186a` |
| Fucsia oscuro | `#9d174d` |
| Texto principal calido | `#5b0a37` |
| Texto secundario calido | `#8a3a63` |

## Mensaje de bienvenida

Al ingresar con la contrasena correcta, la app muestra un mensaje corto y aleatorio.
Debe ser breve, amoroso y con tono de mujer a mujer para que se sienta como un detalle bonito, no como un paso extra del flujo.

Reglas actuales:

- Aparece despues de entrar con la contrasena correcta.
- Elige un mensaje al azar entre 24 opciones.
- Si la sesion sigue activa, evita repetir exactamente el ultimo mensaje.
- Muestra solo el mensaje corto, sin firma ni encabezado adicional.
- Se cierra con Enter, Esc, clic afuera, el boton de cartica con corazon o automaticamente despues de unos segundos.
- No modifica datos, archivos, Excel ni logica de consolidacion.

## Nota para cambios futuros

Si se quiere volver al estilo anterior, usar la seccion "Version anterior: azul / neutral" como referencia para reemplazar las variables CSS y estilos UI en `app.py`.
