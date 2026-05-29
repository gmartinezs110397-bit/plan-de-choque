import importlib
import re
import sys
import unicodedata
import zipfile
from io import BytesIO
from datetime import datetime, date
from pathlib import Path

import msoffcrypto
import msoffcrypto.exceptions as ms_exceptions
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
# Carpeta del proyecto primero (evita importar un cxp_cruce viejo en caché)
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

import cxp_cruce

importlib.reload(cxp_cruce)

from cxp_cruce import (
    METODOS_LABEL,
    aplicar_desempate_en_contratos,
    clave_desde_detalle,
    claves_pendientes_localidad,
    procesar_localidad_cxp,
    quitar_autofiltros_xlsx,
    recalcular_estadisticas_localidad,
    resolver_hoja_cruce_cxp,
    titulo_saldo_corte,
    validar_desempate_completo,
)
from reporte_ejecucion import (
    ReporteEjecucion,
    registrar_resultado_localidad,
)

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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
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
        font-weight: 600;
        color: #0f172a;
        margin: 2rem 0 0.75rem;
        padding-bottom: 0.4rem;
        border-bottom: 2px solid #e2e8f0;
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
    .st-key-select_localidad [data-baseweb="select"] > div,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        border-color: #cbd5e1 !important;
        border-radius: 10px !important;
    }
    .st-key-select_localidad [data-baseweb="select"]:focus-within > div,
    .st-key-select_localidad [data-baseweb="select"]:hover > div,
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
    /* Descargas — verde */
    .st-key-btn_descargar_excel button,
    .st-key-dl_contratos_todas button {
        background: #059669 !important;
        background-color: #059669 !important;
        color: #ffffff !important;
        border: 1px solid #059669 !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 8px rgba(5, 150, 105, 0.35) !important;
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
FILA_INICIO_MATRIZ = 8  # columna A desde fila 8 en hoja MATRIZ OXP
SELECCION_LOCALIDAD = "Seleccione localidad"
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
        "iniciar_consolidacion": False,
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
              if (++intentos > 300) clearInterval(timer);
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
    if not contrasena_ok:
        st.error(
            "Falta configurar la contraseña en Streamlit Cloud → **Manage app** → "
            "**Settings** → **Secrets** (`contrasena_acceso = \"1100\"` o `codigo_acceso`)."
        )
        st.stop()

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
            zf.writestr(nombre, data["bytes_contratos"])
    buf.seek(0)
    mes = mes_capitalizado(f)
    zip_nombre = sanitizar_nombre_archivo(
        f"Contratos plan de choque actualizados {mes} "
        f"{localidades_en_nombre_archivo(localidades)}.zip"
    )
    return buf.getvalue(), zip_nombre, "application/zip"


METODOS_SIN_RESOLVER = (
    METODOS_LABEL["verificar"],
    METODOS_LABEL["sin_matriz"],
)


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
    detalle = list(st.session_state.get("cruce_detalle", []))
    contratos_act = dict(st.session_state.get("contratos_actualizados", {}))
    fecha = st.session_state.get("fecha_analisis") or fecha_referencia_analisis()
    titulo_mes = titulo_saldo_corte(fecha)
    informe = list(st.session_state.get("cruce_informe", []))

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
            contratos_act[loc]["bytes_contratos"],
            fecha,
            mapa,
            detalle,
            loc,
        )
        contratos_act[loc]["bytes_contratos"] = bytes_nuevos
        stats_loc = recalcular_estadisticas_localidad(
            [f for f in detalle if f.get("Localidad") == loc],
            titulo_mes,
        )
        contratos_act[loc].update(stats_loc)
        for i, info in enumerate(informe):
            if info["localidad"] == loc:
                informe[i] = {**info, **stats_loc}
                break

    st.session_state.cruce_detalle = detalle
    st.session_state.contratos_actualizados = contratos_act
    st.session_state.cruce_informe = informe
    st.session_state.consolidated_df = pd.DataFrame(detalle) if detalle else pd.DataFrame()

    conteo_global: dict[str, int] = {}
    for info in informe:
        _agregar_conteo_global(conteo_global, info.get("conteo", {}))
    st.session_state.cruce_resumen_global = [
        {
            "Método": METODOS_LABEL.get(codigo, codigo),
            "Contratos": cantidad,
        }
        for codigo, cantidad in sorted(conteo_global.items(), key=lambda x: -x[1])
        if cantidad > 0
    ]

    for s in st.session_state.get("file_stats", []):
        if s.get("Archivo") == "Contratos (Cps por depurar)":
            loc = s.get("Localidad")
            info = next((i for i in informe if i["localidad"] == loc), None)
            if info:
                s["CXP (suma mes)"] = info["cxp_total"]

    _reset_estado_desempate_wizard()
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
    informe = st.session_state.get("cruce_informe", [])
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
        return BytesIO(quitar_autofiltros_xlsx(dec.getvalue()))

    raw.seek(0)
    try:
        verificar_lectura_matriz(raw)
    except Exception as e:
        raise ValueError(f"{etiqueta}: no se pudo leer ({e})") from e
    raw.seek(0)
    return BytesIO(quitar_autofiltros_xlsx(raw.getvalue()))


def sanitizar_excel_sin_filtros(data: bytes, nombre_archivo: str) -> bytes:
    """Quita filtros de Excel .xlsx/.xlsm al subir (Contratos)."""
    if not str(nombre_archivo).lower().endswith((".xlsx", ".xlsm")):
        return data
    return quitar_autofiltros_xlsx(data)


def leer_hoja_matriz(
    file_bytes: bytes, password: str, nombre_archivo: str = "", **kwargs
) -> pd.DataFrame:
    """Lee la hoja MATRIZ OXP; detecta contraseña incorrecta."""
    try:
        libro = abrir_matriz_excel(file_bytes, password, nombre_archivo)
        return pd.read_excel(libro, sheet_name=SHEET_MATRIZ, engine="openpyxl", **kwargs)
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


def texto_localidad_en_matriz(file_bytes: bytes, password: str, nombre_archivo: str = "") -> str:
    """Lee columna A desde fila 8 en MATRIZ OXP."""
    df = leer_hoja_matriz(
        file_bytes, password, nombre_archivo, header=None, usecols=[0]
    )
    if len(df) < FILA_INICIO_MATRIZ:
        return ""
    valores = df.iloc[FILA_INICIO_MATRIZ - 1 :, 0].dropna().astype(str)
    return " ".join(valores.tolist())


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
            leer_hoja_matriz(
                item["matriz"]["bytes"], password_matriz, item["matriz"]["name"], nrows=3
            )
        except ValueError as e:
            errores.append(f"**{loc}** — Matriz **{nm}**: {e}")
        except Exception as e:
            errores.append(f"**{loc}** — Matriz **{nm}**: {e}")
    return len(errores) == 0, errores


def validar_cola_archivos(cola: list, password_matriz: str) -> tuple[bool, list[str]]:
    errores = []

    pwd_ok, errores_pwd = validar_contrasena_matrices(cola, password_matriz)
    if not pwd_ok:
        return False, errores_pwd

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
        else:
            ok_m, msg_m = validar_localidad_en_hoja_matriz(
                item["matriz"]["bytes"], password_matriz, loc, nm
            )
            if not ok_m:
                errores.append(f"**{loc}** — {msg_m}")

    return len(errores) == 0, errores


def file_to_buffer(uploaded_file) -> dict:
    data = uploaded_file.getvalue()
    data = sanitizar_excel_sin_filtros(data, uploaded_file.name)
    return {"bytes": data, "name": uploaded_file.name}


def buffer_to_file(entry: dict):
    return BytesIO(entry["bytes"])


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
    resumen_global = st.session_state.get("cruce_resumen_global") or []
    if resumen_global:
        partes.append(pd.DataFrame([{"Campo": "— Resumen cruce (todas las localidades) —", "Valor": ""}]))
        rg = pd.DataFrame(resumen_global)
        rg.columns = ["Método", "Contratos"]
        partes.append(rg)
    informe = st.session_state.get("cruce_informe") or []
    contratos_act = st.session_state.get("contratos_actualizados") or {}
    stats_por_loc = {}
    for s in stats:
        loc = s.get("Localidad")
        if not loc:
            continue
        stats_por_loc.setdefault(loc, []).append(s)

    for loc_info in informe:
        loc = loc_info["localidad"]
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
                    "Campo": f"— {loc} —",
                    "Valor": (
                        f"CXP {loc_info['cxp_total']:,.0f} | "
                        f"Sin resolver {loc_info['sin_resolver']}"
                    ),
                },
                {"Campo": "Matriz (origen)", "Valor": matriz_nombre or "—"},
                {"Campo": "Contratos plan de choque (origen)", "Valor": contratos_orig or "—"},
                {
                    "Campo": "Contratos plan de choque (actualizado)",
                    "Valor": contratos_gen,
                },
            ])
        )
        if loc_info.get("resumen_metodos"):
            lm = pd.DataFrame(loc_info["resumen_metodos"])
            lm.columns = ["Método", "Contratos"]
            partes.append(lm)
    detalle = st.session_state.get("cruce_detalle") or []
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
    tiene_c = bool(item.get("contratos") and item["contratos"].get("bytes"))
    tiene_m = bool(item.get("matriz") and item["matriz"].get("bytes"))
    return tiene_c and tiene_m


def validar_archivos_en_cola(cola: list) -> tuple[bool, list[str]]:
    errores = []
    for item in cola:
        loc = item.get("localidad", "Localidad")
        if not item.get("contratos") or not item["contratos"].get("bytes"):
            errores.append(f"**{loc}** — Falta el archivo de Contratos plan de choque.")
        if not item.get("matriz") or not item["matriz"].get("bytes"):
            errores.append(f"**{loc}** — Falta el archivo de Matriz.")
    return len(errores) == 0, errores


def cola_para_ejecutar(cola: list) -> list:
    """Ítems de la cola con Contratos y Matriz listos para consolidar."""
    return [i for i in cola if item_tiene_contratos_y_matriz(i)]


def puede_ejecutar_cola(cola: list) -> bool:
    """La cola tiene al menos un consolidado completo."""
    return bool(cola) and all(item_tiene_contratos_y_matriz(i) for i in cola)


def quitar_de_cola(localidad: str) -> None:
    st.session_state.cola_localidades = [
        i for i in st.session_state.cola_localidades if i["localidad"] != localidad
    ]


def limpiar_resultado_consolidado():
    st.session_state.processed = False
    st.session_state.consolidated_df = None
    st.session_state.file_stats = []
    st.session_state.last_processed_at = None
    st.session_state.error_ultima_ejecucion = None
    st.session_state.errores_ejecucion = []
    st.session_state.fecha_analisis = None
    st.session_state.cruce_informe = []
    st.session_state.cruce_detalle = []
    st.session_state.contratos_actualizados = {}
    st.session_state.cruce_resumen_global = []
    st.session_state.titulo_saldo_corte = ""
    _reset_estado_desempate_wizard()


def _agregar_conteo_global(acumulado: dict, conteo: dict) -> None:
    for codigo, cantidad in conteo.items():
        acumulado[codigo] = acumulado.get(codigo, 0) + cantidad


def _guardar_reporte_en_sesion(reporte: ReporteEjecucion) -> None:
    if not reporte.tiene_casos():
        st.session_state.reporte_ejecucion = None
        return
    df = reporte.a_dataframe()
    st.session_state.reporte_ejecucion = {
        "texto": reporte.generar_texto(),
        "tabla": df.to_dict("records"),
        "resumen": reporte.resumen,
        "generado": datetime.now().isoformat(timespec="seconds"),
    }


def mostrar_reporte_tecnico_admin() -> None:
    """Solo casos no previstos del sistema (para quien mantiene el código)."""
    payload = st.session_state.get("reporte_ejecucion")
    if not payload or not payload.get("tabla"):
        return

    with st.expander("Casos no previstos (para soporte técnico)", expanded=True):
        st.caption(payload.get("resumen", ""))
        nombre_archivo = (
            f"casos_no_previstos_{payload.get('generado', 'ejecucion')}.txt"
        ).replace(":", "-")

        st.download_button(
            "Descargar reporte (.txt)",
            data=payload.get("texto", ""),
            file_name=nombre_archivo,
            mime="text/plain",
            use_container_width=True,
        )
        st.dataframe(
            pd.DataFrame(payload["tabla"]),
            use_container_width=True,
            hide_index=True,
        )


def ejecutar_consolidacion(
    cola,
    password_matriz: str,
    reporte: ReporteEjecucion,
):
    stats, errores = [], []
    informe_localidades = []
    detalle_global = []
    contratos_actualizados = {}
    conteo_global: dict[str, int] = {}
    total = len(cola)
    progress = st.progress(0, text="Iniciando consolidación…")
    ahora = datetime.now()
    titulo_mes = titulo_saldo_corte(ahora)

    for i, item in enumerate(cola):
        localidad = item["localidad"]
        progress.progress(
            (i + 1) / total,
            text=f"Cruce Matriz → Contratos ({localidad})…",
        )

        try:
            df_matriz = leer_hoja_matriz(
                item["matriz"]["bytes"],
                password_matriz,
                item["matriz"]["name"],
                header=6,
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
                item["contratos"]["bytes"],
                df_matriz,
                localidad,
                ahora,
                item["contratos"]["name"],
                item["matriz"]["name"],
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
        contratos_actualizados[localidad] = resultado

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
    st.session_state.cruce_detalle = detalle_global
    st.session_state.contratos_actualizados = contratos_actualizados
    st.session_state.cruce_resumen_global = resumen_global
    st.session_state.file_stats = stats
    st.session_state.consolidated_df = (
        pd.DataFrame(detalle_global) if detalle_global else pd.DataFrame()
    )
    st.session_state.processed = True
    st.session_state.fecha_analisis = ahora
    st.session_state.last_processed_at = formato_fecha_colombia(ahora, con_hora=True)
    st.session_state.titulo_saldo_corte = titulo_mes
    _reset_estado_desempate_wizard()
    return True


def procesar_consolidacion(cola_run: list, pwd: str):
    n = len(cola_run)
    limpiar_resultado_consolidado()
    reporte = ReporteEjecucion()

    with st.spinner("Chequeando archivos…"):
        nombres_ok, errores_nombres = validar_cola_archivos(cola_run, pwd)

    if not nombres_ok:
        reporte.cerrar(False)
        if any(es_error_contrasena(e) for e in errores_nombres):
            st.error("Contraseña incorrecta. Verifique la clave de la Matriz e intente de nuevo.")
        else:
            st.error("No se consolidaron las localidades correctamente. Revise los archivos.")
        for detalle in errores_nombres:
            st.markdown(f"- {detalle}")
        return

    exito = ejecutar_consolidacion(cola_run, pwd, reporte)
    localidades_ok = len(st.session_state.get("cruce_informe", []))
    reporte.cerrar(exito, localidades_ok, n)
    _guardar_reporte_en_sesion(reporte)

    if exito and st.session_state.processed:
        titulo_mes = st.session_state.get("titulo_saldo_corte", "")
        sin_res = sum(i.get("sin_resolver", 0) for i in st.session_state.get("cruce_informe", []))
        msg = (
            f"Se procesaron **{n}** localidad(es). "
            f"Columna **{titulo_mes}** en Cps/Caja por depurar y seguimiento mensual "
            "(Suspendidos, Próximos a perder, Trámites sectores, Liquidados con saldo)."
        )
        if sin_res:
            msg += f" Revise **{sin_res}** contrato(s) marcados como sin resolver."
        st.success(msg)
        for item in st.session_state.get("cruce_informe", []):
            for aviso in item.get("advertencias_suspendidos") or []:
                st.warning(f"**{item.get('localidad', '')}** — {aviso}")
    else:
        limpiar_resultado_consolidado()
        errores_ej = st.session_state.pop("errores_ejecucion", [])
        todos_errores = errores_ej
        if any(es_error_contrasena(e) for e in todos_errores):
            st.error("Contraseña incorrecta. Verifique la clave de la Matriz e intente de nuevo.")
        else:
            st.error("No se consolidaron las localidades correctamente.")
        for detalle in todos_errores:
            st.markdown(f"- {detalle}")

    mostrar_reporte_tecnico_admin()  # solo si hubo casos no previstos


@st.dialog("Contraseña Matriz")
def dialogo_contrasena_matriz():
    pwd = st.text_input(
        "Contraseña",
        type="password",
        key="pwd_matriz_dialog",
        placeholder="Ingrese la contraseña de la Matriz",
    )
    col_ok, col_cancel = st.columns(2)
    with col_ok:
        if st.button("Continuar", type="primary", use_container_width=True):
            st.session_state.pwd_matriz = pwd.strip() if pwd else ""
            st.session_state.iniciar_consolidacion = True
            st.session_state.abrir_dialogo = False
            st.rerun()
    with col_cancel:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.abrir_dialogo = False
            st.rerun()


if not st.session_state.get("acceso_autorizado"):
    render_portada_acceso()

# ── Título ─────────────────────────────────────────────────────────────────────
st.markdown('<h1 class="app-title">Plan de Choque</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="app-subtitle">Bogotá — consolidación por localidad</p>',
    unsafe_allow_html=True,
)

uk = st.session_state.upload_key

# ── Formulario ─────────────────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown('<p class="form-card-title">Entrada por localidad</p>', unsafe_allow_html=True)
    st.caption(
        "Proporcione el archivo de **Contratos plan de choque** y su **Matriz** "
        "correspondiente por localidad."
    )

    st.markdown('<p class="field-label">Localidad</p>', unsafe_allow_html=True)
    localidad = st.selectbox(
        "Localidad",
        options=[SELECCION_LOCALIDAD] + LOCALIDADES,
        index=0,
        label_visibility="collapsed",
        key="select_localidad",
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
        st.markdown(f'<p class="file-ok">✓ {archivo_contratos.name}</p>', unsafe_allow_html=True)

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
        st.markdown(f'<p class="file-ok">✓ {archivo_matriz.name}</p>', unsafe_allow_html=True)

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
    elif any(item["localidad"] == localidad for item in st.session_state.cola_localidades):
        st.warning(f"**{localidad}** ya está en la cola. Quítela o elija otra localidad.")
    else:
        st.session_state.cola_localidades.append(
            entrada_desde_formulario(localidad, archivo_contratos, archivo_matriz)
        )
        st.session_state.upload_key += 1
        st.session_state.select_localidad = SELECCION_LOCALIDAD
        st.toast(f"{localidad} añadido a la cola", icon="➕")
        st.rerun()

# ── Cola pendiente ─────────────────────────────────────────────────────────────
cola = st.session_state.cola_localidades
if cola:
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
            st.rerun()

if st.session_state.get("iniciar_consolidacion"):
    st.session_state.iniciar_consolidacion = False
    procesar_consolidacion(
        st.session_state.cola_ejecucion,
        st.session_state.pwd_matriz,
    )

# ── Resultados ─────────────────────────────────────────────────────────────────
if st.session_state.processed:
    stats = st.session_state.file_stats
    informe = st.session_state.get("cruce_informe", [])
    titulo_mes = st.session_state.get("titulo_saldo_corte", "")
    etiqueta_cxp = titulo_mes or "Saldo de corte"

    st.markdown('<p class="section-title">Resultado consolidado</p>', unsafe_allow_html=True)
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

    st.markdown(
        '<p class="section-title">Informe de cruce Matriz → Contratos</p>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Clave principal: nombre + contrato + año + apropiación. "
        "Si falla, se busca por nombre + contrato + año y se desempata con SALDO FINAL "
        "(columna junto a MONTO LIBERACIONES O FENECICMIENTOS). Si todos los duplicados "
        "en Matriz tienen saldo 0, se asigna 0."
    )

    resumen_global = st.session_state.get("cruce_resumen_global", [])
    if resumen_global:
        st.markdown("**Resumen global**")
        df_rg = pd.DataFrame(resumen_global)
        total_rg = df_rg["Contratos"].sum()
        st.dataframe(df_rg, use_container_width=True, hide_index=True)
        st.markdown(
            f"**Total: {int(total_rg)}/{int(total_contratos)}** contratos con saldo asignado "
            f"en la columna **{titulo_mes}**."
        )

    for loc_info in informe:
        loc = loc_info["localidad"]
        st.markdown(f"**{loc}** — columna «{loc_info['columna_mes']}» ({loc_info['accion_columna']})")
        if loc_info.get("resumen_metodos"):
            st.dataframe(
                pd.DataFrame(loc_info["resumen_metodos"]),
                use_container_width=True,
                hide_index=True,
            )
        fallback = loc_info.get("conteo", {}).get("match_saldo_contrato", 0)
        if fallback:
            detalle_loc = [
                d for d in st.session_state.get("cruce_detalle", [])
                if d.get("Localidad") == loc
                and d.get("Método") == METODOS_LABEL["match_saldo_contrato"]
            ]
            if detalle_loc:
                with st.expander(f"Fallback por Saldo Final ({fallback}) — {loc}"):
                    st.markdown(
                        "La apropiación en Contratos no coincide con la Matriz actualizada; "
                        "se tomó la fila cuyo **Saldo Final** en Matriz coincide con "
                        "**SALDO FINAL** del contrato."
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

    detalle_todo = st.session_state.get("cruce_detalle", [])
    descargas_ok = consolidacion_lista_para_descarga()

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
        st.markdown('<p class="section-title">Archivos procesados</p>', unsafe_allow_html=True)
        cols_show = [c for c in ["Localidad", "Archivo", "Nombre", "Filas", "CXP (suma mes)", f"Columna {titulo_mes}"] if c in pd.DataFrame(stats).columns]
        st.dataframe(pd.DataFrame(stats)[cols_show], use_container_width=True, hide_index=True)

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
        datos_dl, nombre_dl, mime_dl = empaquetar_descarga_contratos(contratos_act, fecha_dl)
        st.download_button(
            label="Descargar Contratos actualizados (ZIP)",
            data=datos_dl,
            file_name=nombre_dl,
            mime=mime_dl,
            key="dl_contratos_todas",
            use_container_width=True,
            disabled=not descargas_ok,
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
            df_export = (
                st.session_state.consolidated_df
                if st.session_state.consolidated_df is not None
                else pd.DataFrame()
            )
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

if st.session_state.get("abrir_dialogo"):
    dialogo_contrasena_matriz()
