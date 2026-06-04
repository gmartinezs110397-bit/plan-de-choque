from __future__ import annotations

import pickle
import re
import sys
import tempfile
import unicodedata
import uuid
import zipfile
from io import BytesIO
from datetime import datetime, date
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# Carpeta del proyecto primero (evita importar un cxp_cruce viejo en caché)
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

# Localidades de Bogotá D.C. (20), orden alfabético
LOCALIDADES = [
    "Antonio Nariño",
    "Barrios Unidos",
    "Bosa",
    "Chapinero",
    "Ciudad Bolívar",
    "Engativá",
    "Fontibón",
    "Kennedy",
    "La Candelaria",
    "Los Mártires",
    "Puente Aranda",
    "Rafael Uribe Uribe",
    "San Cristóbal",
    "Santa Fe",
    "Suba",
    "Sumapaz",
    "Teusaquillo",
    "Tunjuelito",
    "Usaquén",
    "Usme",
]

st.set_page_config(
    page_title="Plan de Choque",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    html, body, [class*="css"] {
        font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
    }
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 1.25rem; max-width: 960px; }

    /* Solo ocultar el texto «Press Enter…», no el icono del ojo */
    [data-testid="stFormSubmitInstruction"],
    div[data-testid="InputInstructions"] > span {
        display: none !important;
    }
    .st-key-portada_acceso_box [data-testid="stCheckbox"] label {
        white-space: nowrap !important;
    }
    .st-key-portada_acceso_box [data-testid="stCheckbox"] {
        margin: 0.15rem 0 0.65rem 0 !important;
    }
    .app-title {
        font-size: 2rem;
        font-weight: 700;
        color: #0f172a;
        letter-spacing: -0.03em;
        margin: 0 0 0.35rem 0;
        text-align: center;
    }
    .app-subtitle {
        text-align: center;
        color: #64748b;
        font-size: 0.95rem;
        margin: 0 0 1.75rem 0;
    }
    .form-card-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #0f172a;
        margin: 0 0 1.25rem 0;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid #e2e8f0;
    }
    .field-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.35rem;
    }
    .field-num {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.35rem;
        height: 1.35rem;
        background: #1e40af;
        color: white;
        border-radius: 50%;
        font-size: 0.72rem;
        font-weight: 700;
        margin-right: 0.5rem;
    }
    .file-ok { color: #16a34a; font-size: 0.85rem; font-weight: 500; }
    .section-title {
        font-size: 1rem;
        font-weight: 700;
        color: #0f172a;
        margin: 2rem 0 0.75rem;
        padding: 0.45rem 0.65rem;
        background: #FFD966;
        border-bottom: none;
        border-radius: 4px;
    }
    .metric-card {
        background: #fff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 0.85rem 0.75rem;
        min-height: 5.25rem;
        display: flex;
        flex-direction: column;
        justify-content: center;
        overflow: hidden;
    }
    .metric-label {
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #64748b;
        line-height: 1.25;
        margin-bottom: 0.35rem;
    }
    .metric-value {
        font-size: clamp(1rem, 2.4vw, 1.35rem);
        font-weight: 700;
        color: #0f172a;
        line-height: 1.15;
        white-space: nowrap;
    }
    .metric-value-sm { font-size: clamp(1.05rem, 2.6vw, 1.45rem); }

    /* Select localidad — borde y foco azul (#2563eb, igual que Ejecutar consolidación) */
    [class*="st-key-select_localidad"] [data-baseweb="select"] > div,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        border-color: #cbd5e1 !important;
        border-radius: 10px !important;
    }
    [class*="st-key-select_localidad"] [data-baseweb="select"]:focus-within > div,
    [class*="st-key-select_localidad"] [data-baseweb="select"]:hover > div,
    [data-testid="stSelectbox"] [data-baseweb="select"]:focus-within > div,
    [data-testid="stSelectbox"] [data-baseweb="select"]:hover > div {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 1px #2563eb !important;
    }
    div[data-baseweb="popover"] li[role="option"]:hover,
    div[data-baseweb="menu"] li[role="option"]:hover {
        background-color: #dbeafe !important;
    }
    div[data-baseweb="popover"] li[role="option"][aria-selected="true"],
    div[data-baseweb="menu"] li[role="option"][aria-selected="true"] {
        background-color: #eff6ff !important;
        color: #1e40af !important;
    }

    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }
    .loading-text { animation: pulse 1.5s ease-in-out infinite; color: #3b82f6; }

    /* Ejecutar consolidación — azul (selector por key de Streamlit) */
    .st-key-btn_ejecutar_consolidacion button {
        background: #2563eb !important;
        background-color: #2563eb !important;
        color: #ffffff !important;
        border: 1px solid #2563eb !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.35) !important;
    }
    .st-key-btn_ejecutar_consolidacion button:hover {
        background: #1d4ed8 !important;
        background-color: #1d4ed8 !important;
        color: #ffffff !important;
        border-color: #1d4ed8 !important;
    }
    .st-key-btn_ejecutar_consolidacion button:active {
        background: #1e40af !important;
        background-color: #1e40af !important;
    }
    .st-key-btn_ejecutar_consolidacion button p,
    .st-key-btn_ejecutar_consolidacion button span {
        color: #ffffff !important;
    }
    /* Quitar de cola — icono basura rojo centrado */
    div[class*="st-key-quitar_cola_"] button {
        position: relative !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background: transparent !important;
        background-color: transparent !important;
        border: 1px solid transparent !important;
        box-shadow: none !important;
        padding: 0.4rem !important;
        min-height: 2.35rem !important;
        min-width: 2.35rem !important;
    }
    div[class*="st-key-quitar_cola_"] button:hover {
        background: #fef2f2 !important;
        background-color: #fef2f2 !important;
        border-color: #fecaca !important;
    }
    div[class*="st-key-quitar_cola_"] button > div {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        min-height: 0 !important;
    }
    div[class*="st-key-quitar_cola_"] button p,
    div[class*="st-key-quitar_cola_"] button [data-testid="stMarkdownContainer"] {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        line-height: 0 !important;
    }
    div[class*="st-key-quitar_cola_"] button::before {
        content: "";
        position: absolute;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
        display: block;
        width: 1.35rem;
        height: 1.35rem;
        margin: 0;
        background-repeat: no-repeat;
        background-position: center;
        background-size: contain;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23dc2626'%3E%3Cpath d='M9 3h6a1 1 0 0 1 1 1v1h4a1 1 0 1 1 0 2h-1v13a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3V7H4a1 1 0 1 1 0-2h4V4a1 1 0 0 1 1-1zm1 2h4V4h-4v1zm-2 3v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V8H8zm3 3a1 1 0 1 1 2 0v7a1 1 0 1 1-2 0v-7zm4 0a1 1 0 1 1 2 0v7a1 1 0 1 1-2 0v-7z'/%3E%3C/svg%3E");
        pointer-events: none;
    }
    /* Descargas — verde UI (distinto del verde LIQUIDADO del Excel) */
    .st-key-btn_descargar_excel button,
    .st-key-dl_contratos_todas button {
        background: #059669 !important;
        background-color: #059669 !important;
        color: #ffffff !important;
        border: 1px solid #059669 !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
    }
    .st-key-btn_descargar_excel button:hover,
    .st-key-dl_contratos_todas button:hover {
        background: #047857 !important;
        background-color: #047857 !important;
        border-color: #047857 !important;
        color: #ffffff !important;
    }
    .st-key-btn_descargar_excel button p,
    .st-key-btn_descargar_excel button span,
    .st-key-dl_contratos_todas button p,
    .st-key-dl_contratos_todas button span {
        color: #ffffff !important;
    }
    .st-key-btn_descargar_excel button:disabled,
    .st-key-dl_contratos_todas button:disabled {
        background: #94a3b8 !important;
        background-color: #94a3b8 !important;
        border-color: #94a3b8 !important;
        color: #f8fafc !important;
        opacity: 0.65 !important;
        box-shadow: none !important;
        cursor: not-allowed !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

SHEET_MATRIZ = "MATRIZ OXP"
MATRIZ_HEADER_FILA = 6  # fila de encabezados en pandas (Excel fila 7)
FILA_INICIO_MATRIZ = 8  # columna A desde fila 8 en hoja MATRIZ OXP
SELECCION_LOCALIDAD = "Seleccione Localidad"
KW_CONTRATOS = "plan de choque"
KW_MATRIZ = "matriz"
PALABRAS_IGNORAR = {"de", "la", "los", "las", "el", "del", "y"}
ARCHIVO_AVANCE_BASE = "Avance plan de choque"
ARCHIVO_RESUMEN_BASE = "Tabla de resumen"
MESES_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def init_session_state():
    defaults = {
        "cola_localidades": [],
        "consolidated_df": None,
        "processed": False,
        "file_stats": [],
        "last_processed_at": None,
        "upload_key": 0,
        "abrir_dialogo": False,
        "pendiente_consolidacion": False,
        "consolidacion_en_curso": False,
        "ejecutar_consolidacion_ahora": False,
        "pwd_matriz": "",
        "cola_ejecucion": [],
        "error_ultima_ejecucion": None,
        "errores_ejecucion": [],
        "fecha_analisis": None,
        "cruce_informe": [],
        "cruce_detalle": [],
        "contratos_actualizados": {},
        "cruce_resumen_global": [],
        "titulo_saldo_corte": "",
        "desempate_wizard_idx": 0,
        "desempate_wizard_mapa": {},
        "acceso_autorizado": False,
        "reporte_ejecucion": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def contrasena_acceso_esperada() -> str | None:
    """Contraseña en .streamlit/secrets.toml (local) o Secrets de Streamlit Cloud."""
    try:
        if st.secrets.get("sin_contrasena_acceso") in (True, "true", "1", "yes", "si", "sí"):
            return None
        valor = st.secrets.get("contrasena_acceso")
        if valor is None:
            valor = st.secrets.get("codigo_acceso")
        if valor is None:
            return None
        texto = str(valor).strip()
        return texto if texto else None
    except Exception:
        return None


CLAVE_INPUT_CONTRASENA = "input_contrasena_portada"
CLAVE_VER_CONTRASENA = "ver_contrasena_portada"


def _componente_teclado_portada_acceso(clave_widget: str) -> None:
    """Foco y captura de teclas (components.html suele funcionar mejor que st.html en Cloud)."""
    selector = f".st-key-{clave_widget} input"
    caja = ".st-key-portada_acceso_box"
    components.html(
        f"""
        <script>
        (function () {{
          const selector = "{selector}";
          const caja = "{caja}";

          function documentos() {{
            const docs = [];
            const vistos = new Set();
            function agregar(doc) {{
              if (!doc || vistos.has(doc)) return;
              vistos.add(doc);
              docs.push(doc);
            }}
            agregar(document);
            try {{ agregar(window.parent.document); }} catch (err) {{}}
            try {{
              window.parent.document.querySelectorAll("iframe").forEach(function (f) {{
                try {{ agregar(f.contentDocument); }} catch (err) {{}}
              }});
            }} catch (err) {{}}
            return docs;
          }}

          function buscarInput() {{
            for (const doc of documentos()) {{
              let el = doc.querySelector(selector);
              if (el) return el;
              const box = doc.querySelector(caja);
              if (box) {{
                el = box.querySelector('[data-testid="stTextInput"] input');
                if (el) return el;
              }}
              const form = doc.querySelector('form[data-testid="stForm"]');
              if (form) {{
                el = form.querySelector("input");
                if (el) return el;
              }}
            }}
            return null;
          }}

          function configurar(el) {{
            if (!el || el.dataset.pcAcceso === "1") return;
            el.dataset.pcAcceso = "1";
            el.setAttribute("autofocus", "");
            el.setAttribute("inputmode", "numeric");
            el.setAttribute("autocomplete", "one-time-code");
          }}

          function enfocar() {{
            const el = buscarInput();
            if (!el) return false;
            configurar(el);
            try {{
              el.focus({{ preventScroll: true }});
              el.click();
            }} catch (err) {{}}
            return true;
          }}

          function insertarTexto(el, ch) {{
            const proto = window.HTMLInputElement.prototype;
            const desc = Object.getOwnPropertyDescriptor(proto, "value");
            const next = el.value + ch;
            if (desc && desc.set) desc.set.call(el, next);
            else el.value = next;
            try {{
              el.dispatchEvent(new InputEvent("input", {{
                bubbles: true,
                inputType: "insertText",
                data: ch,
              }}));
            }} catch (err) {{
              el.dispatchEvent(new Event("input", {{ bubbles: true }}));
            }}
          }}

          function activoEsOtroInput() {{
            const el = buscarInput();
            for (const doc of documentos()) {{
              const ae = doc.activeElement;
              if (!ae) continue;
              if (ae === el) return false;
              const tag = (ae.tagName || "").toUpperCase();
              if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
            }}
            return false;
          }}

          function manejarTecla(e) {{
            if (activoEsOtroInput()) return;
            const el = buscarInput();
            if (!el) return;
            if (e.ctrlKey || e.metaKey || e.altKey) return;
            if (e.key === "Tab" || e.key === "Escape" || e.key.startsWith("Arrow")) return;

            if (e.key === "Enter") {{
              for (const doc of documentos()) {{
                if (doc.activeElement === el) return;
              }}
              e.preventDefault();
              e.stopPropagation();
              enfocar();
              const form = el.closest("form");
              const btn = form && (
                form.querySelector('button[kind="primaryFormSubmit"]') ||
                form.querySelector('button[type="submit"]') ||
                form.querySelector("button")
              );
              if (btn) btn.click();
              return;
            }}

            if (e.key.length !== 1) return;
            e.preventDefault();
            e.stopPropagation();
            enfocar();
            insertarTexto(el, e.key);
          }}

          function vincular(doc) {{
            if (!doc || doc.documentElement.dataset.pcAccesoTeclas === "1") return;
            doc.documentElement.dataset.pcAccesoTeclas = "1";
            doc.addEventListener("keydown", manejarTecla, true);
          }}

          function iniciar() {{
            documentos().forEach(vincular);
            let intentos = 0;
            const timer = setInterval(function () {{
              enfocar();
              if (++intentos > 40) clearInterval(timer);
            }}, 50);
            try {{
              const obs = new MutationObserver(enfocar);
              obs.observe(window.parent.document.body, {{
                childList: true,
                subtree: true,
              }});
            }} catch (err) {{}}
          }}

          iniciar();
        }})();
        </script>
        """,
        height=0,
    )


def render_portada_acceso() -> None:
    """Pantalla de ingreso; detiene la app hasta contraseña correcta."""
    contrasena_ok = contrasena_acceso_esperada()
    st.markdown('<h1 class="app-title">Plan de Choque</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="app-subtitle">Ingrese la contraseña para continuar</p>',
        unsafe_allow_html=True,
    )

    with st.container(border=True, key="portada_acceso_box"):
        mostrar_texto = bool(st.session_state.get(CLAVE_VER_CONTRASENA, False))
        clase_campo = f".st-key-{CLAVE_INPUT_CONTRASENA}"
        st.markdown(
            f"""
            <style>
            .st-key-portada_acceso_box {clase_campo} input {{
                -webkit-text-security: {"none" if mostrar_texto else "disc"};
            }}
            div[data-testid="InputInstructions"] > span {{
                display: none !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
        with st.form(
            "form_contrasena_acceso",
            clear_on_submit=False,
            enter_to_submit=True,
        ):
            ingresado = st.text_input(
                "Contraseña",
                type="default",
                placeholder="Contraseña",
                key=CLAVE_INPUT_CONTRASENA,
                label_visibility="collapsed",
                autocomplete="one-time-code",
            )
            st.checkbox("Mostrar contraseña", key=CLAVE_VER_CONTRASENA)
            enviado = st.form_submit_button(
                "Entrar",
                type="primary",
                use_container_width=True,
            )
        _componente_teclado_portada_acceso(CLAVE_INPUT_CONTRASENA)

    if enviado:
        texto = str(st.session_state.get(CLAVE_INPUT_CONTRASENA, ingresado)).strip()
        if texto == contrasena_ok:
            st.session_state.acceso_autorizado = True
            st.rerun()
        st.session_state[CLAVE_INPUT_CONTRASENA] = ""
        st.error("Contraseña incorrecta.")
        st.rerun()

    st.stop()


init_session_state()


def mes_en_espanol(fecha: datetime | date) -> str:
    return MESES_ES[fecha.month - 1]


def mes_capitalizado(fecha: datetime | date) -> str:
    """Mes con primera letra en mayúscula: Mayo, Junio, …"""
    mes = mes_en_espanol(fecha)
    return mes[:1].upper() + mes[1:] if mes else mes


def formato_numero_metrica(valor: float) -> str:
    """Número compacto para tarjetas (sin salto de línea)."""
    n = int(round(valor))
    return f"{n:,}".replace(",", ".")


def formato_fecha_colombia(fecha: datetime | date, con_hora: bool = False) -> str:
    """Fecha legible en Colombia: día/mes/año."""
    if con_hora and isinstance(fecha, datetime):
        return fecha.strftime("%d/%m/%Y %H:%M")
    return fecha.strftime("%d/%m/%Y")


def parsear_fecha_flexible(
    valor,
    preferir_dia_primero: bool = True,
) -> datetime | None:
    """
    Interpreta fechas en texto o Excel.
    Por defecto asume formato colombiano (día/mes/año). Si día o mes > 12, infiere el orden.
    Ej.: 28/05/2026 → 28 may 2026 | 05/28/2026 (ambiguo) → con preferir_dia_primero falla 5/28;
    sin ambigüedad: 13/05/2026 siempre es 13 mayo.
    """
    if valor is None:
        return None
    if isinstance(valor, str) and not valor.strip():
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, date):
        return datetime(valor.year, valor.month, valor.day)
    if isinstance(valor, pd.Timestamp):
        return valor.to_pydatetime()

    texto = str(valor).strip().split()[0]
    if not texto or texto.lower() in {"nat", "none", "nan"}:
        return None

    match = re.match(
        r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})$",
        texto,
    )
    if match:
        p1, p2, anio = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if anio < 100:
            anio += 2000 if anio < 50 else 1900
        if p1 > 12:
            dia, mes = p1, p2
        elif p2 > 12:
            mes, dia = p1, p2
        elif preferir_dia_primero:
            dia, mes = p1, p2
        else:
            mes, dia = p1, p2
        try:
            return datetime(anio, mes, dia)
        except ValueError:
            return None

    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(texto, fmt)
        except ValueError:
            continue

    try:
        parsed = pd.to_datetime(valor, dayfirst=preferir_dia_primero, errors="coerce")
        if pd.notna(parsed):
            return parsed.to_pydatetime()
    except Exception:
        pass
    return None


def fecha_referencia_analisis() -> datetime:
    """Fecha del análisis (al consolidar); si no hay, usa la fecha actual."""
    guardada = st.session_state.get("fecha_analisis")
    if isinstance(guardada, datetime):
        return guardada
    if isinstance(guardada, str):
        parsed = parsear_fecha_flexible(guardada)
        if parsed:
            return parsed
    return datetime.now()


def sanitizar_nombre_archivo(nombre: str) -> str:
    """Quita caracteres no válidos en Windows."""
    for char in '<>:"/\\|?*':
        nombre = nombre.replace(char, "")
    return nombre.strip() or "salida.xlsx"


def localidades_en_nombre_archivo(localidades: list[str]) -> str:
    """Ej.: (Usaquén,Kennedy) — nombres originales, separados por coma."""
    limpias = []
    for loc in localidades:
        nombre = str(loc).strip()
        for char in '<>:"/\\|?*':
            nombre = nombre.replace(char, "")
        if nombre:
            limpias.append(nombre)
    if not limpias:
        return ""
    return f"({','.join(limpias)})"


def nombre_archivo_salida(
    base: str,
    fecha: datetime | date | None = None,
    localidades: list[str] | None = None,
) -> str:
    """
    Ej.: Avance plan de choque Mayo (Usaquén,Kennedy).xlsx
    Mes junto al nombre base; localidades con su nombre original entre paréntesis.
    """
    f = fecha or fecha_referencia_analisis()
    mes = mes_capitalizado(f)
    nombre = f"{base} {mes}"
    sufijo_loc = localidades_en_nombre_archivo(localidades or [])
    if sufijo_loc:
        nombre += f" {sufijo_loc}"
    nombre += ".xlsx"
    return sanitizar_nombre_archivo(nombre)


def _stem_descarga_contratos(stem: str, mes: str) -> str:
    """
    Si el archivo ya trae «… - Mayo», conserva lo anterior al último « - »
    y sustituye el tramo del mes (p. ej. «… - Junio»).
    Si no hay « - », añade « - {mes}» al final.
    """
    limpio = stem.replace("—", "-").replace("–", "-").strip()
    sep = " - "
    if sep in limpio:
        base, _viejo_mes = limpio.rsplit(sep, 1)
        return f"{base.strip()}{sep}{mes}"
    return f"{limpio} - {mes}"


def nombre_descarga_contratos_actualizado(
    localidad: str,
    nombre_original: str,
    fecha: datetime | date | None = None,
) -> str:
    """
    Nombre del Excel de Contratos actualizado por localidad.
    Ej.: «Contratos plan de choque Suba - Mayo» → «… Suba - Junio» al consolidar junio.
    """
    f = fecha or fecha_referencia_analisis()
    mes = mes_capitalizado(f)
    if nombre_original and str(nombre_original).strip():
        stem = Path(nombre_original).stem
    else:
        stem = f"Contratos plan de choque {localidad}"
    nombre = _stem_descarga_contratos(stem, mes) + ".xlsx"
    return sanitizar_nombre_archivo(nombre)


def _directorio_archivos_sesion() -> Path:
    """Guarda Excels en disco (no en session_state) para que F5 no reenvíe megabytes."""
    raiz = Path(tempfile.gettempdir()) / "plan_de_choque"
    raiz.mkdir(parents=True, exist_ok=True)
    sid = st.session_state.get("_pc_sid_archivos")
    if not sid:
        sid = uuid.uuid4().hex
        st.session_state._pc_sid_archivos = sid
    carpeta = raiz / str(sid)
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def bytes_archivo_cola(entrada: dict) -> bytes:
    """Lee bytes desde disco o desde entrada antigua que aún trae bytes en sesión."""
    if entrada.get("bytes") is not None:
        return entrada["bytes"]
    ruta = entrada.get("path")
    if ruta:
        p = Path(ruta)
        if p.is_file():
            return p.read_bytes()
    return b""


@st.cache_data(show_spinner=False)
def _leer_binario_desde_ruta(ruta: str, modificado: float) -> bytes:
    """Cache en memoria del servidor: F5 no vuelve a leer el ZIP del disco."""
    del modificado
    return Path(ruta).read_bytes()


def bytes_contratos_de_salida(data: dict) -> bytes:
    if data.get("bytes_contratos") is not None:
        return data["bytes_contratos"]
    ruta = data.get("path_contratos")
    if ruta and Path(ruta).is_file():
        return Path(ruta).read_bytes()
    return b""


_CLAVE_RUTA_DETALLE = "_pc_cruce_detalle_ruta"
_CLAVE_RUTA_REPORTE = "_pc_reporte_ejecucion_ruta"
_CLAVE_SNAPSHOT = "_pc_snapshot_consolidacion_ruta"
_CLAVE_MOSTRAR_RESULTADOS = "mostrar_resultados_completos"
_CLAVE_RESUMEN_LIGERO = "_pc_resumen_consolidado"
_ARCHIVO_META_DETALLE = "cruce_detalle_meta.pkl"
_PREFIJOS_WIDGET_ARCHIVO = (
    "uploader_contratos_",
    "uploader_matriz_",
    "select_localidad_",
)


def _guardar_contratos_en_disco(localidad: str, data: dict) -> dict:
    """Quita bytes_contratos de session_state (pesado en cada F5)."""
    if data.get("path_contratos") and data.get("bytes_contratos") is None:
        return data
    raw = data.get("bytes_contratos")
    if raw is None:
        return data
    carpeta = _directorio_archivos_sesion()
    base = sanitizar_nombre_archivo(
        data.get("nombre_contratos") or f"contratos_{localidad}.xlsx"
    )
    destino = carpeta / f"salida_{sanitizar_nombre_archivo(localidad)}_{base}"
    destino.write_bytes(raw)
    ligero = {k: v for k, v in data.items() if k != "bytes_contratos"}
    ligero["path_contratos"] = str(destino)
    return ligero


def _archivo_cola_en_disco(entrada: dict, localidad: str, tipo: str) -> dict:
    """Garantiza path en disco; si solo hay bytes en memoria, los persiste."""
    nombre = entrada.get("name") or f"{tipo}_{localidad}.xlsx"
    if entrada.get("path") and Path(entrada["path"]).is_file():
        return {"name": nombre, "path": entrada["path"]}
    datos = entrada.get("bytes")
    if datos:
        carpeta = _directorio_archivos_sesion()
        destino = carpeta / sanitizar_nombre_archivo(f"{tipo}_{localidad}_{nombre}")
        destino.write_bytes(datos)
        return {"name": nombre, "path": str(destino)}
    return {"name": nombre}


def _asegurar_cola_en_disco(cola: list) -> list:
    """Cola lista para procesar: cada Contratos/Matriz con archivo legible en disco."""
    refs = []
    for item in cola:
        loc = item["localidad"]
        refs.append({
            "localidad": loc,
            "contratos": _archivo_cola_en_disco(item.get("contratos") or {}, loc, "contratos"),
            "matriz": _archivo_cola_en_disco(item.get("matriz") or {}, loc, "matriz"),
        })
    return refs


def _validar_archivos_accesibles(cola: list) -> list[str]:
    errores = []
    for item in cola:
        loc = item["localidad"]
        for clave, etiqueta in (("contratos", "Contratos"), ("matriz", "Matriz")):
            ent = item.get(clave) or {}
            if not entrada_cola_tiene_archivo(ent):
                errores.append(f"**{loc}** — Falta el archivo de {etiqueta}.")
                continue
            if not bytes_archivo_cola(ent):
                errores.append(
                    f"**{loc}** — No se pudo leer {etiqueta} "
                    f"(`{ent.get('name', '')}`). Vuelva a subirlo a la cola."
                )
    return errores


def _es_ruta_meta_detalle(ruta: str) -> bool:
    return Path(ruta).name == _ARCHIVO_META_DETALLE


def _borrar_cruce_detalle_en_disco() -> None:
    ruta = st.session_state.pop(_CLAVE_RUTA_DETALLE, None)
    carpeta = _directorio_archivos_sesion()
    if ruta:
        try:
            Path(ruta).unlink(missing_ok=True)
        except OSError:
            pass
    for f in carpeta.glob("detalle_*.pkl"):
        try:
            f.unlink()
        except OSError:
            pass
    legacy = carpeta / "cruce_detalle.pkl"
    if legacy.is_file():
        try:
            legacy.unlink()
        except OSError:
            pass
    st.session_state.cruce_detalle = []


def _persistir_cruce_detalle(detalle: list) -> None:
    """Detalle en disco por localidad (F5 no carga todo si no hace falta)."""
    carpeta = _directorio_archivos_sesion()
    _borrar_cruce_detalle_en_disco()
    por_loc: dict[str, list] = {}
    for fila in detalle:
        loc = str(fila.get("Localidad") or "_sin_loc")
        por_loc.setdefault(loc, []).append(fila)
    indice: list[tuple[str, str]] = []
    for loc, rows in por_loc.items():
        ruta_loc = carpeta / sanitizar_nombre_archivo(f"detalle_{loc}.pkl")
        with open(ruta_loc, "wb") as f:
            pickle.dump(rows, f, protocol=4)
        indice.append((loc, str(ruta_loc)))
    meta = carpeta / _ARCHIVO_META_DETALLE
    with open(meta, "wb") as f:
        pickle.dump(indice, f, protocol=4)
    st.session_state[_CLAVE_RUTA_DETALLE] = str(meta)
    st.session_state.cruce_detalle = []


@st.cache_data(show_spinner=False)
def _cargar_cruce_detalle_cache(ruta: str, modificado: float) -> list:
    del modificado
    with open(ruta, "rb") as f:
        return pickle.load(f)


@st.cache_data(show_spinner=False)
def _cargar_indice_detalle_cache(ruta_meta: str, modificado: float) -> list[tuple[str, str]]:
    del modificado
    with open(ruta_meta, "rb") as f:
        return pickle.load(f)


@st.cache_data(show_spinner=False)
def _cargar_detalle_completo_desde_meta(ruta_meta: str, modificado: float) -> list:
    del modificado
    out: list = []
    for _loc, ruta in _cargar_indice_detalle_cache(
        ruta_meta, Path(ruta_meta).stat().st_mtime
    ):
        p = Path(ruta)
        if p.is_file():
            out.extend(_cargar_cruce_detalle_cache(str(p), p.stat().st_mtime))
    return out


def obtener_cruce_detalle_localidad(localidad: str) -> list:
    inline = st.session_state.get("cruce_detalle") or []
    if inline:
        return [d for d in inline if d.get("Localidad") == localidad]
    ruta = st.session_state.get(_CLAVE_RUTA_DETALLE)
    if not ruta or not Path(ruta).is_file():
        return []
    p = Path(ruta)
    if _es_ruta_meta_detalle(str(p)):
        for loc, ruta_loc in _cargar_indice_detalle_cache(str(p), p.stat().st_mtime):
            if loc == localidad:
                pl = Path(ruta_loc)
                if pl.is_file():
                    return list(_cargar_cruce_detalle_cache(str(pl), pl.stat().st_mtime))
        return []
    return [
        d
        for d in _cargar_cruce_detalle_cache(str(p), p.stat().st_mtime)
        if d.get("Localidad") == localidad
    ]


def obtener_cruce_detalle() -> list:
    inline = st.session_state.get("cruce_detalle") or []
    if inline:
        return list(inline)
    ruta = st.session_state.get(_CLAVE_RUTA_DETALLE)
    if not ruta or not Path(ruta).is_file():
        return []
    p = Path(ruta)
    if _es_ruta_meta_detalle(str(p)):
        return list(_cargar_detalle_completo_desde_meta(str(p), p.stat().st_mtime))
    return list(_cargar_cruce_detalle_cache(str(p), p.stat().st_mtime))


def informe_requiere_detalle_cruce(informe: list) -> bool:
    return any(_localidad_requiere_detalle_cruce(i) for i in informe)


def establecer_cruce_detalle(detalle: list) -> None:
    if not detalle:
        _borrar_cruce_detalle_en_disco()
        return
    _persistir_cruce_detalle(detalle)


def dataframe_consolidado():
    detalle = obtener_cruce_detalle()
    if not detalle:
        return pd.DataFrame()
    return pd.DataFrame(detalle)


def _purgar_uploaders_obsoletos() -> None:
    """Cada «Añadir a cola» deja Excels en claves viejas del file_uploader (F5 más lento)."""
    uk = int(st.session_state.get("upload_key", 0))
    for key in list(st.session_state.keys()):
        for pref in _PREFIJOS_WIDGET_ARCHIVO:
            if not key.startswith(pref):
                continue
            try:
                if int(key[len(pref) :]) != uk:
                    st.session_state.pop(key, None)
            except ValueError:
                pass


def _aligerar_sesion_archivos_pesados() -> None:
    """Migra sesiones viejas que guardaban ZIP/Excel como bytes (F5 muy lento)."""
    zip_info = st.session_state.get("zip_descarga_contratos")
    if zip_info and zip_info.get("data") and not zip_info.get("path"):
        carpeta = _directorio_archivos_sesion()
        nombre = zip_info.get("nombre") or "contratos.zip"
        ruta = carpeta / sanitizar_nombre_archivo(nombre)
        ruta.write_bytes(zip_info["data"])
        st.session_state.zip_descarga_contratos = {
            "path": str(ruta),
            "nombre": nombre,
            "mime": zip_info.get("mime", "application/zip"),
        }

    act = st.session_state.get("contratos_actualizados") or {}
    if act and any((d or {}).get("bytes_contratos") for d in act.values()):
        st.session_state.contratos_actualizados = {
            loc: _guardar_contratos_en_disco(loc, dict(datos))
            for loc, datos in act.items()
        }

    work = st.session_state.get("consolidacion_work")
    if work and work.get("cola"):
        work["cola"] = _asegurar_cola_en_disco(work["cola"])
        ca = work.get("contratos_actualizados") or {}
        if ca and any((d or {}).get("bytes_contratos") for d in ca.values()):
            for loc, datos in ca.items():
                work["contratos_actualizados"][loc] = _guardar_contratos_en_disco(
                    loc, dict(datos)
                )


def _resumen_ligero_desde_informe(informe: list) -> dict:
    return {
        "n_localidades": len(informe),
        "sin_resolver": sum(i.get("sin_resolver", 0) for i in informe),
        "total_contratos": sum(i.get("total_contratos", 0) for i in informe),
        "total_ok": sum(i.get("contratos_ok", 0) for i in informe),
        "cxp_total": sum(i.get("cxp_total", 0) for i in informe),
        "titulo_mes": st.session_state.get("titulo_saldo_corte", ""),
        "procesado_en": st.session_state.get("last_processed_at", ""),
    }


def _persistir_snapshot_consolidacion() -> None:
    """Informe y stats fuera de session_state (F5 liviano)."""
    informe = st.session_state.get("cruce_informe") or []
    if not informe and not st.session_state.get("processed"):
        return
    snapshot = {
        "informe": informe,
        "file_stats": st.session_state.get("file_stats") or [],
        "cruce_resumen_global": st.session_state.get("cruce_resumen_global") or [],
        "fecha_analisis": st.session_state.get("fecha_analisis"),
        "last_processed_at": st.session_state.get("last_processed_at"),
        "titulo_saldo_corte": st.session_state.get("titulo_saldo_corte", ""),
    }
    ruta = _directorio_archivos_sesion() / "consolidacion_snapshot.pkl"
    with open(ruta, "wb") as f:
        pickle.dump(snapshot, f, protocol=4)
    st.session_state[_CLAVE_SNAPSHOT] = str(ruta)
    st.session_state[_CLAVE_RESUMEN_LIGERO] = _resumen_ligero_desde_informe(informe)
    st.session_state.cruce_informe = []
    st.session_state.file_stats = []
    st.session_state.cruce_resumen_global = []


@st.cache_data(show_spinner=False)
def _cargar_snapshot_consolidacion_cache(ruta: str, modificado: float) -> dict:
    del modificado
    with open(ruta, "rb") as f:
        return pickle.load(f)


def _cargar_snapshot_consolidacion() -> dict:
    if st.session_state.get("cruce_informe"):
        return {
            "informe": st.session_state.get("cruce_informe") or [],
            "file_stats": st.session_state.get("file_stats") or [],
            "cruce_resumen_global": st.session_state.get("cruce_resumen_global") or [],
            "fecha_analisis": st.session_state.get("fecha_analisis"),
            "last_processed_at": st.session_state.get("last_processed_at"),
            "titulo_saldo_corte": st.session_state.get("titulo_saldo_corte", ""),
        }
    ruta = st.session_state.get(_CLAVE_SNAPSHOT)
    if ruta and Path(ruta).is_file():
        p = Path(ruta)
        return _cargar_snapshot_consolidacion_cache(str(p), p.stat().st_mtime)
    return {
        "informe": [],
        "file_stats": [],
        "cruce_resumen_global": [],
        "fecha_analisis": st.session_state.get("fecha_analisis"),
        "last_processed_at": st.session_state.get("last_processed_at"),
        "titulo_saldo_corte": st.session_state.get("titulo_saldo_corte", ""),
    }


def _informe_para_ui() -> list:
    inline = st.session_state.get("cruce_informe") or []
    if inline:
        return list(inline)
    return list(_cargar_snapshot_consolidacion().get("informe") or [])


def _stats_para_ui() -> list:
    inline = st.session_state.get("file_stats") or []
    if inline:
        return list(inline)
    return list(_cargar_snapshot_consolidacion().get("file_stats") or [])


def _resumen_global_para_ui() -> list:
    inline = st.session_state.get("cruce_resumen_global") or []
    if inline:
        return list(inline)
    return list(_cargar_snapshot_consolidacion().get("cruce_resumen_global") or [])


def _borrar_snapshot_consolidacion() -> None:
    ruta = st.session_state.pop(_CLAVE_SNAPSHOT, None)
    if ruta:
        try:
            Path(ruta).unlink(missing_ok=True)
        except OSError:
            pass
    st.session_state.pop(_CLAVE_RESUMEN_LIGERO, None)


def _externalizar_reporte_en_sesion() -> None:
    payload = st.session_state.get("reporte_ejecucion")
    if not payload or not payload.get("tabla"):
        return
    ruta = _directorio_archivos_sesion() / "reporte_ejecucion.pkl"
    with open(ruta, "wb") as f:
        pickle.dump(payload, f, protocol=4)
    st.session_state[_CLAVE_RUTA_REPORTE] = str(ruta)
    st.session_state.pop("reporte_ejecucion", None)


def _compactar_sesion_vista_completa() -> None:
    """Persistencia liviana sin cerrar el panel (rerun por descarga, desempate, etc.)."""
    if st.session_state.get("cruce_detalle"):
        _persistir_cruce_detalle(list(st.session_state.cruce_detalle))
    _aligerar_sesion_archivos_pesados()


def _compactar_sesion_para_f5() -> None:
    """Reduce lo que Streamlit serializa en cada recarga (F5) — vista resumen."""
    if st.session_state.get("cruce_detalle"):
        _persistir_cruce_detalle(list(st.session_state.cruce_detalle))
    if st.session_state.get("processed") and st.session_state.get("cruce_informe"):
        _persistir_snapshot_consolidacion()
    st.session_state.pop("consolidated_df", None)
    st.session_state[_CLAVE_MOSTRAR_RESULTADOS] = False
    _externalizar_reporte_en_sesion()
    _purgar_uploaders_obsoletos()
    _aligerar_sesion_archivos_pesados()


def entrada_cola_tiene_archivo(entrada: dict | None) -> bool:
    if not entrada:
        return False
    return bool(entrada.get("bytes") or entrada.get("path"))


def _regenerar_zip_descarga_contratos() -> None:
    """Genera el ZIP en disco; en sesión solo ruta + nombre (F5 liviano)."""
    contratos_act = st.session_state.get("contratos_actualizados") or {}
    if not contratos_act:
        st.session_state.pop("zip_descarga_contratos", None)
        return
    fecha_dl = st.session_state.get("fecha_analisis") or fecha_referencia_analisis()
    try:
        datos, nombre, mime = empaquetar_descarga_contratos(contratos_act, fecha_dl)
    except ValueError:
        st.session_state.pop("zip_descarga_contratos", None)
        return
    carpeta = _directorio_archivos_sesion()
    ruta = carpeta / sanitizar_nombre_archivo(nombre)
    ruta.write_bytes(datos)
    st.session_state.zip_descarga_contratos = {
        "path": str(ruta),
        "nombre": nombre,
        "mime": mime,
    }


def _vaciar_cola_tras_consolidar() -> None:
    """Libera memoria y acelera recargas; los resultados ya quedaron en la consolidación."""
    for item in st.session_state.get("cola_localidades", []):
        _borrar_archivo_cola_en_disco(item.get("contratos"))
        _borrar_archivo_cola_en_disco(item.get("matriz"))
    st.session_state.cola_localidades = []
    st.session_state.cola_ejecucion = []
    st.session_state.upload_key = int(st.session_state.get("upload_key", 0)) + 1


def empaquetar_descarga_contratos(
    contratos_actualizados: dict,
    fecha: datetime | date | None = None,
) -> tuple[bytes, str, str]:
    """
    Siempre ZIP: evita archivos .xlsx corruptos al descargar directo en Mac/Safari.
    Cada Excel dentro conserva su nombre original + «- {Mes}».
    """
    f = fecha or fecha_referencia_analisis()
    items = sorted(contratos_actualizados.items(), key=lambda x: x[0])
    if not items:
        raise ValueError("No hay contratos actualizados para descargar.")

    localidades = [loc for loc, _ in items]
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for loc, data in items:
            nombre = nombre_descarga_contratos_actualizado(
                loc, data.get("nombre_contratos", ""), f
            )
            zf.writestr(nombre, bytes_contratos_de_salida(data))
    buf.seek(0)
    mes = mes_capitalizado(f)
    zip_nombre = sanitizar_nombre_archivo(
        f"Contratos plan de choque actualizados {mes} "
        f"{localidades_en_nombre_archivo(localidades)}.zip"
    )
    return buf.getvalue(), zip_nombre, "application/zip"


# Etiquetas fijas (mismas que METODOS_LABEL en cxp_cruce); no importar pandas aquí al arranque.
METODOS_SIN_RESOLVER = frozenset({"Sin resolver", "Sin fila en matriz"})


def filas_sin_resolver(detalle: list) -> list[dict]:
    return [d for d in detalle if d.get("Método") in METODOS_SIN_RESOLVER]


def incidencias_sin_resolver(detalle: list) -> list[dict]:
    """Contratos pendientes, ordenados para el asistente de desempate."""
    return sorted(
        filas_sin_resolver(detalle),
        key=lambda f: (
            str(f.get("Localidad") or ""),
            str(f.get("NOMBRE CONTRATISTA") or "").lower(),
            str(f.get("No. de Cto") or ""),
        ),
    )


def _reset_estado_desempate_wizard() -> None:
    st.session_state.desempate_wizard_idx = 0
    st.session_state.desempate_wizard_mapa = {}


def dataframe_resumen_localidades(informe: list) -> pd.DataFrame:
    """Vista compacta: una fila por localidad."""
    if not informe:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "Localidad": loc["localidad"],
                "Asignados": f"{loc.get('contratos_ok', 0)}/{loc.get('total_contratos', 0)}",
                "Sin resolver": loc.get("sin_resolver", 0),
                "CXP (mes)": loc.get("cxp_total", 0),
                "Columna": loc.get("columna_mes", ""),
            }
            for loc in informe
        ]
    )


def _localidad_requiere_detalle_cruce(loc_info: dict) -> bool:
    """Detalle por localidad solo si hay excepciones o avisos."""
    return (
        loc_info.get("sin_resolver", 0) > 0
        or loc_info.get("conteo", {}).get("match_saldo_contrato", 0) > 0
        or bool(loc_info.get("advertencias_suspendidos"))
    )


def mostrar_informe_cruce_consolidado(
    informe: list,
    titulo_mes: str,
    *,
    cargar_tablas_detalle: bool = True,
) -> None:
    """Resumen conciso del cruce; tablas de fallback solo si hace falta."""
    total_contratos = sum(i.get("total_contratos", 0) for i in informe)
    total_ok = sum(i.get("contratos_ok", 0) for i in informe)

    st.markdown(
        '<p class="section-title">Resumen del cruce</p>',
        unsafe_allow_html=True,
    )
    st.caption(
        f"Saldo del mes desde **Saldo Final (V)** en Matriz → columna **{titulo_mes}** "
        f"en Contratos y hojas de seguimiento."
    )

    resumen_global = st.session_state.get("cruce_resumen_global", [])
    if resumen_global:
        df_rg = pd.DataFrame(resumen_global)
        total_rg = int(df_rg["Contratos"].sum())
        c1, c2 = st.columns([2, 1])
        with c1:
            st.dataframe(df_rg, use_container_width=True, hide_index=True)
        with c2:
            st.markdown(
                f"**{total_rg}** de **{total_contratos}** contratos "
                f"con saldo asignado en **{titulo_mes}**."
            )
            if total_ok != total_rg:
                st.caption(
                    f"({total_ok} filas actualizadas en Contratos; "
                    f"incluye verificaciones y vacíos en matriz.)"
                )

    df_loc = dataframe_resumen_localidades(informe)
    if len(df_loc):
        st.dataframe(df_loc, use_container_width=True, hide_index=True)

    with st.expander("Reglas de cruce (referencia)", expanded=False):
        st.markdown(
            "- **Clave principal:** nombre + contrato + año + apropiación (k4).\n"
            "- **Si falla k4:** nombre + contrato + año; desempate por **Saldo Final** "
            "(columna junto a liberaciones/fenecimientos).\n"
            "- **Sin fila o saldo vacío en Matriz:** celda vacía (no cero).\n"
            "- **Pestañas vacías / «NO TIENE»:** no se modifican."
        )

    locales_detalle = [loc for loc in informe if _localidad_requiere_detalle_cruce(loc)]
    if not locales_detalle:
        return
    st.markdown("**Detalle por localidad**")
    for loc_info in locales_detalle:
        loc = loc_info["localidad"]
        sin_loc = loc_info.get("sin_resolver", 0)
        fallback = loc_info.get("conteo", {}).get("match_saldo_contrato", 0)
        avisos = loc_info.get("advertencias_suspendidos") or []
        etiqueta = (
            f"{loc} — {sin_loc} sin resolver"
            if sin_loc
            else f"{loc} — {fallback} por Saldo Final"
            if fallback
            else loc
        )
        with st.expander(etiqueta, expanded=sin_loc > 0):
            if avisos:
                for aviso in avisos:
                    st.warning(aviso)
            st.caption(
                f"Columna «{loc_info['columna_mes']}» — {loc_info['accion_columna']}"
            )
            if loc_info.get("resumen_metodos"):
                st.dataframe(
                    pd.DataFrame(loc_info["resumen_metodos"]),
                    use_container_width=True,
                    hide_index=True,
                )
            detalle_loc = []
            if cargar_tablas_detalle:
                detalle_loc = [
                    d
                    for d in obtener_cruce_detalle_localidad(loc)
                    if d.get("Método") == METODOS_LABEL["match_saldo_contrato"]
                ]
            if detalle_loc:
                st.markdown(
                    "**Fallback por Saldo Final** — la apropiación en Contratos no coincide "
                    "con la Matriz; se tomó la fila cuyo saldo coincide."
                )
                cols = [
                    "NOMBRE CONTRATISTA",
                    "No. de Cto",
                    "APROPIACION DISPONIBLE",
                    "SALDO FINAL (Contratos)",
                    f"Saldo Matriz ({titulo_mes})",
                    "Detalle",
                ]
                st.dataframe(
                    pd.DataFrame(detalle_loc)[cols],
                    use_container_width=True,
                    hide_index=True,
                )


def resumen_sin_resolver_por_localidad(detalle: list) -> pd.DataFrame:
    """Conteo de pendientes por localidad."""
    conteo: dict[str, int] = {}
    for fila in filas_sin_resolver(detalle):
        loc = fila.get("Localidad") or "—"
        conteo[loc] = conteo.get(loc, 0) + 1
    if not conteo:
        return pd.DataFrame(columns=["Localidad", "Sin resolver"])
    return pd.DataFrame(
        [{"Localidad": loc, "Sin resolver": n} for loc, n in sorted(conteo.items())]
    )


def dataframe_sin_resolver(detalle: list) -> pd.DataFrame:
    """Solo columnas útiles para revisar excepciones."""
    filas = filas_sin_resolver(detalle)
    if not filas:
        return pd.DataFrame()
    df = pd.DataFrame(filas)
    preferidas = [
        "Localidad",
        "NOMBRE CONTRATISTA",
        "No. de Cto",
        "AÑO SUSCRIPCIÓN",
        "APROPIACION DISPONIBLE",
        "SALDO FINAL (Contratos)",
        "Método",
        "Detalle",
    ]
    cols_matriz = [c for c in df.columns if str(c).startswith("Saldo Matriz")]
    cols = [c for c in preferidas if c in df.columns] + cols_matriz
    resto = [c for c in df.columns if c not in cols]
    return df[cols + resto]


def aplicar_mapa_desempate(mapa: dict[str, float]) -> tuple[bool, list[str]]:
    """Aplica saldos elegidos a Contratos y actualiza el estado de la consolidación."""
    detalle = list(obtener_cruce_detalle())
    contratos_act = dict(st.session_state.get("contratos_actualizados", {}))
    fecha = st.session_state.get("fecha_analisis") or fecha_referencia_analisis()
    titulo_mes = titulo_saldo_corte(fecha)
    snap = _cargar_snapshot_consolidacion()
    informe = list(snap.get("informe") or [])

    localidades_con_pendientes = {
        loc
        for loc in contratos_act
        if claves_pendientes_localidad(detalle, loc)
    }
    if not localidades_con_pendientes:
        return False, ["No hay contratos pendientes de desempate."]

    errores: list[str] = []
    for loc in sorted(localidades_con_pendientes):
        pendientes = claves_pendientes_localidad(detalle, loc)
        faltan = validar_desempate_completo(
            pendientes,
            mapa,
            [f for f in detalle if f.get("Localidad") == loc],
        )
        if faltan:
            errores.extend([f"**{loc}**: {msg}" for msg in faltan])

    if errores:
        return False, errores

    for loc in sorted(localidades_con_pendientes):
        bytes_nuevos, detalle = aplicar_desempate_en_contratos(
            bytes_contratos_de_salida(contratos_act[loc]),
            fecha,
            mapa,
            detalle,
            loc,
        )
        contratos_act[loc]["bytes_contratos"] = bytes_nuevos
        contratos_act[loc] = _guardar_contratos_en_disco(loc, contratos_act[loc])
        stats_loc = recalcular_estadisticas_localidad(
            [f for f in detalle if f.get("Localidad") == loc],
            titulo_mes,
        )
        contratos_act[loc].update(stats_loc)
        for i, info in enumerate(informe):
            if info["localidad"] == loc:
                informe[i] = {**info, **stats_loc}
                break

    establecer_cruce_detalle(detalle)
    st.session_state.contratos_actualizados = contratos_act

    conteo_global: dict[str, int] = {}
    for info in informe:
        _agregar_conteo_global(conteo_global, info.get("conteo", {}))
    resumen_global = [
        {
            "Método": METODOS_LABEL.get(codigo, codigo),
            "Contratos": cantidad,
        }
        for codigo, cantidad in sorted(conteo_global.items(), key=lambda x: -x[1])
        if cantidad > 0
    ]

    file_stats = list(snap.get("file_stats") or _stats_para_ui())
    for s in file_stats:
        if s.get("Archivo") == "Contratos (Cps por depurar)":
            loc = s.get("Localidad")
            info = next((i for i in informe if i["localidad"] == loc), None)
            if info:
                s["CXP (suma mes)"] = info["cxp_total"]

    st.session_state.cruce_informe = informe
    st.session_state.file_stats = file_stats
    st.session_state.cruce_resumen_global = resumen_global
    _persistir_snapshot_consolidacion()

    _reset_estado_desempate_wizard()
    st.session_state.zip_descarga_listo = False
    _regenerar_zip_descarga_contratos()
    return True, []


def render_asistente_desempate(detalle: list, titulo_mes: str) -> None:
    """Asistente paso a paso: una incidencia, opciones Matriz con radio, aplicar al final."""
    incidencias = incidencias_sin_resolver(detalle)
    if not incidencias:
        return

    mapa: dict[str, float] = dict(st.session_state.get("desempate_wizard_mapa", {}))
    n = len(incidencias)
    idx = int(st.session_state.get("desempate_wizard_idx", 0))
    idx = max(0, min(idx, n - 1))
    st.session_state.desempate_wizard_idx = idx

    claves_todas = {clave_desde_detalle(inc) for inc in incidencias}
    resueltas = len(claves_todas & set(mapa.keys()))
    st.progress(
        resueltas / n if n else 0.0,
        text=f"{resueltas} de {n} incidencias con saldo elegido",
    )

    inc = incidencias[idx]
    clave = clave_desde_detalle(inc)
    loc = inc.get("Localidad") or "—"

    saldo_asignar = mapa.get(clave)
    texto_saldo = (
        formato_numero_metrica(saldo_asignar) if saldo_asignar is not None else "—"
    )
    st.markdown(
        f'<p style="font-size:1.05rem;margin:0.25rem 0 0.5rem;">'
        f'<strong>Incidencia {idx + 1} de {n}</strong>'
        f' · Localidad: <strong>{loc}</strong></p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="font-size:1.2rem;margin:0.5rem 0 1rem;">'
        f"<strong>Saldo a asignar en {titulo_mes}:</strong> "
        f'<span style="color:#1e40af;font-weight:700;">{texto_saldo}</span></p>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown("**Contratos plan de choque**")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Contratista:** {inc.get('NOMBRE CONTRATISTA', '—')}")
            st.markdown(f"**No. de contrato:** {inc.get('No. de Cto', '—')}")
        with c2:
            ap = inc.get("APROPIACION DISPONIBLE")
            sf = inc.get("SALDO FINAL (Contratos)")
            st.markdown(
                f"**Apropiación:** {formato_numero_metrica(float(ap)) if ap is not None else '—'}"
            )
            st.markdown(
                f"**SALDO FINAL:** {formato_numero_metrica(float(sf)) if sf is not None else '—'}"
            )
        if inc.get("Detalle"):
            st.caption(inc.get("Detalle"))

    candidatos = inc.get("candidatos_matriz") or []
    st.markdown("**Opciones en Matriz** (elija una)")
    if candidatos:
        labels: list[str] = []
        valores: list[float] = []
        for cand in candidatos:
            ap = formato_numero_metrica(float(cand.get("apropiacion") or 0))
            sal = formato_numero_metrica(float(cand.get("saldo") or 0))
            labels.append(
                f"Opción {cand.get('opcion')} — Apropiación {ap} — {titulo_mes}: {sal}"
            )
            valores.append(float(cand["saldo"]))

        default_idx = None
        if clave in mapa:
            for i, val in enumerate(valores):
                if val == mapa[clave]:
                    default_idx = i
                    break

        eleccion = st.radio(
            "Línea de Matriz que corresponde",
            options=list(range(len(labels))),
            format_func=lambda i, lbls=labels: lbls[i],
            index=default_idx,
            key=f"wiz_radio_{clave}",
            label_visibility="collapsed",
        )
        if eleccion is not None:
            mapa[clave] = valores[eleccion]
    else:
        st.warning(
            inc.get("Detalle")
            or "No hay filas candidatas en Matriz. Indique el saldo manualmente."
        )
        previo = float(mapa[clave]) if clave in mapa else 0.0
        manual = st.number_input(
            f"Saldo para {titulo_mes}",
            min_value=0.0,
            value=previo,
            step=1.0,
            format="%d",
            key=f"wiz_num_{clave}",
        )
        mapa[clave] = float(manual)

    st.session_state.desempate_wizard_mapa = mapa

    nav_prev, nav_next = st.columns(2)
    with nav_prev:
        if st.button("← Anterior", disabled=idx == 0, use_container_width=True):
            st.session_state.desempate_wizard_idx = idx - 1
            st.rerun()
    with nav_next:
        etiqueta_next = "Siguiente →" if idx < n - 1 else "Fin del listado"
        if st.button(etiqueta_next, disabled=idx >= n - 1, use_container_width=True):
            if clave not in mapa:
                st.warning("Elija una opción de Matriz antes de continuar.")
            else:
                st.session_state.desempate_wizard_idx = idx + 1
                st.rerun()

    completo = claves_todas <= set(mapa.keys())
    faltan = n - len(claves_todas & set(mapa.keys()))
    st.markdown("---")
    if completo:
        st.success(
            f"Las **{n}** incidencias tienen saldo asignado. "
            "Puede aplicar los cambios y desbloquear las descargas."
        )
    else:
        st.info(f"Faltan **{faltan}** incidencia(s) por confirmar (use **Siguiente →**).")

    if st.button(
        "Aplicar desempates y desbloquear descargas",
        type="primary",
        use_container_width=True,
        disabled=not completo,
        key="btn_aplicar_desempate_wizard",
    ):
        ok, msgs = aplicar_mapa_desempate(mapa)
        if ok:
            st.success("Desempates aplicados. Ya puede descargar Contratos y archivos globales.")
            st.rerun()
        else:
            for msg in msgs:
                st.error(msg)


def consolidacion_lista_para_descarga() -> bool:
    """True si no hay pendientes sin resolver."""
    resumen = st.session_state.get(_CLAVE_RESUMEN_LIGERO)
    if resumen is not None:
        return int(resumen.get("sin_resolver", 0)) == 0
    informe = _informe_para_ui()
    return sum(i.get("sin_resolver", 0) for i in informe) == 0


def normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def palabras_localidad(localidad: str) -> list[str]:
    palabras = re.findall(r"[a-z0-9]+", normalizar(localidad))
    significativas = [p for p in palabras if p not in PALABRAS_IGNORAR and len(p) >= 2]
    return significativas if significativas else palabras


def contiene_palabra_localidad(texto: str, localidad: str) -> bool:
    texto_norm = normalizar(texto)
    return any(palabra in texto_norm for palabra in palabras_localidad(localidad))


def verificar_lectura_matriz(libro: BytesIO) -> None:
    """Comprueba que el Excel desbloqueado tiene la hoja MATRIZ OXP."""
    libro.seek(0)
    pd.read_excel(libro, sheet_name=SHEET_MATRIZ, nrows=1, engine="openpyxl")
    libro.seek(0)


def abrir_matriz_excel(file_bytes: bytes, password: str, nombre_archivo: str = "") -> BytesIO:
    """
    Abre la Matriz (nunca Contratos).
    - Si está protegida: usa la contraseña (obligatoria y debe ser correcta).
    - Si no está protegida: abre sin contraseña.
    """
    pwd = str(password).strip() if password else ""
    etiqueta = f"Matriz **{nombre_archivo}**" if nombre_archivo else "Matriz"
    raw = BytesIO(file_bytes)
    office = msoffcrypto.OfficeFile(raw)

    if office.is_encrypted():
        if not pwd:
            raise ValueError("Ingrese la contraseña de la Matriz.")
        dec = BytesIO()
        raw.seek(0)
        try:
            office.load_key(password=pwd)
            office.decrypt(dec)
        except (ms_exceptions.InvalidKeyError, ms_exceptions.DecryptionError):
            raise ValueError("Contraseña incorrecta.") from None
        try:
            verificar_lectura_matriz(dec)
        except Exception:
            raise ValueError("Contraseña incorrecta.") from None
        dec.seek(0)
        return dec

    raw.seek(0)
    try:
        verificar_lectura_matriz(raw)
    except Exception as e:
        raise ValueError(f"{etiqueta}: no se pudo leer ({e})") from e
    raw.seek(0)
    return BytesIO(file_bytes)


def _bytes_matriz_sin_reguardar(file_bytes: bytes, password: str) -> BytesIO:
    """Abre la Matriz sin pasar por openpyxl.save (preserva caché de fórmulas en col. V)."""
    raw = BytesIO(file_bytes)
    office = msoffcrypto.OfficeFile(raw)
    if office.is_encrypted():
        pwd = str(password).strip() if password else ""
        if not pwd:
            raise ValueError("Ingrese la contraseña de la Matriz.")
        dec = BytesIO()
        raw.seek(0)
        try:
            office.load_key(password=pwd)
            office.decrypt(dec)
        except (ms_exceptions.InvalidKeyError, ms_exceptions.DecryptionError):
            raise ValueError("Contraseña incorrecta.") from None
        dec.seek(0)
        return dec
    return BytesIO(file_bytes)


def _cuenta_celdas_numericas(valores: list) -> int:
    n = 0
    for v in valores:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            continue
        try:
            float(v)
            n += 1
        except (TypeError, ValueError):
            continue
    return n


def _indices_saldo_final_calculado(ws, fila_hdr: int) -> tuple[int, int, int] | None:
    """Columnas Apropiación − Giros − Liberación/Fenecimiento (= fórmula Saldo Final)."""
    col_a = col_g = col_l = None
    for c in range(1, (ws.max_column or 0) + 1):
        titulo = ws.cell(fila_hdr, c).value
        if titulo is None:
            continue
        n = normalizar(str(titulo))
        if n == "apropiacion":
            col_a = c
        elif n == "giros":
            col_g = c
        elif "liberacion" in n or "fenecimiento" in n:
            col_l = c
    if col_a and col_g and col_l:
        return col_a, col_g, col_l
    return None


def _saldo_final_desde_dataframe(df: pd.DataFrame) -> pd.Series | None:
    """Apropiación − Giros − Liberación desde columnas ya cargadas (rápido)."""
    col_a = col_g = col_l = None
    for c in df.columns:
        n = normalizar(str(c))
        if n == "apropiacion":
            col_a = c
        elif n == "giros":
            col_g = c
        elif "liberacion" in n or "fenecimiento" in n:
            col_l = c
    if not (col_a and col_g and col_l):
        return None
    a = pd.to_numeric(df[col_a], errors="coerce").fillna(0)
    g = pd.to_numeric(df[col_g], errors="coerce").fillna(0)
    lib = pd.to_numeric(df[col_l], errors="coerce").fillna(0)
    return a - g - lib


def _calcular_saldo_final_matriz_ws(ws, fila_hdr: int) -> list:
    cols = _indices_saldo_final_calculado(ws, fila_hdr)
    if not cols:
        return []
    col_a, col_g, col_l = cols
    max_r = ws.max_row or fila_hdr
    filas: list = []
    for a_val, g_val, l_val in zip(
        ws.iter_rows(
            min_row=fila_hdr + 1,
            max_row=max_r,
            min_col=col_a,
            max_col=col_a,
            values_only=True,
        ),
        ws.iter_rows(
            min_row=fila_hdr + 1,
            max_row=max_r,
            min_col=col_g,
            max_col=col_g,
            values_only=True,
        ),
        ws.iter_rows(
            min_row=fila_hdr + 1,
            max_row=max_r,
            min_col=col_l,
            max_col=col_l,
            values_only=True,
        ),
    ):
        try:
            filas.append(
                float((a_val[0] if a_val else None) or 0)
                - float((g_val[0] if g_val else None) or 0)
                - float((l_val[0] if l_val else None) or 0)
            )
        except (TypeError, ValueError):
            filas.append(None)
    return filas


def _columna_matriz_data_only(
    libro: BytesIO,
    header: int,
    nombre_columna: str,
) -> list:
    """
    Valores de «Saldo Final» en MATRIZ OXP (data_only).
    Si la caché de fórmulas está vacía (p. ej. tras guardar sin abrir en Excel),
    calcula Apropiación − Giros − Liberación/Fenecimiento.
    """
    from openpyxl import load_workbook

    if header is None:
        return []

    libro.seek(0)
    wb = load_workbook(libro, read_only=True, data_only=True)
    try:
        ws = wb[SHEET_MATRIZ]
        fila_hdr = int(header) + 1
        col_idx = None
        objetivo = normalizar(nombre_columna)
        for c in range(1, (ws.max_column or 0) + 1):
            titulo = ws.cell(fila_hdr, c).value
            if titulo is not None and normalizar(str(titulo)) == objetivo:
                col_idx = c
                break
        valores: list = []
        if col_idx is not None:
            max_r = ws.max_row or fila_hdr
            valores = [
                row[0]
                for row in ws.iter_rows(
                    min_row=fila_hdr + 1,
                    max_row=max_r,
                    min_col=col_idx,
                    max_col=col_idx,
                    values_only=True,
                )
            ]
        umbral = max(3, int(len(valores) * 0.01)) if valores else 3
        if _cuenta_celdas_numericas(valores) < umbral:
            calculados = _calcular_saldo_final_matriz_ws(ws, fila_hdr)
            if _cuenta_celdas_numericas(calculados) > _cuenta_celdas_numericas(valores):
                return calculados
        return valores
    finally:
        wb.close()


def leer_hoja_matriz(
    file_bytes: bytes,
    password: str,
    nombre_archivo: str = "",
    *,
    avance: callable | None = None,
    **kwargs,
) -> pd.DataFrame:
    """Lee la hoja MATRIZ OXP; detecta contraseña incorrecta."""
    try:
        header_pd = kwargs.get("header", MATRIZ_HEADER_FILA)
        # Sin openpyxl.save: preserva caché de fórmulas en Saldo Final (col. V).
        valores_saldo: list = []
        if avance:
            avance("Matriz · abrir")
        libro = _bytes_matriz_sin_reguardar(file_bytes, password)
        if avance:
            avance("Matriz · leer hoja")
        df = pd.read_excel(
            libro, sheet_name=SHEET_MATRIZ, engine="openpyxl", **kwargs
        )
        if header_pd is not None:
            candidatos = ("Saldo Final", "SALDO FINAL", "Saldo final")
            col_df = next((c for c in candidatos if c in df.columns), None)
            if col_df:
                if avance:
                    avance("Matriz · Saldo Final")
                n = len(df)
                serie = pd.to_numeric(df[col_df], errors="coerce")
                umbral = max(3, int(n * 0.01))
                if int(serie.notna().sum()) < umbral:
                    calc_df = _saldo_final_desde_dataframe(df)
                    if calc_df is not None and int(calc_df.notna().sum()) > int(
                        serie.notna().sum()
                    ):
                        serie = calc_df
                    else:
                        libro.seek(0)
                        valores_saldo = _columna_matriz_data_only(
                            libro, header_pd, "Saldo Final"
                        )
                        serie = pd.to_numeric(
                            pd.Series(valores_saldo[:n]), errors="coerce"
                        )
                        if len(valores_saldo) < n:
                            serie = pd.concat(
                                [
                                    serie,
                                    pd.Series([pd.NA] * (n - len(valores_saldo))),
                                ],
                                ignore_index=True,
                            )
                df = df.copy()
                df[col_df] = serie
        return df
    except ValueError:
        raise
    except Exception as e:
        err = str(e).lower()
        if "zip" in err or "bad magic" in err or "not a zip" in err:
            raise ValueError("Contraseña incorrecta.") from e
        raise ValueError(f"No se pudo leer la hoja {SHEET_MATRIZ}: {e}") from e


def es_error_contrasena(mensaje: str) -> bool:
    m = normalizar(mensaje)
    return "contrasena incorrecta" in m or "ingrese la contrasena" in m


def _probar_contrasena_matriz(
    file_bytes: bytes, password: str, nombre_archivo: str = ""
) -> None:
    """Valida contraseña sin re-guardar el Excel (evita lectura lenta duplicada)."""
    try:
        libro = _bytes_matriz_sin_reguardar(file_bytes, password)
        libro.seek(0)
        pd.read_excel(
            libro, sheet_name=SHEET_MATRIZ, engine="openpyxl", nrows=1
        )
    except ValueError:
        raise
    except Exception as e:
        err = str(e).lower()
        if "zip" in err or "bad magic" in err or "not a zip" in err:
            raise ValueError("Contraseña incorrecta.") from e
        etiqueta = f"Matriz **{nombre_archivo}**" if nombre_archivo else "Matriz"
        raise ValueError(f"{etiqueta}: no se pudo abrir ({e})") from e


def _valores_columna_a_matriz(file_bytes: bytes, password: str) -> list[str]:
    """Columna A desde fila 8 (solo validación de localidad)."""
    from openpyxl import load_workbook

    libro = _bytes_matriz_sin_reguardar(file_bytes, password)
    libro.seek(0)
    wb = load_workbook(libro, read_only=True, data_only=True)
    try:
        ws = wb[SHEET_MATRIZ]
        return [
            str(ws.cell(r, 1).value or "").strip()
            for r in range(FILA_INICIO_MATRIZ, (ws.max_row or FILA_INICIO_MATRIZ) + 1)
            if ws.cell(r, 1).value is not None and str(ws.cell(r, 1).value).strip()
        ]
    finally:
        wb.close()


def texto_localidad_en_matriz(file_bytes: bytes, password: str, nombre_archivo: str = "") -> str:
    """Lee columna A desde fila 8 en MATRIZ OXP."""
    del nombre_archivo
    return " ".join(_valores_columna_a_matriz(file_bytes, password))


def validar_nombre_contratos(nombre_archivo: str, localidad: str) -> tuple[bool, str]:
    nombre = normalizar(nombre_archivo)
    if KW_CONTRATOS not in nombre:
        return False, f"Contratos: falta «{KW_CONTRATOS}» en **{nombre_archivo}**"
    if not contiene_palabra_localidad(nombre_archivo, localidad):
        return False, (
            f"Contratos: **{nombre_archivo}** no incluye ninguna palabra de la localidad "
            f"**{localidad}**"
        )
    return True, ""


def validar_nombre_matriz(nombre_archivo: str) -> tuple[bool, str]:
    if KW_MATRIZ not in normalizar(nombre_archivo):
        return False, f"Matriz: falta «{KW_MATRIZ}» en el nombre **{nombre_archivo}**"
    return True, ""


def validar_localidad_en_hoja_matriz(
    file_bytes: bytes, password: str, localidad: str, nombre_archivo: str
) -> tuple[bool, str]:
    try:
        texto = texto_localidad_en_matriz(file_bytes, password, nombre_archivo)
    except ValueError as e:
        return False, f"**{localidad}** — Matriz **{nombre_archivo}**: {e}"
    except Exception as e:
        return False, f"**{localidad}** — Matriz **{nombre_archivo}**: no se pudo abrir ({e})"

    if not texto.strip():
        return (
            False,
            f"Matriz **{nombre_archivo}**: no se encontró localidad en columna A "
            f"(desde fila {FILA_INICIO_MATRIZ}) en **{SHEET_MATRIZ}**",
        )
    if not contiene_palabra_localidad(texto, localidad):
        return (
            False,
            f"Matriz **{nombre_archivo}**: en **{SHEET_MATRIZ}** (col. A, fila {FILA_INICIO_MATRIZ}+) "
            f"no coincide con la localidad **{localidad}**",
        )
    return True, ""


def validar_contrasena_matrices(cola: list, password_matriz: str) -> tuple[bool, list[str]]:
    """Prueba la contraseña únicamente en los bytes del archivo Matriz."""
    errores = []
    for item in cola:
        loc = item["localidad"]
        nm = item["matriz"]["name"]
        try:
            _probar_contrasena_matriz(
                bytes_archivo_cola(item["matriz"]),
                password_matriz,
                item["matriz"]["name"],
            )
        except ValueError as e:
            errores.append(f"**{loc}** — Matriz **{nm}**: {e}")
        except Exception as e:
            errores.append(f"**{loc}** — Matriz **{nm}**: {e}")
    return len(errores) == 0, errores


def _validar_nombres_en_cola(
    cola: list,
    password_matriz: str,
    *,
    verificar_texto_localidad: bool = True,
) -> tuple[bool, list[str]]:
    errores: list[str] = []
    for item in cola:
        loc = item["localidad"]
        nc = item["contratos"]["name"]
        nm = item["matriz"]["name"]

        ok_c, msg_c = validar_nombre_contratos(nc, loc)
        if not ok_c:
            errores.append(f"**{loc}** — {msg_c}")

        ok_nm, msg_nm = validar_nombre_matriz(nm)
        if not ok_nm:
            errores.append(f"**{loc}** — {msg_nm}")
        elif verificar_texto_localidad:
            ok_m, msg_m = validar_localidad_en_hoja_matriz(
                bytes_archivo_cola(item["matriz"]), password_matriz, loc, nm
            )
            if not ok_m:
                errores.append(f"**{loc}** — {msg_m}")

    return len(errores) == 0, errores


def validar_cola_archivos(
    cola: list,
    password_matriz: str,
    *,
    verificar_texto_localidad: bool = True,
) -> tuple[bool, list[str]]:
    errores = list(_validar_archivos_accesibles(cola))
    if errores:
        return False, errores

    pwd_ok, errores_pwd = validar_contrasena_matrices(cola, password_matriz)
    if not pwd_ok:
        return False, errores_pwd

    return _validar_nombres_en_cola(
        cola,
        password_matriz,
        verificar_texto_localidad=verificar_texto_localidad,
    )


def file_to_buffer(uploaded_file) -> dict:
    data = uploaded_file.getvalue()
    carpeta = _directorio_archivos_sesion()
    destino = carpeta / sanitizar_nombre_archivo(uploaded_file.name)
    destino.write_bytes(data)
    return {"path": str(destino), "name": uploaded_file.name}


def buffer_to_file(entry: dict):
    return BytesIO(bytes_archivo_cola(entry))


def read_contratos(file_like, name: str, localidad: str):
    try:
        df = pd.read_excel(file_like)
        df = df.copy()
        df["Localidad"] = localidad
        df["Tipo archivo"] = "Contratos plan de choque"
        df["Archivo origen"] = name
        return df
    except Exception as e:
        st.error(f"No se pudo leer Contratos (**{name}**): {e}")
        return None


def read_matriz(file_bytes: bytes, password: str, name: str, localidad: str):
    try:
        df = leer_hoja_matriz(file_bytes, password, name)
    except ValueError as e:
        st.session_state.error_ultima_ejecucion = str(e)
        return None
    except Exception as e:
        st.session_state.error_ultima_ejecucion = f"No se pudo leer Matriz ({name}): {e}"
        return None

    df = df.copy()
    df["Localidad"] = localidad
    df["Tipo archivo"] = "Matriz"
    df["Archivo origen"] = name
    return df


def generate_excel_bytes(dataframe: pd.DataFrame, sheet_name: str = "Datos") -> BytesIO:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        dataframe.to_excel(writer, index=False, sheet_name=sheet_name)
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        fmt = workbook.add_format({
            "bold": True, "text_wrap": True, "valign": "top",
            "border": 1, "bg_color": "#1e40af", "font_color": "#ffffff",
        })
        for col_num, value in enumerate(dataframe.columns.values):
            worksheet.write(0, col_num, value, fmt)
            worksheet.set_column(col_num, col_num, 18)
    output.seek(0)
    return output


def localidades_analizadas(stats: list) -> list[str]:
    return sorted({s["Localidad"] for s in stats if s.get("Localidad")})


def construir_avance_plan_de_choque(
    consolidated_df: pd.DataFrame, stats: list, fecha: datetime
) -> pd.DataFrame:
    """Contenido de Avance plan de choque — pendiente reglas de negocio."""
    localidades = localidades_analizadas(stats)
    return pd.DataFrame({
        "Campo": [
            "Archivo",
            "Mes de análisis",
            "Fecha de análisis",
            "Cantidad de localidades",
            "Registros en consolidado",
            "Estado",
        ],
        "Valor": [
            nombre_archivo_salida(ARCHIVO_AVANCE_BASE, fecha, localidades).replace(
                ".xlsx", ""
            ),
            mes_en_espanol(fecha),
            formato_fecha_colombia(fecha, con_hora=True),
            len(localidades),
            len(consolidated_df) if consolidated_df is not None else 0,
            (
                "Pendiente definir análisis de avance "
                "(consolidará Matriz + Contratos actualizados por localidad)"
            ),
        ],
    })


def construir_tabla_resumen(
    consolidated_df: pd.DataFrame, stats: list, fecha: datetime
) -> pd.DataFrame:
    """Tabla de resumen con metadatos y cruce CXP."""
    localidades = localidades_analizadas(stats)
    titulo_mes = titulo_saldo_corte(fecha)
    meta = pd.DataFrame({
        "Campo": [
            "Mes de análisis",
            "Fecha de análisis",
            "Columna en Contratos plan de choque",
            "Cantidad de localidades",
            "Fuentes consolidadas",
        ],
        "Valor": [
            mes_capitalizado(fecha),
            formato_fecha_colombia(fecha, con_hora=True),
            titulo_mes,
            len(localidades),
            "Por localidad: Matriz + Contratos plan de choque actualizados",
        ],
    })
    partes = [meta]
    informe = st.session_state.get("cruce_informe") or []
    if informe:
        partes.append(
            pd.DataFrame([{"Campo": "— Localidades (resumen) —", "Valor": ""}])
        )
        df_loc = dataframe_resumen_localidades(informe)
        partes.append(
            pd.DataFrame(
                [
                    {
                        "Campo": row["Localidad"],
                        "Valor": (
                            f"{row['Asignados']} asignados · "
                            f"sin resolver {row['Sin resolver']} · "
                            f"CXP {row['CXP (mes)']:,.0f} · {row['Columna']}"
                        ),
                    }
                    for _, row in df_loc.iterrows()
                ]
            )
        )
    resumen_global = st.session_state.get("cruce_resumen_global") or []
    if resumen_global:
        partes.append(
            pd.DataFrame([{"Campo": "— Métodos de cruce (global) —", "Valor": ""}])
        )
        rg = pd.DataFrame(resumen_global)
        rg.columns = ["Campo", "Valor"]
        partes.append(rg)
    contratos_act = st.session_state.get("contratos_actualizados") or {}
    stats_por_loc = {}
    for s in stats:
        loc = s.get("Localidad")
        if not loc:
            continue
        stats_por_loc.setdefault(loc, []).append(s)

    for loc_info in informe:
        loc = loc_info["localidad"]
        if not _localidad_requiere_detalle_cruce(loc_info):
            continue
        filas_loc = stats_por_loc.get(loc, [])
        matriz_nombre = next(
            (s.get("Nombre") for s in filas_loc if s.get("Archivo") == "Matriz"), ""
        )
        contratos_orig = next(
            (s.get("Nombre") for s in filas_loc if "Contratos" in str(s.get("Archivo", ""))),
            "",
        )
        data_cto = contratos_act.get(loc, {})
        contratos_gen = nombre_descarga_contratos_actualizado(
            loc,
            data_cto.get("nombre_contratos") or contratos_orig,
            fecha,
        )
        partes.append(
            pd.DataFrame([
                {
                    "Campo": f"— Detalle {loc} —",
                    "Valor": (
                        f"{loc_info['contratos_ok']}/{loc_info['total_contratos']} asignados · "
                        f"sin resolver {loc_info['sin_resolver']}"
                    ),
                },
                {"Campo": "Matriz (origen)", "Valor": matriz_nombre or "—"},
                {"Campo": "Contratos (origen)", "Valor": contratos_orig or "—"},
                {"Campo": "Contratos (actualizado)", "Valor": contratos_gen},
            ])
        )
        if loc_info.get("resumen_metodos"):
            lm = pd.DataFrame(loc_info["resumen_metodos"])
            lm.columns = ["Campo", "Valor"]
            partes.append(lm)

    if informe and stats_por_loc:
        partes.append(pd.DataFrame([{"Campo": "— Archivos origen —", "Valor": ""}]))
        for loc_info in informe:
            loc = loc_info["localidad"]
            filas_loc = stats_por_loc.get(loc, [])
            matriz_nombre = next(
                (s.get("Nombre") for s in filas_loc if s.get("Archivo") == "Matriz"), "—"
            )
            contratos_orig = next(
                (s.get("Nombre") for s in filas_loc if "Contratos" in str(s.get("Archivo", ""))),
                "—",
            )
            partes.append(
                pd.DataFrame([
                    {
                        "Campo": loc,
                        "Valor": f"Matriz: {matriz_nombre} | Contratos: {contratos_orig}",
                    }
                ])
            )
    detalle = obtener_cruce_detalle()
    filas_sr = filas_sin_resolver(detalle)
    if filas_sr and consolidacion_lista_para_descarga():
        partes.append(
            pd.DataFrame([{"Campo": "— Contratos sin resolver (histórico) —", "Valor": len(filas_sr)}])
        )
    elif filas_sr:
        partes.append(
            pd.DataFrame([
                {
                    "Campo": "— Contratos sin resolver (pendientes) —",
                    "Valor": (
                        f"{len(filas_sr)} — complete el desempate manual antes de exportar globales"
                    ),
                }
            ])
        )

    if stats:
        partes.append(pd.DataFrame([{"Campo": "— Archivos —", "Valor": ""}]))
        partes.append(pd.DataFrame(stats))
    if len(partes) > 1:
        return pd.concat(partes, ignore_index=True, sort=False)
    return pd.DataFrame({
        "Nota": [
            "Pendiente definir Tabla de resumen",
            f"Mes: {mes_en_espanol(fecha)}",
            f"Registros en consolidado: {len(consolidated_df) if consolidated_df is not None else 0}",
        ],
    })


def carpeta_descargas() -> Path:
    """Carpeta Descargas del usuario (Windows en español o inglés)."""
    home = Path.home()
    for nombre in ("Downloads", "Descargas"):
        carpeta = home / nombre
        if carpeta.is_dir():
            return carpeta
    return home


def guardar_archivos_salida(
    consolidated_df: pd.DataFrame, stats: list
) -> list[Path]:
    """
    Guarda siempre 2 archivos en Descargas.
    El nombre incluye mes del análisis y cada localidad, p. ej.:
    - Avance plan de choque Mayo (Usaquén,Kennedy).xlsx
    - Tabla de resumen Mayo (Usaquén,Kennedy).xlsx
    """
    if not stats and (consolidated_df is None or consolidated_df.empty):
        raise ValueError("No hay datos consolidados para exportar.")

    fecha = fecha_referencia_analisis()
    localidades = localidades_analizadas(stats)
    carpeta = carpeta_descargas()
    df_avance = construir_avance_plan_de_choque(consolidated_df, stats, fecha)
    df_resumen = construir_tabla_resumen(consolidated_df, stats, fecha)

    salidas = [
        (
            nombre_archivo_salida(ARCHIVO_AVANCE_BASE, fecha, localidades),
            df_avance,
            "Avance",
        ),
        (
            nombre_archivo_salida(ARCHIVO_RESUMEN_BASE, fecha, localidades),
            df_resumen,
            "Resumen",
        ),
    ]

    rutas = []
    for nombre, df_salida, hoja in salidas:
        ruta = carpeta / nombre
        ruta.write_bytes(generate_excel_bytes(df_salida, sheet_name=hoja).getvalue())
        rutas.append(ruta)

    return rutas


def formulario_completo(localidad, contratos, matriz) -> bool:
    return (
        bool(localidad)
        and localidad != SELECCION_LOCALIDAD
        and contratos is not None
        and matriz is not None
    )


def entrada_desde_formulario(localidad, contratos, matriz) -> dict:
    return {
        "localidad": localidad,
        "contratos": file_to_buffer(contratos),
        "matriz": file_to_buffer(matriz),
    }


def item_tiene_contratos_y_matriz(item: dict) -> bool:
    tiene_c = entrada_cola_tiene_archivo(item.get("contratos"))
    tiene_m = entrada_cola_tiene_archivo(item.get("matriz"))
    return tiene_c and tiene_m


def validar_archivos_en_cola(cola: list) -> tuple[bool, list[str]]:
    errores = []
    for item in cola:
        loc = item.get("localidad", "Localidad")
        if not entrada_cola_tiene_archivo(item.get("contratos")):
            errores.append(f"**{loc}** — Falta el archivo de Contratos plan de choque.")
        if not entrada_cola_tiene_archivo(item.get("matriz")):
            errores.append(f"**{loc}** — Falta el archivo de Matriz.")
    return len(errores) == 0, errores


def cola_para_ejecutar(cola: list) -> list:
    """Ítems de la cola con Contratos y Matriz listos para consolidar."""
    return [i for i in cola if item_tiene_contratos_y_matriz(i)]


def puede_ejecutar_cola(cola: list) -> bool:
    """La cola tiene al menos un consolidado completo."""
    return bool(cola) and all(item_tiene_contratos_y_matriz(i) for i in cola)


def _borrar_archivo_cola_en_disco(entrada: dict | None) -> None:
    if not entrada:
        return
    ruta = entrada.get("path")
    if not ruta:
        return
    try:
        Path(ruta).unlink(missing_ok=True)
    except OSError:
        pass


def quitar_de_cola(localidad: str) -> None:
    for item in st.session_state.cola_localidades:
        if item.get("localidad") == localidad:
            _borrar_archivo_cola_en_disco(item.get("contratos"))
            _borrar_archivo_cola_en_disco(item.get("matriz"))
    st.session_state.cola_localidades = [
        i for i in st.session_state.cola_localidades if i["localidad"] != localidad
    ]


def limpiar_resultado_consolidado():
    st.session_state.processed = False
    st.session_state.pop("consolidated_df", None)
    st.session_state.file_stats = []
    st.session_state.last_processed_at = None
    st.session_state.error_ultima_ejecucion = None
    st.session_state.errores_ejecucion = []
    st.session_state.fecha_analisis = None
    st.session_state.cruce_informe = []
    _borrar_cruce_detalle_en_disco()
    _borrar_snapshot_consolidacion()
    st.session_state.pop(_CLAVE_MOSTRAR_RESULTADOS, None)
    st.session_state.contratos_actualizados = {}
    st.session_state.cruce_resumen_global = []
    st.session_state.titulo_saldo_corte = ""
    st.session_state.pop("consolidacion_work", None)
    st.session_state.pop("zip_descarga_contratos", None)
    st.session_state.pop("zip_descarga_listo", None)
    st.session_state.pop(_CLAVE_RUTA_REPORTE, None)
    st.session_state.pop("reporte_ejecucion", None)
    _reset_estado_desempate_wizard()


def _agregar_conteo_global(acumulado: dict, conteo: dict) -> None:
    for codigo, cantidad in conteo.items():
        acumulado[codigo] = acumulado.get(codigo, 0) + cantidad


def _guardar_reporte_en_sesion(reporte: ReporteEjecucion) -> None:
    if not reporte.tiene_casos():
        st.session_state.pop("reporte_ejecucion", None)
        st.session_state.pop(_CLAVE_RUTA_REPORTE, None)
        return
    df = reporte.a_dataframe()
    payload = {
        "texto": reporte.generar_texto(),
        "tabla": df.to_dict("records"),
        "resumen": reporte.resumen,
        "generado": datetime.now().isoformat(timespec="seconds"),
    }
    ruta = _directorio_archivos_sesion() / "reporte_ejecucion.pkl"
    with open(ruta, "wb") as f:
        pickle.dump(payload, f, protocol=4)
    st.session_state[_CLAVE_RUTA_REPORTE] = str(ruta)
    st.session_state.pop("reporte_ejecucion", None)


def _cargar_reporte_ejecucion() -> dict | None:
    legacy = st.session_state.get("reporte_ejecucion")
    if legacy and legacy.get("tabla"):
        return legacy
    ruta = st.session_state.get(_CLAVE_RUTA_REPORTE)
    if ruta and Path(ruta).is_file():
        with open(ruta, "rb") as f:
            return pickle.load(f)
    return None


def mostrar_reporte_tecnico_admin() -> None:
    """Solo casos no previstos del sistema (para quien mantiene el código)."""
    payload = _cargar_reporte_ejecucion()
    if not payload or not payload.get("tabla"):
        return

    with st.expander("Casos no previstos (para soporte técnico)", expanded=False):
        st.caption(payload.get("resumen", ""))
        nombre_archivo = (
            f"casos_no_previstos_{payload.get('generado', 'ejecucion')}.txt"
        ).replace(":", "-")

        st.download_button(
            "Descargar reporte (.txt)",
            data=payload.get("texto", ""),
            file_name=nombre_archivo,
            mime="text/plain",
            key="dl_reporte_casos_no_previstos",
            use_container_width=True,
        )
        st.dataframe(
            pd.DataFrame(payload["tabla"]),
            use_container_width=True,
            hide_index=True,
        )


# Barra por pasos iguales (más movimiento visible); texto: localidad + fase.
_PASOS_VALIDACION = 4
_PASOS_POR_LOCALIDAD = 14  # 3 Matriz + 9 Cruce/Excel + 2 cierre


def _barra_nueva(num_localidades: int) -> dict:
    n = max(int(num_localidades), 1)
    return {"paso": 0, "total": _PASOS_VALIDACION + n * _PASOS_POR_LOCALIDAD}


def _texto_fase_barra(
    fase: str,
    localidad: str | None = None,
    indice: int = 0,
    total: int = 0,
) -> str:
    if localidad and total:
        return f"{localidad} ({indice + 1}/{total}) · {fase}"
    if localidad:
        return f"{localidad} · {fase}"
    return fase


def _barra_tick(
    barra: dict,
    progress,
    fase: str,
    *,
    localidad: str | None = None,
    indice: int = 0,
    total: int = 0,
) -> None:
    barra["paso"] = int(barra.get("paso", 0)) + 1
    valor = barra["paso"] / max(int(barra.get("total", 1)), 1)
    _actualizar_barra_progreso(
        progress,
        min(valor, 1.0),
        _texto_fase_barra(fase, localidad, indice, total),
    )


def _actualizar_barra_progreso(progress, valor: float, texto: str) -> None:
    """Actualiza la barra (sin bloquear la ejecución en Streamlit Cloud)."""
    if progress is None:
        return
    progress.progress(min(max(valor, 0.0), 1.0), text=texto)


def _omitir_formulario_entrada() -> bool:
    """Solo durante un run activo (Continuar o paso siguiente), no al abrir la página."""
    return bool(st.session_state.get("ejecutar_consolidacion_ahora"))


def _sanear_sesion_consolidacion() -> None:
    """Evita quedar colgado si la sesión quedó a medias tras F5 o un cierre."""
    if st.session_state.get("consolidacion_work") and not st.session_state.get(
        "ejecutar_consolidacion_ahora"
    ):
        st.session_state.consolidacion_en_curso = False
        st.session_state.pendiente_consolidacion = False
    if st.session_state.get("pendiente_consolidacion") and not st.session_state.get(
        "ejecutar_consolidacion_ahora"
    ):
        st.session_state.pendiente_consolidacion = False


def _reporte_con_casos_guardados(casos: list) -> ReporteEjecucion:
    reporte = ReporteEjecucion()
    for datos in casos:
        reporte.casos.append(CasoNoPrevisto(**datos))
    return reporte


def _procesar_localidad_en_work(
    work: dict,
    item: dict,
    reporte: ReporteEjecucion,
    progress,
    indice: int,
    total: int,
) -> None:
    """Cruza una localidad y acumula el resultado en work."""
    pwd = work["pwd"]
    ahora = work["ahora"]
    titulo_mes = work["titulo_mes"]
    localidad = item["localidad"]
    barra = work["_barra"]

    def tick(fase: str) -> None:
        _barra_tick(
            barra,
            progress,
            fase,
            localidad=localidad,
            indice=indice,
            total=total,
        )

    try:
        df_matriz = leer_hoja_matriz(
            bytes_archivo_cola(item["matriz"]),
            pwd,
            item["matriz"]["name"],
            header=MATRIZ_HEADER_FILA,
            avance=tick,
        )
    except ValueError as e:
        work["errores"].append(f"**{localidad}** — Matriz: {e}")
        reporte.desde_excepcion(
            e,
            localidad=localidad,
            archivo=item["matriz"]["name"],
            fase="lectura_matriz",
        )
        return
    except Exception as e:
        work["errores"].append(f"**{localidad}** — Matriz: no se pudo leer ({e})")
        reporte.desde_excepcion(
            e,
            localidad=localidad,
            archivo=item["matriz"]["name"],
            fase="lectura_matriz",
        )
        return

    try:
        resultado = procesar_localidad_cxp(
            bytes_archivo_cola(item["contratos"]),
            df_matriz,
            localidad,
            ahora,
            item["contratos"]["name"],
            item["matriz"]["name"],
            avance=tick,
        )
    except ValueError as e:
        work["errores"].append(f"**{localidad}** — Contratos: {e}")
        reporte.desde_excepcion(
            e,
            localidad=localidad,
            archivo=item["contratos"]["name"],
            fase="procesamiento_contratos",
        )
        return
    except Exception as e:
        work["errores"].append(
            f"**{localidad}** — Contratos: no se pudo procesar ({e})"
        )
        reporte.desde_excepcion(
            e,
            localidad=localidad,
            archivo=item["contratos"]["name"],
            fase="procesamiento_contratos",
        )
        return

    tick("Excel · aplicado")
    registrar_resultado_localidad(reporte, item, resultado)
    _agregar_conteo_global(work["conteo_global"], resultado["conteo"])
    work["informe_localidades"].append({
        "localidad": localidad,
        "columna_mes": resultado["columna_mes"],
        "accion_columna": resultado["accion_columna"],
        "total_contratos": resultado["total_contratos"],
        "contratos_ok": resultado["contratos_ok"],
        "sin_resolver": resultado["sin_resolver"],
        "cxp_total": resultado["cxp_total"],
        "resumen_metodos": resultado["resumen_metodos"],
        "conteo": resultado["conteo"],
        "advertencias_suspendidos": resultado.get("advertencias_suspendidos", []),
    })
    work["detalle_global"].extend(resultado["detalle"])
    work["contratos_actualizados"][localidad] = _guardar_contratos_en_disco(
        localidad, resultado
    )
    work["stats"].extend([
        {
            "Localidad": localidad,
            "Archivo": f"Contratos ({resultado.get('hoja_cruce', 'Cps/Caja por depurar')})",
            "Nombre": item["contratos"]["name"],
            "Filas": resultado["total_contratos"],
            "CXP (suma mes)": resultado["cxp_total"],
            f"Columna {titulo_mes}": resultado["accion_columna"],
        },
        {
            "Localidad": localidad,
            "Archivo": "Matriz",
            "Nombre": item["matriz"]["name"],
            "Filas": len(df_matriz),
        },
    ])

    tick("Localidad · lista")


def _aplicar_work_a_sesion(work: dict) -> bool:
    errores = work["errores"]
    informe = work["informe_localidades"]
    total = len(work["cola"])
    titulo_mes = work["titulo_mes"]
    ahora = work["ahora"]

    if errores:
        st.session_state.errores_ejecucion = list(errores)
        st.session_state.pop("consolidacion_work", None)
        st.session_state.processed = False
        return False

    if len(informe) != total:
        st.session_state.errores_ejecucion = [
            f"**{item['localidad']}** — no se pudo consolidar (revise los mensajes anteriores)."
            for item in work["cola"]
            if item["localidad"] not in {x["localidad"] for x in informe}
        ]
        st.session_state.pop("consolidacion_work", None)
        st.session_state.processed = False
        return False

    conteo_global = work["conteo_global"]
    detalle_global = work["detalle_global"]
    resumen_global = [
        {
            "Método": METODOS_LABEL.get(codigo, codigo),
            "Contratos": cantidad,
        }
        for codigo, cantidad in sorted(conteo_global.items(), key=lambda x: -x[1])
        if cantidad > 0
    ]

    st.session_state.cruce_informe = informe
    establecer_cruce_detalle(detalle_global)
    st.session_state.contratos_actualizados = work["contratos_actualizados"]
    st.session_state.cruce_resumen_global = resumen_global
    st.session_state.file_stats = work["stats"]
    st.session_state.processed = True
    st.session_state.fecha_analisis = ahora
    st.session_state.last_processed_at = formato_fecha_colombia(ahora, con_hora=True)
    st.session_state.titulo_saldo_corte = titulo_mes
    _reset_estado_desempate_wizard()
    st.session_state.zip_descarga_listo = False
    _regenerar_zip_descarga_contratos()
    _persistir_snapshot_consolidacion()
    st.session_state[_CLAVE_MOSTRAR_RESULTADOS] = True
    return True


def ejecutar_consolidacion(
    cola,
    password_matriz: str,
    reporte: ReporteEjecucion,
    progress=None,
    fraccion_inicio: float = 0.0,
    fraccion_fin: float = 1.0,
):
    del fraccion_inicio, fraccion_fin
    stats, errores = [], []
    informe_localidades = []
    detalle_global = []
    contratos_actualizados = {}
    conteo_global: dict[str, int] = {}
    total = len(cola) or 1
    ahora = datetime.now()
    titulo_mes = titulo_saldo_corte(ahora)
    barra = _barra_nueva(total)

    for i, item in enumerate(cola):
        localidad = item["localidad"]

        def tick(fase: str) -> None:
            _barra_tick(
                barra,
                progress,
                fase,
                localidad=localidad,
                indice=i,
                total=total,
            )

        try:
            df_matriz = leer_hoja_matriz(
                bytes_archivo_cola(item["matriz"]),
                password_matriz,
                item["matriz"]["name"],
                header=MATRIZ_HEADER_FILA,
                avance=tick,
            )
        except ValueError as e:
            errores.append(f"**{localidad}** — Matriz: {e}")
            reporte.desde_excepcion(
                e,
                localidad=localidad,
                archivo=item["matriz"]["name"],
                fase="lectura_matriz",
            )
            continue
        except Exception as e:
            errores.append(f"**{localidad}** — Matriz: no se pudo leer ({e})")
            reporte.desde_excepcion(
                e,
                localidad=localidad,
                archivo=item["matriz"]["name"],
                fase="lectura_matriz",
            )
            continue

        try:
            resultado = procesar_localidad_cxp(
                bytes_archivo_cola(item["contratos"]),
                df_matriz,
                localidad,
                ahora,
                item["contratos"]["name"],
                item["matriz"]["name"],
                avance=tick,
            )
        except ValueError as e:
            errores.append(f"**{localidad}** — Contratos: {e}")
            reporte.desde_excepcion(
                e,
                localidad=localidad,
                archivo=item["contratos"]["name"],
                fase="procesamiento_contratos",
            )
            continue
        except Exception as e:
            errores.append(f"**{localidad}** — Contratos: no se pudo procesar ({e})")
            reporte.desde_excepcion(
                e,
                localidad=localidad,
                archivo=item["contratos"]["name"],
                fase="procesamiento_contratos",
            )
            continue

        tick("Excel · aplicado")
        registrar_resultado_localidad(reporte, item, resultado)
        _agregar_conteo_global(conteo_global, resultado["conteo"])
        informe_localidades.append({
            "localidad": localidad,
            "columna_mes": resultado["columna_mes"],
            "accion_columna": resultado["accion_columna"],
            "total_contratos": resultado["total_contratos"],
            "contratos_ok": resultado["contratos_ok"],
            "sin_resolver": resultado["sin_resolver"],
            "cxp_total": resultado["cxp_total"],
            "resumen_metodos": resultado["resumen_metodos"],
            "conteo": resultado["conteo"],
            "advertencias_suspendidos": resultado.get("advertencias_suspendidos", []),
        })
        detalle_global.extend(resultado["detalle"])
        contratos_actualizados[localidad] = _guardar_contratos_en_disco(
            localidad, resultado
        )

        stats.extend([
            {
                "Localidad": localidad,
                "Archivo": f"Contratos ({resultado.get('hoja_cruce', 'Cps/Caja por depurar')})",
                "Nombre": item["contratos"]["name"],
                "Filas": resultado["total_contratos"],
                "CXP (suma mes)": resultado["cxp_total"],
                f"Columna {titulo_mes}": resultado["accion_columna"],
            },
            {
                "Localidad": localidad,
                "Archivo": "Matriz",
                "Nombre": item["matriz"]["name"],
                "Filas": len(df_matriz),
            },
        ])

        tick("Localidad · lista")

    _barra_tick(barra, progress, "Consolidación · terminada")
    if progress is not None:
        progress.empty()

    if errores:
        st.session_state.errores_ejecucion = errores
        limpiar_resultado_consolidado()
        return False

    if len(informe_localidades) != total:
        limpiar_resultado_consolidado()
        return False

    resumen_global = [
        {
            "Método": METODOS_LABEL.get(codigo, codigo),
            "Contratos": cantidad,
        }
        for codigo, cantidad in sorted(conteo_global.items(), key=lambda x: -x[1])
        if cantidad > 0
    ]

    st.session_state.cruce_informe = informe_localidades
    establecer_cruce_detalle(detalle_global)
    st.session_state.contratos_actualizados = contratos_actualizados
    st.session_state.cruce_resumen_global = resumen_global
    st.session_state.file_stats = stats
    st.session_state.processed = True
    st.session_state.fecha_analisis = ahora
    st.session_state.last_processed_at = formato_fecha_colombia(ahora, con_hora=True)
    st.session_state.titulo_saldo_corte = titulo_mes
    _reset_estado_desempate_wizard()
    _persistir_snapshot_consolidacion()
    st.session_state[_CLAVE_MOSTRAR_RESULTADOS] = True
    return True


def _consolidacion_corriendo() -> bool:
    return bool(
        st.session_state.get("ejecutar_consolidacion_ahora")
        or st.session_state.get("consolidacion_en_curso")
    )


def _limpiar_estado_consolidacion_bloqueado() -> None:
    """Evita quedar con el botón deshabilitado si una ejecución anterior se interrumpió."""
    if st.session_state.get("consolidacion_en_curso") and not st.session_state.get(
        "ejecutar_consolidacion_ahora"
    ):
        st.session_state.consolidacion_en_curso = False


def _consumir_disparador_consolidacion() -> bool:
    """True si el usuario pulsó Continuar en el paso anterior."""
    if st.session_state.pop("pendiente_consolidacion", False):
        return True
    if st.session_state.pop("iniciar_consolidacion", False):
        return True
    return False


def _resolver_cola_para_ejecutar() -> list:
    cola = st.session_state.get("cola_ejecucion") or []
    if not cola:
        base = st.session_state.get("cola_localidades") or []
        if base:
            cola = cola_para_ejecutar(base)
            st.session_state.cola_ejecucion = cola
    return _asegurar_cola_en_disco(cola) if cola else []


def _ejecutar_consolidacion_si_pendiente(progress=None) -> None:
    if not st.session_state.get("ejecutar_consolidacion_ahora"):
        return
    work = st.session_state.get("consolidacion_work")
    disparo = _consumir_disparador_consolidacion()
    if not disparo and not work:
        st.session_state.ejecutar_consolidacion_ahora = False
        st.session_state.consolidacion_en_curso = False
        return
    if disparo:
        cola = _resolver_cola_para_ejecutar()
        if not cola:
            st.session_state.ejecutar_consolidacion_ahora = False
            st.session_state.consolidacion_en_curso = False
            if progress is not None:
                progress.empty()
            st.error(
                "No hay cola de ejecución. Pulse **Ejecutar consolidación** de nuevo "
                "y luego **Continuar**."
            )
            return
        pwd = st.session_state.get("pwd_matriz", "")
        procesar_consolidacion(cola, pwd, progress=progress, reiniciar=True)
    else:
        cola = _asegurar_cola_en_disco(work["cola"])
        pwd = work["pwd"]
        procesar_consolidacion(cola, pwd, progress=progress, reiniciar=False)


def procesar_consolidacion(
    cola_run: list,
    pwd: str,
    progress=None,
    *,
    reiniciar: bool = True,
):
    n = len(cola_run)
    if n == 0:
        st.error("La cola está vacía. Añada localidades con Contratos y Matriz.")
        return
    st.session_state.consolidacion_en_curso = True
    if progress is None:
        progress = st.progress(0, text="Preparando consolidación…")
    try:
        work = st.session_state.get("consolidacion_work")
        if reiniciar or work is None:
            limpiar_resultado_consolidado()
            cola_run = _asegurar_cola_en_disco(cola_run)
            barra = _barra_nueva(n)
            _barra_tick(barra, progress, "Validación · archivos")
            errores_acceso = _validar_archivos_accesibles(cola_run)
            if errores_acceso:
                nombres_ok, errores_nombres = False, errores_acceso
            else:
                _barra_tick(barra, progress, "Validación · contraseña Matriz")
                pwd_ok, errores_pwd = validar_contrasena_matrices(cola_run, pwd)
                if not pwd_ok:
                    nombres_ok, errores_nombres = False, errores_pwd
                else:
                    _barra_tick(barra, progress, "Validación · nombres")
                    nombres_ok, errores_nombres = _validar_nombres_en_cola(
                        cola_run,
                        pwd,
                        verificar_texto_localidad=False,
                    )
            if nombres_ok:
                _barra_tick(barra, progress, "Validación · lista")
            if not nombres_ok:
                st.session_state.ejecutar_consolidacion_ahora = False
                reporte = ReporteEjecucion()
                reporte.cerrar(False)
                if any(es_error_contrasena(e) for e in errores_nombres):
                    st.error(
                        "Contraseña incorrecta. Verifique la clave de la Matriz e intente de nuevo."
                    )
                else:
                    st.error(
                        "No se consolidaron las localidades correctamente. Revise los archivos."
                    )
                for detalle in errores_nombres:
                    st.markdown(f"- {detalle}")
                _actualizar_barra_progreso(
                    progress,
                    0.0,
                    "Validación detenida. Corrija los puntos anteriores.",
                )
                return

            ahora = datetime.now()
            work = {
                "cola": cola_run,
                "idx": 0,
                "pwd": pwd,
                "reporte_casos": [],
                "stats": [],
                "informe_localidades": [],
                "detalle_global": [],
                "contratos_actualizados": {},
                "conteo_global": {},
                "errores": [],
                "ahora": ahora,
                "titulo_mes": titulo_saldo_corte(ahora),
                "_barra": barra,
            }
            st.session_state.consolidacion_work = work
        else:
            work["cola"] = _asegurar_cola_en_disco(work["cola"])
            if "_barra" not in work:
                work["_barra"] = _barra_nueva(len(work["cola"]))
            st.session_state.consolidacion_work = work

        work = st.session_state.consolidacion_work
        total = len(work["cola"])

        while work["idx"] < total:
            idx = work["idx"]
            reporte_paso = ReporteEjecucion()
            _procesar_localidad_en_work(
                work, work["cola"][idx], reporte_paso, progress, idx, total
            )
            work["reporte_casos"].extend(c.a_dict() for c in reporte_paso.casos)
            work["idx"] = idx + 1

        _barra_tick(work.get("_barra", _barra_nueva(total)), progress, "Consolidación · terminada")
        progress.empty()

        reporte = _reporte_con_casos_guardados(work["reporte_casos"])
        exito = _aplicar_work_a_sesion(work)
        localidades_ok = len(st.session_state.get("cruce_informe", []))
        reporte.cerrar(exito, localidades_ok, n)
        _guardar_reporte_en_sesion(reporte)
        st.session_state.pop("consolidacion_work", None)

        if exito and st.session_state.processed:
            titulo_mes = st.session_state.get("titulo_saldo_corte", "")
            sin_res = sum(
                i.get("sin_resolver", 0)
                for i in st.session_state.get("cruce_informe", [])
            )
            msg = (
                f"**{n}** localidad(es) consolidadas · columna **{titulo_mes}** "
                f"(Cps, Suspendidos, Próximos, Trámites, Liquidados, Estrategias)."
            )
            if sin_res:
                msg += f" Pendiente: **{sin_res}** desempate(s) manual(es)."
            _vaciar_cola_tras_consolidar()
            msg += " La cola de entrada se vació para acelerar la app al recargar (F5)."
            st.success(msg)
        else:
            errores_ej = st.session_state.pop("errores_ejecucion", [])
            if any(es_error_contrasena(e) for e in errores_ej):
                st.error(
                    "Contraseña incorrecta. Verifique la clave de la Matriz e intente de nuevo."
                )
            else:
                st.error("No se consolidaron las localidades correctamente.")
            for detalle in errores_ej:
                st.markdown(f"- {detalle}")

        # Evita duplicar el download_button si luego se pinta el panel completo.
        if not (
            exito
            and st.session_state.get(_CLAVE_MOSTRAR_RESULTADOS)
        ):
            mostrar_reporte_tecnico_admin()
    finally:
        st.session_state.consolidacion_en_curso = False
        # Si aún hay trabajo pendiente (st.rerun al siguiente paso), mantener el flag.
        if st.session_state.get("consolidacion_work") is None:
            st.session_state.ejecutar_consolidacion_ahora = False


def render_solicitud_contrasena_matriz() -> None:
    """Formulario en página (sin modal) para no bloquear la vista durante la ejecución."""
    with st.container(border=True):
        st.markdown("**Contraseña Matriz**")
        st.caption("Ingrese la contraseña para abrir los archivos de Matriz.")
        pwd = st.text_input(
            "Contraseña",
            type="password",
            key="pwd_matriz_dialog",
            placeholder="Ingrese la contraseña de la Matriz",
            label_visibility="collapsed",
        )
        col_ok, col_cancel = st.columns(2)
        with col_ok:
            if st.button(
                "Continuar",
                type="primary",
                use_container_width=True,
                key="btn_pwd_matriz_continuar",
            ):
                st.session_state.pwd_matriz = pwd.strip() if pwd else ""
                st.session_state.abrir_dialogo = False
                st.session_state.pop("consolidacion_work", None)
                st.session_state.pendiente_consolidacion = True
                st.session_state.ejecutar_consolidacion_ahora = True
                st.rerun()
        with col_cancel:
            if st.button(
                "Cancelar",
                use_container_width=True,
                key="btn_pwd_matriz_cancelar",
            ):
                st.session_state.abrir_dialogo = False
                st.session_state.pop("consolidacion_work", None)
                st.session_state.pendiente_consolidacion = False
                st.session_state.ejecutar_consolidacion_ahora = False
                st.rerun()


if not st.session_state.get("acceso_autorizado"):
    if contrasena_acceso_esperada() is None:
        # App de prueba / Secrets sin contrasena_acceso: entrada directa
        st.session_state.acceso_autorizado = True
    else:
        render_portada_acceso()
        st.stop()

@st.cache_resource(show_spinner=False)
def _dependencias_consolidacion():
    """Una sola carga por proceso del servidor (no en cada F5)."""
    import msoffcrypto
    import msoffcrypto.exceptions as ms_exceptions
    import pandas as pd

    import cxp_cruce

    from cxp_cruce import (
        METODOS_LABEL,
        aplicar_desempate_en_contratos,
        clave_desde_detalle,
        claves_pendientes_localidad,
        procesar_localidad_cxp,
        recalcular_estadisticas_localidad,
        resolver_hoja_cruce_cxp,
        titulo_saldo_corte,
        validar_desempate_completo,
    )
    from reporte_ejecucion import (
        CasoNoPrevisto,
        ReporteEjecucion,
        registrar_resultado_localidad,
    )

    return {
        "pd": pd,
        "msoffcrypto": msoffcrypto,
        "ms_exceptions": ms_exceptions,
        "cxp_cruce": cxp_cruce,
        "METODOS_LABEL": METODOS_LABEL,
        "aplicar_desempate_en_contratos": aplicar_desempate_en_contratos,
        "clave_desde_detalle": clave_desde_detalle,
        "claves_pendientes_localidad": claves_pendientes_localidad,
        "procesar_localidad_cxp": procesar_localidad_cxp,
        "recalcular_estadisticas_localidad": recalcular_estadisticas_localidad,
        "resolver_hoja_cruce_cxp": resolver_hoja_cruce_cxp,
        "titulo_saldo_corte": titulo_saldo_corte,
        "validar_desempate_completo": validar_desempate_completo,
        "CasoNoPrevisto": CasoNoPrevisto,
        "ReporteEjecucion": ReporteEjecucion,
        "registrar_resultado_localidad": registrar_resultado_localidad,
    }


def _necesita_dependencias_pesadas() -> bool:
    if st.session_state.get("ejecutar_consolidacion_ahora"):
        return True
    if st.session_state.get("cola_localidades") or st.session_state.get("consolidacion_work"):
        return True
    if st.session_state.get("abrir_dialogo"):
        return True
    if st.session_state.get("processed") and st.session_state.get(
        _CLAVE_MOSTRAR_RESULTADOS, False
    ):
        return True
    if st.session_state.get("acceso_autorizado"):
        # Formulario / añadir a cola: hace falta pandas, cxp_cruce, etc.
        if st.session_state.get("processed") and not st.session_state.get(
            _CLAVE_MOSTRAR_RESULTADOS, False
        ):
            return False  # F5 rápido: solo resumen tras consolidar
        return True
    return False


def _inicializar_dependencias_modulo() -> None:
    global pd, msoffcrypto, ms_exceptions, cxp_cruce, METODOS_LABEL
    global aplicar_desempate_en_contratos, clave_desde_detalle
    global claves_pendientes_localidad, procesar_localidad_cxp
    global recalcular_estadisticas_localidad, resolver_hoja_cruce_cxp, titulo_saldo_corte
    global validar_desempate_completo, CasoNoPrevisto, ReporteEjecucion
    global registrar_resultado_localidad
    if globals().get("_DEPS_MODULO_LISTAS"):
        return
    dep = _dependencias_consolidacion()
    pd = dep["pd"]
    msoffcrypto = dep["msoffcrypto"]
    ms_exceptions = dep["ms_exceptions"]
    cxp_cruce = dep["cxp_cruce"]
    METODOS_LABEL = dep["METODOS_LABEL"]
    aplicar_desempate_en_contratos = dep["aplicar_desempate_en_contratos"]
    clave_desde_detalle = dep["clave_desde_detalle"]
    claves_pendientes_localidad = dep["claves_pendientes_localidad"]
    procesar_localidad_cxp = dep["procesar_localidad_cxp"]
    recalcular_estadisticas_localidad = dep["recalcular_estadisticas_localidad"]
    resolver_hoja_cruce_cxp = dep["resolver_hoja_cruce_cxp"]
    titulo_saldo_corte = dep["titulo_saldo_corte"]
    validar_desempate_completo = dep["validar_desempate_completo"]
    CasoNoPrevisto = dep["CasoNoPrevisto"]
    ReporteEjecucion = dep["ReporteEjecucion"]
    registrar_resultado_localidad = dep["registrar_resultado_localidad"]
    globals()["_DEPS_MODULO_LISTAS"] = True


if _necesita_dependencias_pesadas():
    _inicializar_dependencias_modulo()

_limpiar_estado_consolidacion_bloqueado()
_sanear_sesion_consolidacion()
if not st.session_state.get("ejecutar_consolidacion_ahora"):
    if st.session_state.get(_CLAVE_MOSTRAR_RESULTADOS):
        _compactar_sesion_vista_completa()
    else:
        _compactar_sesion_para_f5()

_barra_consolidacion = None
if st.session_state.get("ejecutar_consolidacion_ahora"):
    _barra_consolidacion = st.progress(0, text="Iniciando consolidación…")

# ── Título ─────────────────────────────────────────────────────────────────────
st.markdown('<h1 class="app-title">Plan de Choque</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="app-subtitle">Bogotá — consolidación por localidad</p>',
    unsafe_allow_html=True,
)

_omitir_formulario = _omitir_formulario_entrada()

if _omitir_formulario:
    cola_ej = st.session_state.get("cola_ejecucion") or []
    if not cola_ej and st.session_state.get("consolidacion_work"):
        cola_ej = st.session_state.consolidacion_work.get("cola", [])
    if cola_ej:
        nombres = ", ".join(item["localidad"] for item in cola_ej)
        st.info(
            f"Consolidación en curso ({len(cola_ej)} localidad/es): **{nombres}**. "
            "No cierre esta pestaña hasta ver el resultado."
        )
    else:
        st.info("Consolidación en curso. No cierre esta pestaña hasta ver el resultado.")
    _ejecutar_consolidacion_si_pendiente(_barra_consolidacion)
    st.divider()

uk = st.session_state.upload_key

_trabajo_pausado = st.session_state.get("consolidacion_work")
if not _omitir_formulario and _trabajo_pausado:
    _idx = _trabajo_pausado.get("idx", 0)
    _total = len(_trabajo_pausado.get("cola", []))
    with st.container(border=True):
        st.warning(
            f"Quedó una consolidación interrumpida (**{_idx}/{_total}** localidades procesadas)."
        )
        c_reanudar, c_descartar = st.columns(2)
        with c_reanudar:
            if st.button(
                "Reanudar consolidación",
                type="primary",
                use_container_width=True,
                key="btn_reanudar_consolidacion",
            ):
                st.session_state.ejecutar_consolidacion_ahora = True
                st.session_state.consolidacion_en_curso = True
                st.session_state.pendiente_consolidacion = False
                st.rerun()
        with c_descartar:
            if st.button(
                "Descartar y empezar de nuevo",
                use_container_width=True,
                key="btn_descartar_consolidacion",
            ):
                st.session_state.pop("consolidacion_work", None)
                st.session_state.pendiente_consolidacion = False
                st.session_state.ejecutar_consolidacion_ahora = False
                st.rerun()

if not _omitir_formulario:
    # ── Formulario ─────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown('<p class="form-card-title">Entrada por localidad</p>', unsafe_allow_html=True)
        st.caption(
            "Proporcione el archivo de **Contratos plan de choque** y su **Matriz** "
            "correspondiente por localidad. En Excel, quite los **filtros/autofiltros** "
            "de ambos archivos antes de subirlos."
        )

        st.markdown('<p class="field-label">Localidad</p>', unsafe_allow_html=True)
        localidad = st.selectbox(
            "Localidad",
            options=[SELECCION_LOCALIDAD] + LOCALIDADES,
            index=0,
            label_visibility="collapsed",
            key=f"select_localidad_{uk}",
        )

        st.divider()

        st.markdown(
            '<p class="field-label"><span class="field-num">1</span> Contratos plan de choque</p>',
            unsafe_allow_html=True,
        )
        archivo_contratos = st.file_uploader(
            "Contratos plan de choque",
            type=["xlsx", "xls"],
            accept_multiple_files=False,
            label_visibility="collapsed",
            key=f"uploader_contratos_{uk}",
            help="Un solo archivo Excel (.xlsx o .xls).",
        )
        if archivo_contratos:
            st.markdown(
                f'<p class="file-ok">✓ {archivo_contratos.name}</p>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<p class="field-label"><span class="field-num">2</span> Matriz</p>',
            unsafe_allow_html=True,
        )
        archivo_matriz = st.file_uploader(
            "Matriz",
            type=["xlsx", "xls"],
            accept_multiple_files=False,
            label_visibility="collapsed",
            key=f"uploader_matriz_{uk}",
            help="Un solo archivo Excel. Hoja MATRIZ OXP.",
        )
        if archivo_matriz:
            st.markdown(
                f'<p class="file-ok">✓ {archivo_matriz.name}</p>',
                unsafe_allow_html=True,
            )

        form_ok = formulario_completo(localidad, archivo_contratos, archivo_matriz)

        add_clicked = st.button(
            "Añadir a cola de consolidados",
            type="secondary",
            use_container_width=True,
            help="Guarda la localidad y los archivos en la cola. Luego puede cargar la siguiente.",
        )

    if add_clicked:
        if not form_ok:
            st.warning(
                "Complete la localidad y los dos archivos antes de añadir el consolidado a la cola."
            )
        elif any(
            item["localidad"] == localidad for item in st.session_state.cola_localidades
        ):
            st.warning(f"**{localidad}** ya está en la cola. Quítela o elija otra localidad.")
        else:
            st.session_state.cola_localidades.append(
                entrada_desde_formulario(localidad, archivo_contratos, archivo_matriz)
            )
            st.session_state.upload_key += 1
            _purgar_uploaders_obsoletos()
            st.toast(f"{localidad} añadido a la cola", icon="➕")
            st.rerun()

# ── Cola pendiente ─────────────────────────────────────────────────────────────
cola = st.session_state.cola_localidades
if not _omitir_formulario and cola:
    st.markdown(
        f'<p class="section-title">Cola de consolidados ({len(cola)})</p>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Los archivos quedan guardados en la cola. Use el icono de basura para eliminar una localidad."
    )
    for i, item in enumerate(cola):
        loc = item["localidad"]
        c_num, c_loc, c_con, c_mat, c_btn = st.columns([0.4, 1.5, 2.1, 2.1, 0.75])
        with c_num:
            st.markdown(f"**{i + 1}**")
        with c_loc:
            st.markdown(loc)
        with c_con:
            st.markdown(f"Contratos: `{item['contratos']['name']}`")
        with c_mat:
            st.markdown(f"Matriz: `{item['matriz']['name']}`")
        with c_btn:
            if st.button(
                " ",
                key=f"quitar_cola_{loc}",
                use_container_width=True,
                help=f"Eliminar {loc} de la cola",
            ):
                quitar_de_cola(loc)
                limpiar_resultado_consolidado()
                st.toast(f"{loc} eliminado de la cola", icon="🗑️")
                st.rerun()

    if st.button("Vaciar cola", type="secondary"):
        st.session_state.cola_localidades = []
        limpiar_resultado_consolidado()
        st.rerun()

st.divider()
run_clicked = False
if st.session_state.get("abrir_dialogo"):
    render_solicitud_contrasena_matriz()
elif not _consolidacion_corriendo():
    run_clicked = st.button(
        "Ejecutar consolidación",
        type="primary",
        use_container_width=True,
        key="btn_ejecutar_consolidacion",
        help="Procesa todos los consolidados de la cola.",
    )

if run_clicked:
    if not puede_ejecutar_cola(st.session_state.cola_localidades):
        st.warning(
            "Añada al menos un consolidado a la cola (localidad, Contratos y Matriz) "
            "antes de ejecutar."
        )
    else:
        cola_ejec = cola_para_ejecutar(st.session_state.cola_localidades)
        archivos_ok, errores_archivos = validar_archivos_en_cola(cola_ejec)
        if not cola_ejec or not archivos_ok:
            st.error(
                "No se puede ejecutar: cada localidad en la cola debe incluir "
                "Contratos plan de choque y Matriz."
            )
            for detalle in errores_archivos:
                st.markdown(f"- {detalle}")
        else:
            st.session_state.cola_ejecucion = cola_ejec
            st.session_state.abrir_dialogo = True
            st.session_state.pendiente_consolidacion = False
            st.rerun()

def _render_panel_resultados_completos() -> None:
    """Tablas, desempate y descargas (solo cuando el usuario lo pide o tras consolidar)."""
    snap = _cargar_snapshot_consolidacion()
    stats = snap.get("file_stats") or []
    informe = snap.get("informe") or []
    st.session_state.cruce_resumen_global = snap.get("cruce_resumen_global") or []
    titulo_mes = snap.get("titulo_saldo_corte") or st.session_state.get("titulo_saldo_corte", "")
    etiqueta_cxp = titulo_mes or "Saldo de corte"
    fecha_analisis = snap.get("fecha_analisis") or st.session_state.get("fecha_analisis")
    procesado_en = snap.get("last_processed_at") or st.session_state.get("last_processed_at", "")

    st.markdown('<p class="section-title">Resultado consolidado</p>', unsafe_allow_html=True)
    if titulo_mes or procesado_en or fecha_analisis:
        partes_fecha = []
        if titulo_mes:
            partes_fecha.append(f"Columna **{titulo_mes}**")
        if fecha_analisis:
            partes_fecha.append(formato_fecha_colombia(fecha_analisis))
        if procesado_en:
            partes_fecha.append(f"Procesado {procesado_en}")
        st.caption(" · ".join(partes_fecha))
    mostrar_reporte_tecnico_admin()

    total_contratos = sum(i.get("total_contratos", 0) for i in informe)
    total_ok = sum(i.get("contratos_ok", 0) for i in informe)
    sin_resolver = sum(i.get("sin_resolver", 0) for i in informe)
    cxp_total = sum(i.get("cxp_total", 0) for i in informe)
    cxp_fmt = formato_numero_metrica(cxp_total)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Localidades</div>'
            f'<div class="metric-value metric-value-sm">{len(informe)}</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Contratos cruzados</div>'
            f'<div class="metric-value metric-value-sm">{total_ok}/{total_contratos}</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">{etiqueta_cxp}</div>'
            f'<div class="metric-value">{cxp_fmt}</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Sin resolver</div>'
            f'<div class="metric-value">{sin_resolver}</div></div>',
            unsafe_allow_html=True,
        )

    requiere_detalle = sin_resolver > 0 or informe_requiere_detalle_cruce(informe)
    mostrar_informe_cruce_consolidado(
        informe,
        titulo_mes,
        cargar_tablas_detalle=requiere_detalle,
    )
    descargas_ok = consolidacion_lista_para_descarga()

    detalle_todo: list = []
    if sin_resolver > 0:
        detalle_todo = obtener_cruce_detalle()
    if sin_resolver > 0 and detalle_todo:
        st.markdown('<p class="section-title">Contratos sin resolver</p>', unsafe_allow_html=True)
        st.error(
            f"Hay **{sin_resolver}** contrato(s) sin saldo en **{titulo_mes}**. "
            "Las descargas de Contratos actualizados y archivos globales están bloqueadas "
            "hasta completar el desempate manual (información 100% confiable)."
        )
        df_resumen_sr = resumen_sin_resolver_por_localidad(detalle_todo)
        if len(df_resumen_sr) > 1:
            st.markdown("**Por localidad**")
            st.dataframe(df_resumen_sr, use_container_width=True, hide_index=True)
        st.caption(
            "Revise cada incidencia en pantalla: elija la línea de Matriz correcta y avance con **Siguiente**. "
            "Al terminar todas, aplique los desempates."
        )
        render_asistente_desempate(detalle_todo, titulo_mes)

    if stats:
        with st.expander("Archivos de entrada (Matriz y Contratos)", expanded=False):
            cols_show = [
                c
                for c in [
                    "Localidad",
                    "Archivo",
                    "Nombre",
                    "Filas",
                    "CXP (suma mes)",
                    f"Columna {titulo_mes}",
                ]
                if c in pd.DataFrame(stats).columns
            ]
            st.dataframe(
                pd.DataFrame(stats)[cols_show],
                use_container_width=True,
                hide_index=True,
            )

    contratos_act = st.session_state.get("contratos_actualizados", {})
    if contratos_act:
        fecha_dl = st.session_state.get("fecha_analisis") or fecha_referencia_analisis()
        n_loc = len(contratos_act)
        st.markdown(
            '<p class="section-title">Contratos plan de choque actualizados</p>',
            unsafe_allow_html=True,
        )
        st.caption(
            f"Un ZIP con {n_loc} archivo(s) Excel (uno por localidad). "
            f"Abra el ZIP y use el .xlsx dentro. "
            f"El mes en el nombre se actualiza a «- {mes_capitalizado(fecha_dl)}» "
            "(conserva el texto antes del guion)."
        )
        if not descargas_ok:
            st.caption(
                "Disponible cuando **Sin resolver** sea 0 (complete el desempate manual arriba)."
            )
        zip_info = st.session_state.get("zip_descarga_contratos")
        nombre_dl = (zip_info or {}).get("nombre") or "contratos.zip"
        mime_dl = (zip_info or {}).get("mime") or "application/zip"
        ruta_zip = (zip_info or {}).get("path")
        if descargas_ok and ruta_zip and Path(ruta_zip).is_file():
            datos_dl = _leer_binario_desde_ruta(
                ruta_zip, Path(ruta_zip).stat().st_mtime
            )
            st.download_button(
                label="Descargar Contratos actualizados (ZIP)",
                data=datos_dl,
                file_name=nombre_dl,
                mime=mime_dl,
                key="dl_contratos_todas",
                use_container_width=True,
            )
        elif descargas_ok:
            st.warning(
                "No se encontró el ZIP en el servidor. Vuelva a consolidar o aplique "
                "el desempate para regenerarlo."
            )
        with st.expander("Archivos incluidos en la descarga"):
            for loc, data in sorted(contratos_act.items(), key=lambda x: x[0]):
                st.markdown(
                    f"- **{loc}:** "
                    f"`{nombre_descarga_contratos_actualizado(loc, data.get('nombre_contratos', ''), fecha_dl)}`"
                )
    st.markdown('<p class="section-title">Archivos globales de salida</p>', unsafe_allow_html=True)
    if not descargas_ok:
        st.caption(
            "Bloqueados mientras haya contratos sin resolver. "
            "Los archivos globales solo se generan con datos 100% completos."
        )
    else:
        st.caption(
            "Reúnen la información de **todas** las localidades: "
            "Matriz y Contratos plan de choque actualizados (con desempate aplicado). "
            "Se guardan en Descargas."
        )
    if st.button(
        "Descargar archivos de salida",
        use_container_width=True,
        key="btn_descargar_excel",
        disabled=not descargas_ok,
    ):
        try:
            df_export = dataframe_consolidado()
            rutas = guardar_archivos_salida(df_export, stats)
            st.session_state.ultima_descarga = [str(r) for r in rutas]
            st.toast("2 archivos guardados en Descargas", icon="✅")
            lista = "\n".join(f"- `{r.name}`" for r in rutas)
            st.success(
                "Se guardaron **2** archivos en Descargas (siempre los mismos, "
                "sin importar cuántas localidades procesó):\n\n" + lista
            )
        except (OSError, ValueError) as e:
            st.error(f"No se pudo guardar en Descargas: {e}")

    if st.button(
        "Ocultar resultados (recarga más rápida)",
        use_container_width=True,
        key="btn_ocultar_resultados_completos",
    ):
        st.session_state[_CLAVE_MOSTRAR_RESULTADOS] = False
        st.rerun()


# ── Resultados ─────────────────────────────────────────────────────────────────
if st.session_state.processed:
    resumen_ligero = st.session_state.get(_CLAVE_RESUMEN_LIGERO) or {}
    if not resumen_ligero:
        snap_tmp = _cargar_snapshot_consolidacion()
        informe_tmp = snap_tmp.get("informe") or []
        if informe_tmp:
            resumen_ligero = _resumen_ligero_desde_informe(informe_tmp)
            st.session_state[_CLAVE_RESUMEN_LIGERO] = resumen_ligero

    if not st.session_state.get(_CLAVE_MOSTRAR_RESULTADOS):
        st.markdown('<p class="section-title">Resultado consolidado</p>', unsafe_allow_html=True)
        n_loc = resumen_ligero.get("n_localidades", 0)
        sin_r = resumen_ligero.get("sin_resolver", 0)
        titulo_mes = resumen_ligero.get("titulo_mes") or st.session_state.get(
            "titulo_saldo_corte", ""
        )
        st.success(
            f"Consolidación lista: **{n_loc}** localidad(es), "
            f"**{resumen_ligero.get('total_ok', 0)}/{resumen_ligero.get('total_contratos', 0)}** "
            f"contratos cruzados"
            + (f", **{sin_r}** sin resolver" if sin_r else "")
            + (f". Columna **{titulo_mes}**." if titulo_mes else ".")
        )
        st.caption(
            "Tras F5 la pantalla se mantiene liviana. Pulse el botón para cargar tablas, "
            "desempate y descargas."
        )
        if st.button(
            "Mostrar resultados completos",
            type="primary",
            use_container_width=True,
            key="btn_mostrar_resultados_completos",
        ):
            st.session_state[_CLAVE_MOSTRAR_RESULTADOS] = True
            _inicializar_dependencias_modulo()
            st.rerun()
    else:
        _inicializar_dependencias_modulo()
        _render_panel_resultados_completos()
