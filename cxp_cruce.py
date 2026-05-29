"""Cruce Matriz → Contratos (CXP / Saldo Final) y actualización de columna del mes.

Incluye desempate manual: aplicar_desempate_en_contratos (aprox. línea 304).
"""

from __future__ import annotations

import calendar
import re
import unicodedata
from copy import copy
from datetime import date, datetime
from io import BytesIO
from typing import Any

import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from constantes import COL_DESEMPATE_MANUAL

MESES_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

SHEET_CONTRATOS = "Cps por depurar"
HEADER_MATRIZ = 6
HEADER_CONTRATOS = 2
FILA_CONTEO_CONTRATOS = 1
FILA_SUMA_CONTRATOS = 2

METODOS_LABEL = {
    "k4_exacto": "Match exacto (4 campos)",
    "match_saldo_contrato": "Fallback por Saldo Final",
    "todos_cero_matriz": "Fallback: todos cero en matriz",
    "k3_unico": "Match por contrato (sin apropiación)",
    "verificar": "Sin resolver",
    "sin_matriz": "Sin fila en matriz",
    "desempate_manual": "Desempate manual",
}

CODIGOS_SIN_RESOLVER = ("verificar", "sin_matriz")
LABELS_SIN_RESOLVER = {METODOS_LABEL[c] for c in CODIGOS_SIN_RESOLVER}
LABEL_A_CODIGO = {v: k for k, v in METODOS_LABEL.items()}

TIPO_FILA_CONTRATOS = "Contratos"
TIPO_FILA_CANDIDATO_MATRIZ = "Candidato Matriz"
COL_OPCION_MATRIZ = "Opción Matriz"


def _normalizar(texto: str) -> str:
    texto = str(texto).lower()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _norm_num(valor) -> str:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    if isinstance(valor, float) and valor == int(valor):
        return str(int(valor))
    return str(valor).strip()


def clave_cuatro(nombre, contrato, anio, apropiacion) -> str:
    n = re.sub(r"\s+", "", str(nombre).upper())
    return n + _norm_num(contrato) + _norm_num(anio) + _norm_num(apropiacion)


def clave_tres(nombre, contrato, anio) -> str:
    n = re.sub(r"\s+", "", str(nombre).upper())
    return n + _norm_num(contrato) + _norm_num(anio)


def _palabras_localidad(localidad: str) -> list[str]:
    palabras = re.findall(r"[a-z0-9]+", _normalizar(localidad))
    ignorar = {"de", "la", "los", "las", "el", "del", "y"}
    significativas = [p for p in palabras if p not in ignorar and len(p) >= 2]
    return significativas if significativas else palabras


def fila_coincide_localidad(valor_celda, localidad: str) -> bool:
    texto = _normalizar(str(valor_celda))
    return any(p in texto for p in _palabras_localidad(localidad))


def _columna(df: pd.DataFrame, *candidatos: str) -> str | None:
    mapa = {_normalizar(c): c for c in df.columns}
    for cand in candidatos:
        key = _normalizar(cand)
        if key in mapa:
            return mapa[key]
    return None


def preparar_indice_matriz(df_matriz: pd.DataFrame, localidad: str) -> tuple[pd.DataFrame, dict, dict]:
    col_loc = _columna(df_matriz, "Localidad", "LOCALIDAD") or df_matriz.columns[0]
    df_loc = df_matriz[df_matriz[col_loc].apply(lambda v: fila_coincide_localidad(v, localidad))].copy()

    col_nombre = _columna(df_matriz, "NOMBRE CONTRATISTA")
    col_cto = _columna(df_matriz, "Número Contrato", "Numero Contrato")
    col_anio = _columna(df_matriz, "Año Suscripción", "Ano Suscripcion")
    col_aprop = _columna(df_matriz, "Apropiación", "Apropiacion")
    col_saldo = _columna(df_matriz, "Saldo Final")

    if not all([col_nombre, col_cto, col_anio, col_aprop, col_saldo]):
        raise ValueError("La Matriz no tiene las columnas esperadas para el cruce.")

    df_loc["_k4"] = df_loc.apply(
        lambda r: clave_cuatro(r[col_nombre], r[col_cto], r[col_anio], r[col_aprop]),
        axis=1,
    )
    df_loc["_k3"] = df_loc.apply(
        lambda r: clave_tres(r[col_nombre], r[col_cto], r[col_anio]),
        axis=1,
    )
    df_loc["_saldo"] = pd.to_numeric(df_loc[col_saldo], errors="coerce").fillna(0)

    mapa_k4 = df_loc.drop_duplicates("_k4", keep="first").set_index("_k4")["_saldo"].to_dict()
    grupos_k3 = {k: g for k, g in df_loc.groupby("_k3", sort=False)}
    return df_loc, mapa_k4, grupos_k3


def buscar_saldo_matriz(
    mapa_k4: dict,
    grupos_k3: dict,
    nombre,
    contrato,
    anio,
    apropiacion,
    saldo_final_contrato,
) -> tuple[float | None, str, str]:
    """
    Devuelve (saldo_matriz, metodo_codigo, detalle_texto).
    """
    k4 = clave_cuatro(nombre, contrato, anio, apropiacion)
    if k4 in mapa_k4:
        return float(mapa_k4[k4]), "k4_exacto", ""

    k3 = clave_tres(nombre, contrato, anio)
    if k3 not in grupos_k3:
        return None, "sin_matriz", "No hay fila en la Matriz para este contrato."

    g = grupos_k3[k3]
    if len(g) == 1:
        return float(g.iloc[0]["_saldo"]), "k3_unico", "Apropiación en Matriz distinta; una sola fila."

    sf = g["_saldo"]
    if (sf > 0).sum() == 0:
        return 0.0, "todos_cero_matriz", "Varias filas en Matriz, todas con saldo 0."

    sk = float(pd.to_numeric(saldo_final_contrato, errors="coerce") or 0)
    coinciden = g[sf == sk]
    if len(coinciden) == 1:
        detalle = (
            f"Apropiación en Contratos ({_norm_num(apropiacion)}) distinta a la Matriz; "
            f"se usó SALDO FINAL del contrato ({sk:,.0f})."
        )
        return float(coinciden.iloc[0]["_saldo"]), "match_saldo_contrato", detalle
    if len(coinciden) > 1:
        return float(coinciden.iloc[0]["_saldo"]), "match_saldo_contrato", "Varias filas con el mismo saldo."

    return (
        None,
        "verificar",
        "Hay saldos > 0 en Matriz pero ninguno coincide con SALDO FINAL del contrato.",
    )


def clave_fila_contrato(nombre, contrato, anio, apropiacion) -> str:
    return clave_cuatro(nombre, contrato, anio, apropiacion)


def clave_desde_detalle(fila: dict) -> str:
    return clave_fila_contrato(
        fila["NOMBRE CONTRATISTA"],
        fila["No. de Cto"],
        fila["AÑO SUSCRIPCIÓN"],
        fila["APROPIACION DISPONIBLE"],
    )


def _es_fila_contratos_revision(fila: dict) -> bool:
    return fila.get("Tipo fila", TIPO_FILA_CONTRATOS) == TIPO_FILA_CONTRATOS


def _listar_opciones_matriz(grupo: pd.DataFrame) -> list[dict]:
    """Filas en Matriz con mismo nombre + contrato + año (sin apropiación)."""
    col_aprop = _columna(grupo, "APROPIACION DISPONIBLE", "Apropiación", "Apropiacion")
    if not col_aprop:
        return []
    opciones = []
    for n, (_, row) in enumerate(grupo.iterrows(), 1):
        opciones.append({
            "opcion": n,
            "apropiacion": row[col_aprop],
            "saldo": float(row["_saldo"]),
        })
    return opciones


def construir_dataframe_revision(
    detalle_filas: list[dict],
    localidad: str | None = None,
) -> pd.DataFrame:
    """
    Lista a revisar: fila del Contrato + candidatos en Matriz (misma búsqueda k3).
    «Desempate manual» solo en la fila Contratos (saldo elegido para el mes).
    """
    pendientes = [
        f
        for f in detalle_filas
        if f.get("Método") in LABELS_SIN_RESOLVER
        and _es_fila_contratos_revision(f)
        and (localidad is None or f.get("Localidad") == localidad)
    ]
    if not pendientes:
        return pd.DataFrame()

    filas_export: list[dict] = []
    for f in pendientes:
        titulo_mes_col = next(
            (c for c in f if str(c).startswith("Saldo Matriz (")),
            f"Saldo Matriz",
        )
        fila_contratos = {
            "Tipo fila": TIPO_FILA_CONTRATOS,
            COL_OPCION_MATRIZ: "—",
            "Localidad": f.get("Localidad"),
            "NOMBRE CONTRATISTA": f.get("NOMBRE CONTRATISTA"),
            "No. de Cto": f.get("No. de Cto"),
            "AÑO SUSCRIPCIÓN": f.get("AÑO SUSCRIPCIÓN"),
            "APROPIACION DISPONIBLE": f.get("APROPIACION DISPONIBLE"),
            "SALDO FINAL (Contratos)": f.get("SALDO FINAL (Contratos)"),
            "Método": f.get("Método"),
            "Detalle": f.get("Detalle"),
            titulo_mes_col: f.get(titulo_mes_col),
            COL_DESEMPATE_MANUAL: "",
        }
        filas_export.append(fila_contratos)

        candidatos = f.get("candidatos_matriz") or []
        for cand in candidatos:
            filas_export.append({
                "Tipo fila": TIPO_FILA_CANDIDATO_MATRIZ,
                COL_OPCION_MATRIZ: cand.get("opcion"),
                "Localidad": f.get("Localidad"),
                "NOMBRE CONTRATISTA": f.get("NOMBRE CONTRATISTA"),
                "No. de Cto": f.get("No. de Cto"),
                "AÑO SUSCRIPCIÓN": f.get("AÑO SUSCRIPCIÓN"),
                "APROPIACION DISPONIBLE": cand.get("apropiacion"),
                "SALDO FINAL (Contratos)": f.get("SALDO FINAL (Contratos)"),
                "Método": "—",
                "Detalle": "Opción en Matriz (referencia; no complete Desempate aquí)",
                titulo_mes_col: cand.get("saldo"),
                COL_DESEMPATE_MANUAL: "",
            })

    preferidas = [
        "Tipo fila",
        COL_OPCION_MATRIZ,
        "Localidad",
        "NOMBRE CONTRATISTA",
        "No. de Cto",
        "AÑO SUSCRIPCIÓN",
        "APROPIACION DISPONIBLE",
        "SALDO FINAL (Contratos)",
        "Método",
        "Detalle",
    ]
    df = pd.DataFrame(filas_export)
    cols_matriz = [c for c in df.columns if str(c).startswith("Saldo Matriz")]
    cols = [c for c in preferidas if c in df.columns] + cols_matriz + [COL_DESEMPATE_MANUAL]
    return df[[c for c in cols if c in df.columns]]


def parsear_mapa_desempate(df_revision: pd.DataFrame) -> dict[str, float]:
    """Lee la columna Desempate manual (solo filas con valor numérico)."""
    col_d = _columna(df_revision, COL_DESEMPATE_MANUAL, "Desempate Manual")
    if not col_d:
        raise ValueError(f"Falta la columna «{COL_DESEMPATE_MANUAL}» en el archivo subido.")

    col_nombre = _columna(df_revision, "NOMBRE CONTRATISTA")
    col_cto = _columna(df_revision, "No. de Cto", "Número Contrato")
    col_anio = _columna(df_revision, "AÑO SUSCRIPCIÓN", "Año Suscripción")
    col_aprop = _columna(df_revision, "APROPIACION DISPONIBLE", "Apropiación")
    if not all([col_nombre, col_cto, col_anio, col_aprop]):
        raise ValueError(
            "El archivo debe conservar las columnas del listado: "
            "NOMBRE CONTRATISTA, No. de Cto, AÑO SUSCRIPCIÓN, APROPIACION DISPONIBLE."
        )

    col_tipo = _columna(df_revision, "Tipo fila", "Tipo Fila")
    mapa: dict[str, float] = {}
    for idx, row in df_revision.iterrows():
        if col_tipo and str(row.get(col_tipo, "")).strip() == TIPO_FILA_CANDIDATO_MATRIZ:
            continue
        raw = row[col_d]
        if raw is None or (isinstance(raw, float) and pd.isna(raw)) or str(raw).strip() == "":
            continue
        saldo = pd.to_numeric(raw, errors="coerce")
        if pd.isna(saldo):
            raise ValueError(
                f"Fila {int(idx) + 2}: «{COL_DESEMPATE_MANUAL}» debe ser un número "
                f"(valor recibido: {raw!r})."
            )
        k = clave_fila_contrato(
            row[col_nombre], row[col_cto], row[col_anio], row[col_aprop]
        )
        mapa[k] = float(saldo)
    return mapa


def claves_pendientes_localidad(detalle_filas: list[dict], localidad: str) -> set[str]:
    return {
        clave_desde_detalle(f)
        for f in detalle_filas
        if f.get("Localidad") == localidad
        and f.get("Método") in LABELS_SIN_RESOLVER
        and _es_fila_contratos_revision(f)
    }


def validar_desempate_completo(
    pendientes: set[str],
    mapa: dict[str, float],
    detalle_localidad: list[dict] | None = None,
) -> list[str]:
    por_clave = {
        clave_desde_detalle(f): f
        for f in (detalle_localidad or [])
        if f.get("Método") in LABELS_SIN_RESOLVER and _es_fila_contratos_revision(f)
    }
    errores = []
    for k in sorted(pendientes):
        if k not in mapa:
            fila = por_clave.get(k, {})
            nombre = fila.get("NOMBRE CONTRATISTA", "Contrato")
            cto = fila.get("No. de Cto", "")
            errores.append(
                f"**{nombre}** (contrato {cto}): complete «{COL_DESEMPATE_MANUAL}»."
            )
    return errores


def _etiqueta_saldo_matriz(titulo_mes: str) -> str:
    return f"Saldo Matriz ({titulo_mes})"


def recalcular_estadisticas_localidad(
    detalle_filas: list[dict],
    titulo_mes: str,
) -> dict[str, Any]:
    col_saldo = _etiqueta_saldo_matriz(titulo_mes)
    conteo: dict[str, int] = {k: 0 for k in METODOS_LABEL}
    saldos_mes: list[float] = []

    for fila in detalle_filas:
        codigo = LABEL_A_CODIGO.get(fila.get("Método", ""), "verificar")
        conteo[codigo] = conteo.get(codigo, 0) + 1
        if codigo not in CODIGOS_SIN_RESOLVER:
            saldo = fila.get(col_saldo)
            if saldo is not None and not (isinstance(saldo, float) and pd.isna(saldo)):
                saldos_mes.append(float(saldo))

    total = sum(conteo.values())
    sin_resolver = sum(conteo.get(c, 0) for c in CODIGOS_SIN_RESOLVER)
    resumen_metodos = [
        {"Método": METODOS_LABEL[codigo], "Contratos": cantidad}
        for codigo, cantidad in sorted(conteo.items(), key=lambda x: -x[1])
        if cantidad > 0
    ]
    return {
        "total_contratos": total,
        "contratos_ok": total - sin_resolver,
        "sin_resolver": sin_resolver,
        "cxp_total": sum(saldos_mes),
        "conteo": conteo,
        "resumen_metodos": resumen_metodos,
    }


def aplicar_desempate_en_contratos(
    contratos_bytes: bytes,
    fecha_analisis: datetime,
    mapa_desempate: dict[str, float],
    detalle_filas: list[dict],
    localidad: str,
) -> tuple[bytes, list[dict]]:
    """
    Escribe saldos manuales en la columna de corte y actualiza el detalle.
    Solo aplica a contratos que siguen «sin resolver».
    """
    titulo_mes = titulo_saldo_corte(fecha_analisis)
    col_saldo_label = _etiqueta_saldo_matriz(titulo_mes)
    pendientes = claves_pendientes_localidad(detalle_filas, localidad)

    df_c = pd.read_excel(
        BytesIO(contratos_bytes), sheet_name=SHEET_CONTRATOS, header=HEADER_CONTRATOS
    )
    col_nombre = _columna(df_c, "NOMBRE CONTRATISTA")
    col_cto = _columna(df_c, "No. de Cto", "Número Contrato")
    col_anio = _columna(df_c, "AÑO SUSCRIPCIÓN", "ANO SUSCRIPCION", "Año Suscripción")
    col_aprop = _columna(df_c, "APROPIACION DISPONIBLE", "Apropiación", "Apropiacion")
    if not all([col_nombre, col_cto, col_anio, col_aprop]):
        raise ValueError("Contratos: faltan columnas para aplicar el desempate.")

    col_mes_existente = _indice_columna_corte(list(df_c.columns), fecha_analisis)
    col_mes = col_mes_existente or titulo_mes
    crear_columna = col_mes_existente is None

    detalle_nuevo = []
    for fila in detalle_filas:
        if fila.get("Localidad") != localidad:
            detalle_nuevo.append(dict(fila))
            continue
        copia = dict(fila)
        if copia.get("Método") in LABELS_SIN_RESOLVER:
            k = clave_desde_detalle(copia)
            if k in mapa_desempate:
                saldo = mapa_desempate[k]
                copia[col_saldo_label] = saldo
                copia["Método"] = METODOS_LABEL["desempate_manual"]
                copia["Detalle"] = (
                    f"Saldo asignado en «{COL_DESEMPATE_MANUAL}» ({saldo:,.0f})."
                )
        detalle_nuevo.append(copia)

    valores_excel: dict[int, float | None] = {}
    for i, (_, row) in enumerate(df_c.iterrows()):
        nombre = row[col_nombre]
        if pd.isna(nombre) or not str(nombre).strip():
            continue
        fila_excel = _fila_inicio_datos_contratos() + i
        k = clave_fila_contrato(
            nombre, row[col_cto], row[col_anio], row[col_aprop]
        )
        if k in pendientes and k in mapa_desempate:
            valores_excel[fila_excel] = mapa_desempate[k]

    bytes_nuevos = exportar_contratos_preservando_formato(
        contratos_bytes,
        fecha_analisis,
        valores_excel,
        crear_columna=crear_columna,
        titulo_columna=titulo_mes,
    )
    return bytes_nuevos, detalle_nuevo


def _fecha_datetime(fecha: datetime | date) -> datetime:
    if isinstance(fecha, datetime):
        return fecha
    return datetime(fecha.year, fecha.month, fecha.day)


def titulo_saldo_corte(fecha: datetime | date) -> str:
    """
    Título de columna según fecha de ejecución.
    Ej.: Saldo a 31 de mayo, Saldo a 30 de abril (último día del mes).
    """
    f = _fecha_datetime(fecha)
    dia = calendar.monthrange(f.year, f.month)[1]
    mes = MESES_ES[f.month - 1]
    return f"Saldo a {dia} de {mes}"


def titulo_columna_mes(fecha: datetime | date) -> str:
    """Alias del título de corte (compatibilidad)."""
    return titulo_saldo_corte(fecha)


def _fila_encabezado_contratos() -> int:
    """Fila 1-based del encabezado en «Cps por depurar» (fila 3 en Excel)."""
    return HEADER_CONTRATOS + 1


def _fila_inicio_datos_contratos() -> int:
    """Primera fila de datos de contratos (fila 4 en Excel)."""
    return HEADER_CONTRATOS + 2


def _copiar_estilo_celda(origen, destino) -> None:
    if origen.has_style:
        destino.font = copy(origen.font)
        destino.fill = copy(origen.fill)
        destino.border = copy(origen.border)
        destino.alignment = copy(origen.alignment)
        destino.number_format = origen.number_format


def _texto_ancho_celda(celda) -> str:
    """Texto visible aproximado para calcular auto-ancho (como doble clic en Excel)."""
    valor = celda.value
    if valor is None:
        return ""
    if isinstance(valor, float) and not isinstance(valor, bool):
        if abs(valor - round(valor)) < 1e-9:
            valor = int(round(valor))
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        nf = str(celda.number_format or "")
        texto = f"{valor:,}"
        if "." in nf and "," not in nf.replace("#", "").replace("0", ""):
            pass
        if "." in nf or "0.000" in nf.lower():
            texto = texto.replace(",", ".")
        return texto
    return str(valor).strip()


def _autoajustar_ancho_columna(ws, col: int) -> None:
    """
    Ajusta el ancho de la columna al contenido (equivalente a doble clic en el borde).
    Revisa filas 1-2, encabezado y filas de contratos.
    """
    col_nombre = _indice_columna_en_hoja(ws, "NOMBRE CONTRATISTA")
    fila_ini = _fila_inicio_datos_contratos()
    max_len = 0

    for fila in range(1, ws.max_row + 1):
        if fila >= fila_ini and col_nombre and not _fila_tiene_contratista(ws, fila, col_nombre):
            continue
        celda = ws.cell(fila, col)
        texto = _texto_ancho_celda(celda)
        if texto:
            max_len = max(max_len, len(texto))

    # Conversión aproximada a unidades de ancho de Excel (+ margen como AutoFit)
    ancho = min(max(max_len * 1.15 + 3, 11), 60)
    ws.column_dimensions[get_column_letter(col)].width = ancho


def _ajustar_ancho_columna_corte(
    ws,
    col: int,
    col_referencia: int,
    titulo: str = "",
) -> None:
    """Auto-ancho por contenido; no menos que SALDO FINAL si ya era más ancha."""
    _autoajustar_ancho_columna(ws, col)
    letra = get_column_letter(col)
    letra_ref = get_column_letter(col_referencia)
    dim_ref = ws.column_dimensions.get(letra_ref)
    if dim_ref and dim_ref.width:
        actual = ws.column_dimensions[letra].width or 0
        ws.column_dimensions[letra].width = max(actual, dim_ref.width)
    elif titulo:
        ws.column_dimensions[letra].width = max(
            ws.column_dimensions[letra].width or 0,
            min(max(len(titulo) * 1.15 + 3, 11), 60),
        )


def _titulos_columnas_hoja(ws) -> list[str]:
    fila = _fila_encabezado_contratos()
    titulos = []
    for col in range(1, ws.max_column + 1):
        val = ws.cell(fila, col).value
        if val is not None and str(val).strip():
            titulos.append(str(val).strip())
        else:
            titulos.append("")
    return titulos


def _indice_columna_en_hoja(ws, *candidatos: str) -> int | None:
    fila = _fila_encabezado_contratos()
    for col in range(1, ws.max_column + 1):
        val = ws.cell(fila, col).value
        if val is None or not str(val).strip():
            continue
        norm = _normalizar(str(val))
        for cand in candidatos:
            if _normalizar(cand) == norm:
                return col
    return None


def _indice_columna_corte_en_hoja(ws, fecha: datetime | date) -> tuple[int | None, str]:
    titulos = _titulos_columnas_hoja(ws)
    nombre = _indice_columna_corte(titulos, fecha)
    if not nombre:
        return None, titulo_saldo_corte(fecha)
    fila = _fila_encabezado_contratos()
    for col in range(1, ws.max_column + 1):
        if _normalizar(str(ws.cell(fila, col).value)) == _normalizar(nombre):
            return col, nombre
    return None, nombre


def _columna_estilo_saldo_final(ws) -> int:
    """Columna SALDO FINAL (junto a MONTO LIBERACIONES…) para copiar formato."""
    col_sf = _indice_columna_en_hoja(ws, "SALDO FINAL", "Saldo Final")
    if col_sf:
        return col_sf
    col_monto = _indice_columna_en_hoja(
        ws,
        "MONTO LIBERACIONES O FENECICMIENTOS",
        "MONTO LIBERACIONES O FENECICMIENTOS",
        "MONTO LIBERACIONES",
    )
    if col_monto:
        return col_monto + 1
    return _ultima_columna_con_datos(ws)


def _columna_tiene_contenido(ws, col: int) -> bool:
    """True si la columna tiene encabezado, resumen (1-2) o dato de contrato."""
    fila_hdr = _fila_encabezado_contratos()
    hdr = ws.cell(fila_hdr, col).value
    if hdr is not None and str(hdr).strip():
        return True
    for fila in (FILA_CONTEO_CONTRATOS, FILA_SUMA_CONTRATOS):
        if ws.cell(fila, col).value not in (None, ""):
            return True

    col_nombre = _indice_columna_en_hoja(ws, "NOMBRE CONTRATISTA")
    fila_ini = _fila_inicio_datos_contratos()
    for fila in range(fila_ini, ws.max_row + 1):
        if col_nombre and not _fila_tiene_contratista(ws, fila, col_nombre):
            continue
        if ws.cell(fila, col).value not in (None, ""):
            return True
    return False


def _ultima_columna_con_datos(ws) -> int:
    """
    Última columna con información real (no el área vacía tras el filtro de Excel).
    Busca desde la columna 1 hasta SALDO FINAL + margen de columnas mensuales.
    """
    col_sf = _columna_estilo_saldo_final(ws)
    ultima = col_sf
    limite = min(ws.max_column, col_sf + 48)

    for col in range(1, limite + 1):
        if _columna_tiene_contenido(ws, col):
            ultima = max(ultima, col)

    return ultima


def _agregar_columna_corte_en_hoja(ws, titulo: str) -> int:
    """Inserta columna tras la última con datos; estilo copiado de SALDO FINAL."""
    fila_hdr = _fila_encabezado_contratos()
    col_estilo = _columna_estilo_saldo_final(ws)
    nueva_col = _ultima_columna_con_datos(ws) + 1

    _copiar_estilo_celda(ws.cell(fila_hdr, col_estilo), ws.cell(fila_hdr, nueva_col))
    ws.cell(fila_hdr, nueva_col, value=titulo)

    for fila in (FILA_CONTEO_CONTRATOS, FILA_SUMA_CONTRATOS):
        _copiar_estilo_celda(ws.cell(fila, col_estilo), ws.cell(fila, nueva_col))

    return nueva_col


def _fila_tiene_contratista(ws, fila: int, col_nombre: int) -> bool:
    val = ws.cell(fila, col_nombre).value
    return val is not None and str(val).strip() != ""


def _celda_tiene_formula(celda) -> bool:
    if celda.data_type == "f":
        return True
    val = celda.value
    return isinstance(val, str) and val.startswith("=")


def _actualizar_resumen_filas_1_2(ws, col_corte: int) -> None:
    """
    Fila 1: cantidad de contratos con saldo en la columna de corte.
    Fila 2: suma de esos saldos (si no hay fórmula ya definida).
    """
    col_nombre = _indice_columna_en_hoja(ws, "NOMBRE CONTRATISTA")
    fila_ini = _fila_inicio_datos_contratos()
    conteo = 0
    suma = 0.0
    for fila in range(fila_ini, ws.max_row + 1):
        if col_nombre and not _fila_tiene_contratista(ws, fila, col_nombre):
            continue
        raw = ws.cell(fila, col_corte).value
        if raw is None or raw == "":
            continue
        try:
            saldo = float(raw)
        except (TypeError, ValueError):
            continue
        if saldo != 0:
            conteo += 1
        suma += saldo

    col_estilo = _columna_estilo_saldo_final(ws)
    celda_conteo = ws.cell(FILA_CONTEO_CONTRATOS, col_corte)
    celda_suma = ws.cell(FILA_SUMA_CONTRATOS, col_corte)
    if not _celda_tiene_formula(celda_conteo):
        celda_conteo.value = conteo
        _copiar_estilo_celda(ws.cell(FILA_CONTEO_CONTRATOS, col_estilo), celda_conteo)
    if not _celda_tiene_formula(celda_suma):
        celda_suma.value = suma
        _copiar_estilo_celda(ws.cell(FILA_SUMA_CONTRATOS, col_estilo), celda_suma)


def exportar_contratos_preservando_formato(
    contratos_bytes: bytes,
    fecha_analisis: datetime,
    valores_por_fila: dict[int, float | None],
    crear_columna: bool,
    titulo_columna: str,
) -> bytes:
    """
    Guarda el libro original intacto (filas 1-2, formatos, otras hojas).
    Solo escribe la columna de corte en las filas de datos indicadas.
    valores_por_fila: fila Excel 1-based -> saldo.
    """
    wb = load_workbook(BytesIO(contratos_bytes))
    if SHEET_CONTRATOS not in wb.sheetnames:
        raise ValueError(f"Contratos: falta la hoja «{SHEET_CONTRATOS}».")
    ws = wb[SHEET_CONTRATOS]

    titulo_corte = titulo_columna or titulo_saldo_corte(fecha_analisis)
    col_corte, titulo_usado = _indice_columna_corte_en_hoja(ws, fecha_analisis)
    col_estilo = _columna_estilo_saldo_final(ws)
    if col_corte is None:
        col_corte = _agregar_columna_corte_en_hoja(ws, titulo_corte)
    else:
        if crear_columna and titulo_columna:
            ws.cell(_fila_encabezado_contratos(), col_corte, value=titulo_columna)

    col_nombre = _indice_columna_en_hoja(ws, "NOMBRE CONTRATISTA")

    for fila, valor in valores_por_fila.items():
        if col_nombre and not _fila_tiene_contratista(ws, fila, col_nombre):
            continue
        celda = ws.cell(fila, col_corte, value=valor)
        _copiar_estilo_celda(ws.cell(fila, col_estilo), celda)

    _actualizar_resumen_filas_1_2(ws, col_corte)
    _ajustar_ancho_columna_corte(ws, col_corte, col_estilo, titulo_usado or titulo_corte)

    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return out.getvalue()


def _indice_columna_corte(columnas: list, fecha: datetime | date) -> str | None:
    """Busca columna existente: Saldo a 31 de mayo, SALDO A 31 DE MAYO, etc."""
    f = _fecha_datetime(fecha)
    objetivo = _normalizar(titulo_saldo_corte(f))
    for col in columnas:
        if _normalizar(str(col)) == objetivo:
            return col

    dia = str(calendar.monthrange(f.year, f.month)[1])
    mes = _normalizar(MESES_ES[f.month - 1])
    for col in columnas:
        n = _normalizar(str(col))
        if "saldo" in n and dia in n and mes in n:
            return col

    mes_cap = MESES_ES[f.month - 1][:1].upper() + MESES_ES[f.month - 1][1:]
    for col in columnas:
        if _normalizar(str(col)) == _normalizar(mes_cap):
            return col
    return None


def procesar_localidad_cxp(
    contratos_bytes: bytes,
    df_matriz: pd.DataFrame,
    localidad: str,
    fecha_analisis: datetime,
    nombre_contratos: str = "",
    nombre_matriz: str = "",
) -> dict[str, Any]:
    titulo_mes = titulo_saldo_corte(fecha_analisis)
    _, mapa_k4, grupos_k3 = preparar_indice_matriz(df_matriz, localidad)

    libro = pd.ExcelFile(BytesIO(contratos_bytes))
    if SHEET_CONTRATOS not in libro.sheet_names:
        raise ValueError(f"Contratos: falta la hoja «{SHEET_CONTRATOS}».")

    df_c = pd.read_excel(BytesIO(contratos_bytes), sheet_name=SHEET_CONTRATOS, header=HEADER_CONTRATOS)

    col_nombre = _columna(df_c, "NOMBRE CONTRATISTA")
    col_cto = _columna(df_c, "No. de Cto", "Número Contrato", "Numero Contrato")
    col_anio = _columna(df_c, "AÑO SUSCRIPCIÓN", "ANO SUSCRIPCION", "Año Suscripción")
    col_aprop = _columna(df_c, "APROPIACION DISPONIBLE", "Apropiación", "Apropiacion")
    col_saldo_k = _columna(df_c, "SALDO FINAL", "Saldo Final")

    if not all([col_nombre, col_cto, col_anio, col_aprop, col_saldo_k]):
        raise ValueError("Contratos: faltan columnas para el cruce en «Cps por depurar».")

    col_mes_existente = _indice_columna_corte(list(df_c.columns), fecha_analisis)
    if col_mes_existente:
        col_mes = col_mes_existente
        accion_columna = "actualizada"
        crear_columna = False
    else:
        col_mes = titulo_mes
        accion_columna = "creada"
        crear_columna = True

    conteo: dict[str, int] = {k: 0 for k in METODOS_LABEL}
    detalle_filas: list[dict] = []
    saldos_mes: list[float] = []
    valores_excel: dict[int, float | None] = {}

    for i, (_, row) in enumerate(df_c.iterrows()):
        nombre = row[col_nombre]
        if pd.isna(nombre) or not str(nombre).strip():
            continue

        saldo, metodo, texto_det = buscar_saldo_matriz(
            mapa_k4,
            grupos_k3,
            nombre,
            row[col_cto],
            row[col_anio],
            row[col_aprop],
            row[col_saldo_k],
        )
        conteo[metodo] = conteo.get(metodo, 0) + 1
        fila_excel = _fila_inicio_datos_contratos() + i

        if saldo is None:
            valores_excel[fila_excel] = None
            saldo_guardar = None
        else:
            valores_excel[fila_excel] = float(saldo)
            saldo_guardar = saldo
            if metodo != "verificar" and metodo != "sin_matriz":
                saldos_mes.append(float(saldo))

        candidatos_matriz: list[dict] = []
        if metodo == "verificar":
            k3 = clave_tres(nombre, row[col_cto], row[col_anio])
            if k3 in grupos_k3:
                candidatos_matriz = _listar_opciones_matriz(grupos_k3[k3])

        detalle_filas.append({
            "Tipo fila": TIPO_FILA_CONTRATOS,
            "Localidad": localidad,
            "NOMBRE CONTRATISTA": nombre,
            "No. de Cto": row[col_cto],
            "AÑO SUSCRIPCIÓN": row[col_anio],
            "APROPIACION DISPONIBLE": row[col_aprop],
            "SALDO FINAL (Contratos)": row[col_saldo_k],
            f"Saldo Matriz ({titulo_mes})": saldo_guardar,
            "Método": METODOS_LABEL.get(metodo, metodo),
            "Detalle": texto_det,
            "candidatos_matriz": candidatos_matriz,
        })

    out = BytesIO()
    out.write(
        exportar_contratos_preservando_formato(
            contratos_bytes,
            fecha_analisis,
            valores_excel,
            crear_columna=crear_columna,
            titulo_columna=titulo_mes,
        )
    )
    out.seek(0)

    total_contratos = sum(conteo.values())
    resumen_metodos = [
        {
            "Método": METODOS_LABEL.get(codigo, codigo),
            "Contratos": cantidad,
        }
        for codigo, cantidad in sorted(conteo.items(), key=lambda x: -x[1])
        if cantidad > 0
    ]

    sin_resolver = conteo.get("verificar", 0) + conteo.get("sin_matriz", 0)
    ok = total_contratos - sin_resolver

    return {
        "localidad": localidad,
        "nombre_contratos": nombre_contratos,
        "nombre_matriz": nombre_matriz,
        "columna_mes": col_mes,
        "accion_columna": accion_columna,
        "bytes_contratos": out.getvalue(),
        "total_contratos": total_contratos,
        "contratos_ok": ok,
        "sin_resolver": sin_resolver,
        "cxp_total": sum(saldos_mes),
        "conteo": conteo,
        "resumen_metodos": resumen_metodos,
        "detalle": detalle_filas,
    }


__all__ = [
    "COL_DESEMPATE_MANUAL",
    "METODOS_LABEL",
    "aplicar_desempate_en_contratos",
    "buscar_saldo_matriz",
    "claves_pendientes_localidad",
    "construir_dataframe_revision",
    "parsear_mapa_desempate",
    "procesar_localidad_cxp",
    "recalcular_estadisticas_localidad",
    "titulo_saldo_corte",
    "validar_desempate_completo",
]
