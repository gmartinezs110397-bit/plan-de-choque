"""Actualización de la pestaña Suspendidos (seguimiento mensual desde Matriz)."""

from __future__ import annotations

import re
from copy import copy
from datetime import date, datetime
from typing import Any

from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter

from constantes import HOJAS_SUSPENDIDOS
from cxp_cruce import (
    FILA_CONTEO_CONTRATOS,
    FILA_SUMA_CONTRATOS,
    MESES_ES,
    _celda_tiene_formula,
    _columna,
    _copiar_estilo_celda,
    _fecha_datetime,
    _fila_encabezado_contratos,
    _fila_inicio_datos_contratos,
    _fila_tiene_contratista,
    _indice_columna_en_hoja,
    _normalizar,
    _ultima_columna_con_datos,
    clave_tres,
    preparar_indice_matriz,
)

FILL_VERDE_NEON = PatternFill(fill_type="solid", fgColor="CCFF00")
FILL_AMARILLO = PatternFill(fill_type="solid", fgColor="FFFF00")
FILL_ENCABEZADO_AZUL = PatternFill(fill_type="solid", fgColor="BDD7EE")
FILL_ENCABEZADO_AMARILLO = PatternFill(fill_type="solid", fgColor="FFF2CC")

_MESES_POR_NOMBRE = {_normalizar(m): i + 1 for i, m in enumerate(MESES_ES)}

_RGB_AZUL_ENCABEZADO = (
    "BDD7EE",
    "9BC2E6",
    "8DB4E2",
    "4472C4",
    "5B9BD5",
    "DDEBF7",
    "DAEEF3",
    "C5D9F1",
)
_RGB_AMARILLO_ENCABEZADO = (
    "FFF2CC",
    "FFFF00",
    "FFEB9C",
    "FFC000",
    "FFE699",
    "FFF9C4",
    "FCE4D6",
)


def resolver_hoja_suspendidos(nombres_hojas: list[str]) -> str | None:
    for candidato in HOJAS_SUSPENDIDOS:
        if candidato in nombres_hojas:
            return candidato
    for nombre in nombres_hojas:
        if _normalizar(nombre) == "suspendidos":
            return nombre
    return None


def titulo_saldo_suspendidos(fecha: datetime | date) -> str:
    mes = MESES_ES[_fecha_datetime(fecha).month - 1].upper()
    return f"SALDO {mes}"


def titulo_estado_suspendidos(fecha: datetime | date) -> str:
    mes = MESES_ES[_fecha_datetime(fecha).month - 1].upper()
    return f"ESTADO ACTUAL {mes}"


def _titulos_saldo_equivalentes(fecha: datetime | date) -> tuple[str, ...]:
    mes = MESES_ES[_fecha_datetime(fecha).month - 1].upper()
    return (
        titulo_saldo_suspendidos(fecha),
        mes,
        f"SALDO ({mes})",
        f"SALDO A {mes}",
    )


def _titulos_estado_equivalentes(fecha: datetime | date) -> tuple[str, ...]:
    mes = MESES_ES[_fecha_datetime(fecha).month - 1].upper()
    return (
        titulo_estado_suspendidos(fecha),
        f"ESTADO ACTUAL ({mes})",
        f"ESTADO ACTUAL A {mes}",
    )


def preparar_mapa_k3_saldo_estado(
    df_matriz,
    localidad: str,
) -> dict[str, dict[str, Any]]:
    """Por clave nombre+contrato+año: suma de saldos en Matriz y estado representativo."""
    df_loc, _, grupos_k3 = preparar_indice_matriz(df_matriz, localidad)
    col_estado = _columna(
        df_loc,
        "ESTADO ACTUAL",
        "Estado Actual",
        "Estado",
        "ESTADO",
    )
    mapa: dict[str, dict[str, Any]] = {}
    for k3, grupo in grupos_k3.items():
        saldo = float(grupo["_saldo"].sum())
        estado = ""
        if col_estado:
            g = grupo.copy()
            g["_abs"] = g["_saldo"].abs()
            fila_ref = g.loc[g["_abs"].idxmax()]
            raw = fila_ref[col_estado]
            if raw is not None and str(raw).strip():
                estado = str(raw).strip()
        mapa[k3] = {"saldo": saldo, "estado": estado}
    return mapa


def _mes_desde_titulo(titulo: str) -> int | None:
    norm = _normalizar(str(titulo or ""))
    if not norm:
        return None

    m = re.search(r"\(([^)]+)\)", norm)
    if m:
        mes = _MESES_POR_NOMBRE.get(_normalizar(m.group(1)))
        if mes:
            return mes

    for prefijo in ("estado actual ", "estado actual a ", "saldo "):
        if norm.startswith(prefijo):
            resto = norm[len(prefijo) :].strip()
            mes = _MESES_POR_NOMBRE.get(resto)
            if mes:
                return mes

    if norm in _MESES_POR_NOMBRE:
        return _MESES_POR_NOMBRE[norm]

    if norm.startswith("saldo a "):
        for mes_nombre, num in _MESES_POR_NOMBRE.items():
            if mes_nombre in norm:
                return num
    return None


def _es_columna_saldo_mes(titulo: str) -> bool:
    norm = _normalizar(str(titulo or ""))
    if not norm:
        return False
    if norm.startswith("estado actual"):
        return False
    if "responsable" in norm or "nombre" in norm:
        return False
    mes = _mes_desde_titulo(titulo)
    return mes is not None and (
        norm == mes
        or norm.startswith("saldo ")
        or norm.startswith("saldo a ")
        or norm in _MESES_POR_NOMBRE
    )


def _es_columna_estado_mes(titulo: str) -> bool:
    norm = _normalizar(str(titulo or ""))
    return norm.startswith("estado actual") and _mes_desde_titulo(titulo) is not None


def _listar_pares_mes_seguimiento(ws) -> list[tuple[int, int, int]]:
    """(col_saldo, col_estado, número de mes) ordenados por mes."""
    fila_hdr = _fila_encabezado_contratos()
    saldos: dict[int, int] = {}
    estados: dict[int, int] = {}

    for col in range(1, ws.max_column + 1):
        val = ws.cell(fila_hdr, col).value
        if val is None or not str(val).strip():
            continue
        titulo = str(val).strip()
        mes = _mes_desde_titulo(titulo)
        if mes is None:
            continue
        if _es_columna_estado_mes(titulo):
            estados[mes] = col
        elif _es_columna_saldo_mes(titulo):
            saldos[mes] = col

    pares: list[tuple[int, int, int]] = []
    for mes in sorted(set(saldos) | set(estados)):
        col_s = saldos.get(mes)
        col_e = estados.get(mes)
        if col_s and col_e:
            pares.append((col_s, col_e, mes))
    return pares


def _indice_columna_titulos(ws, titulos: tuple[str, ...]) -> int | None:
    fila_hdr = _fila_encabezado_contratos()
    objetivos = {_normalizar(t) for t in titulos}
    for col in range(1, ws.max_column + 1):
        val = ws.cell(fila_hdr, col).value
        if val is not None and _normalizar(str(val)) in objetivos:
            return col
    return None


def _par_mes_anterior(
    ws,
    fecha: datetime | date,
    col_saldo: int,
    col_estado: int,
) -> tuple[int | None, int | None]:
    mes_actual = _fecha_datetime(fecha).month
    pares = _listar_pares_mes_seguimiento(ws)
    previas = [p for p in pares if p[2] < mes_actual]
    if previas:
        return previas[-1][0], previas[-1][1]

    if pares:
        idx_actual = next(
            (i for i, p in enumerate(pares) if p[0] == col_saldo and p[1] == col_estado),
            None,
        )
        if idx_actual is not None and idx_actual > 0:
            return pares[idx_actual - 1][0], pares[idx_actual - 1][1]
        if pares[-1][0] != col_saldo:
            return pares[-1][0], pares[-1][1]
        if len(pares) >= 2:
            return pares[-2][0], pares[-2][1]
    return None, None


def _rgb_celda(celda) -> str:
    color = celda.fill.fgColor if celda.fill else None
    rgb = getattr(color, "rgb", None) if color else None
    if not rgb:
        return ""
    s = str(rgb).upper()
    if len(s) == 8:
        return s[2:]
    return s


def _es_fill_azul_encabezado(celda) -> bool:
    rgb = _rgb_celda(celda)
    if not rgb:
        return False
    return any(a in rgb for a in _RGB_AZUL_ENCABEZADO)


def _es_fill_amarillo_encabezado(celda) -> bool:
    rgb = _rgb_celda(celda)
    if not rgb:
        return False
    return any(a in rgb for a in _RGB_AMARILLO_ENCABEZADO)


def _fill_encabezado_alterno(celda_referencia) -> PatternFill:
    if _es_fill_azul_encabezado(celda_referencia):
        return FILL_ENCABEZADO_AMARILLO
    if _es_fill_amarillo_encabezado(celda_referencia):
        return FILL_ENCABEZADO_AZUL
    rgb = _rgb_celda(celda_referencia)
    if rgb:
        return FILL_ENCABEZADO_AMARILLO
    return FILL_ENCABEZADO_AZUL


def _copiar_estilo_columna(
    ws,
    col_origen: int,
    col_destino: int,
    fila_desde: int = 1,
    fila_hasta: int | None = None,
) -> None:
    if fila_hasta is None:
        fila_hasta = ws.max_row
    for fila in range(fila_desde, fila_hasta + 1):
        _copiar_estilo_celda(ws.cell(fila, col_origen), ws.cell(fila, col_destino))


def _aplicar_titulos_encabezado_mes(
    ws,
    col_saldo: int,
    col_estado: int,
    fecha: datetime | date,
    col_prev_saldo: int | None,
    col_prev_estado: int | None,
) -> None:
    fila_hdr = _fila_encabezado_contratos()
    titulo_saldo = titulo_saldo_suspendidos(fecha)
    titulo_estado = titulo_estado_suspendidos(fecha)

    ws.cell(fila_hdr, col_saldo, value=titulo_saldo)
    ws.cell(fila_hdr, col_estado, value=titulo_estado)

    ref = None
    if col_prev_estado:
        ref = ws.cell(fila_hdr, col_prev_estado)
    elif col_prev_saldo:
        ref = ws.cell(fila_hdr, col_prev_saldo)

    fill_titulo = _fill_encabezado_alterno(ref) if ref else FILL_ENCABEZADO_AZUL
    ws.cell(fila_hdr, col_saldo).fill = fill_titulo
    ws.cell(fila_hdr, col_estado).fill = fill_titulo


def _es_suspendido(valor) -> bool:
    return "suspendido" in _normalizar(str(valor or ""))


def _celda_tiene_relleno_verde(celda) -> bool:
    fill = celda.fill
    if not fill or fill.fill_type != "solid":
        return False
    color = fill.fgColor
    rgb = getattr(color, "rgb", None) if color else None
    if not rgb:
        return False
    s = str(rgb).upper()
    verdes = ("CCFF00", "39FF14", "00FF00", "92D050", "C6EFCE", "00B050")
    return any(v in s for v in verdes)


def _celda_tiene_relleno_amarillo(celda) -> bool:
    fill = celda.fill
    if not fill or fill.fill_type != "solid":
        return False
    rgb = getattr(fill.fgColor, "rgb", None) if fill.fgColor else None
    if not rgb:
        return False
    s = str(rgb).upper()
    return "FFFF00" in s or "FFEB9C" in s or "FFC000" in s


def _asegurar_columnas_mes(
    ws,
    fecha: datetime | date,
) -> tuple[int, int, int | None, int | None, bool]:
    """
    Devuelve (col_saldo, col_estado, col_prev_saldo, col_prev_estado, columnas_nuevas).
    """
    col_saldo = _indice_columna_titulos(ws, _titulos_saldo_equivalentes(fecha))
    col_estado = _indice_columna_titulos(ws, _titulos_estado_equivalentes(fecha))
    columnas_nuevas = col_saldo is None or col_estado is None

    col_prev_saldo, col_prev_estado = _par_mes_anterior(
        ws, fecha, col_saldo or 0, col_estado or 0
    )

    siguiente = _ultima_columna_con_datos(ws) + 1
    if col_saldo is None:
        col_saldo = siguiente
        siguiente += 1
    if col_estado is None:
        col_estado = siguiente

    fila_hdr = _fila_encabezado_contratos()

    if columnas_nuevas and col_prev_saldo and col_prev_estado:
        _copiar_estilo_columna(ws, col_prev_saldo, col_saldo)
        _copiar_estilo_columna(ws, col_prev_estado, col_estado)
    elif columnas_nuevas:
        col_estilo = _indice_columna_en_hoja(ws, "ESTADO ACTUAL") or col_prev_estado
        if col_estilo:
            _copiar_estilo_columna(ws, col_estilo, col_estado)
        col_sf = _indice_columna_en_hoja(ws, "SALDO FINAL", "Saldo Final")
        if col_sf:
            _copiar_estilo_columna(ws, col_sf, col_saldo)

    if columnas_nuevas or (
        _normalizar(str(ws.cell(fila_hdr, col_saldo).value or ""))
        != _normalizar(titulo_saldo_suspendidos(fecha))
    ):
        _aplicar_titulos_encabezado_mes(
            ws, col_saldo, col_estado, fecha, col_prev_saldo, col_prev_estado
        )

    if columnas_nuevas and col_prev_saldo and col_prev_estado:
        for fila in (FILA_CONTEO_CONTRATOS, FILA_SUMA_CONTRATOS):
            _copiar_estilo_celda(ws.cell(fila, col_prev_saldo), ws.cell(fila, col_saldo))
            _copiar_estilo_celda(ws.cell(fila, col_prev_estado), ws.cell(fila, col_estado))

    if not col_prev_saldo or not col_prev_estado:
        col_prev_saldo, col_prev_estado = _par_mes_anterior(
            ws, fecha, col_saldo, col_estado
        )

    return col_saldo, col_estado, col_prev_saldo, col_prev_estado, columnas_nuevas


def _resolver_relleno_estado(
    prev_estado,
    prev_celda,
    curr_estado,
) -> PatternFill | None:
    prev_txt = str(prev_estado or "").strip()
    curr_txt = str(curr_estado or "").strip()
    prev_susp = _es_suspendido(prev_txt)
    curr_susp = _es_suspendido(curr_txt)
    prev_verde = _celda_tiene_relleno_verde(prev_celda) if prev_celda else False
    prev_amarillo = _celda_tiene_relleno_amarillo(prev_celda) if prev_celda else False

    if _normalizar(prev_txt) == _normalizar(curr_txt):
        if prev_verde and not curr_susp:
            return FILL_VERDE_NEON
        if prev_amarillo and curr_susp:
            return FILL_AMARILLO
        return None

    if not curr_susp:
        return FILL_VERDE_NEON

    if prev_verde or (prev_txt and not prev_susp):
        return FILL_AMARILLO

    if not prev_susp and prev_txt:
        return FILL_AMARILLO

    return None


def _conteo_suspendidos_en_columna(ws, col_estado: int) -> int:
    col_nombre = _indice_columna_en_hoja(ws, "NOMBRE CONTRATISTA")
    fila_ini = _fila_inicio_datos_contratos()
    total = 0
    for fila in range(fila_ini, ws.max_row + 1):
        if col_nombre and not _fila_tiene_contratista(ws, fila, col_nombre):
            continue
        if _es_suspendido(ws.cell(fila, col_estado).value):
            total += 1
    return total


def _conteo_suspendidos_mes_anterior(
    ws,
    col_prev_estado: int | None,
) -> int | None:
    if not col_prev_estado:
        return None
    celda_prev = ws.cell(FILA_CONTEO_CONTRATOS, col_prev_estado)
    if celda_prev.value not in (None, ""):
        try:
            return int(float(celda_prev.value))
        except (TypeError, ValueError):
            pass
    return _conteo_suspendidos_en_columna(ws, col_prev_estado)


def _suma_saldos_columna(ws, col_saldo: int) -> float:
    col_nombre = _indice_columna_en_hoja(ws, "NOMBRE CONTRATISTA")
    fila_ini = _fila_inicio_datos_contratos()
    suma = 0.0
    for fila in range(fila_ini, ws.max_row + 1):
        if col_nombre and not _fila_tiene_contratista(ws, fila, col_nombre):
            continue
        raw = ws.cell(fila, col_saldo).value
        if raw is None or raw == "":
            continue
        try:
            suma += float(raw)
        except (TypeError, ValueError):
            continue
    return suma


def _actualizar_resumen_suspendidos(
    ws,
    col_saldo: int,
    col_estado: int,
    col_prev_saldo: int | None,
    col_prev_estado: int | None,
) -> tuple[int, int]:
    """Fila 1: conteo suspendidos (sin color). Fila 2: suma saldos. Devuelve (real, mostrado)."""
    conteo_real = _conteo_suspendidos_en_columna(ws, col_estado)
    conteo_prev = _conteo_suspendidos_mes_anterior(ws, col_prev_estado)
    conteo_mostrar = conteo_real
    if conteo_prev is not None and conteo_real > conteo_prev:
        conteo_mostrar = conteo_prev

    suma = _suma_saldos_columna(ws, col_saldo)

    celda_conteo = ws.cell(FILA_CONTEO_CONTRATOS, col_estado)
    celda_suma = ws.cell(FILA_SUMA_CONTRATOS, col_saldo)

    if col_prev_estado:
        _copiar_estilo_celda(
            ws.cell(FILA_CONTEO_CONTRATOS, col_prev_estado),
            celda_conteo,
        )
    if col_prev_saldo:
        _copiar_estilo_celda(
            ws.cell(FILA_SUMA_CONTRATOS, col_prev_saldo),
            celda_suma,
        )

    if not _celda_tiene_formula(celda_conteo):
        celda_conteo.value = conteo_mostrar
        celda_conteo.fill = PatternFill(fill_type=None)

    if not _celda_tiene_formula(celda_suma):
        celda_suma.value = suma

    return conteo_real, conteo_mostrar


def _autoajustar_columna_suspendidos(ws, col: int, titulo: str = "") -> None:
    from cxp_cruce import _autoajustar_ancho_columna

    _autoajustar_ancho_columna(ws, col)
    if titulo:
        letra = get_column_letter(col)
        min_titulo = min(max(len(titulo) * 1.15 + 3, 11), 60)
        ws.column_dimensions[letra].width = max(
            ws.column_dimensions[letra].width or 0,
            min_titulo,
        )


def actualizar_hoja_suspendidos(
    ws,
    mapa_k3: dict[str, dict[str, Any]],
    fecha: datetime | date,
) -> list[str]:
    """
    Escribe SALDO MES y ESTADO ACTUAL MES desde Matriz.
    Colores solo en celdas de estado del mes actual.
    """
    advertencias: list[str] = []
    col_saldo, col_estado, col_prev_saldo, col_prev_estado, _ = _asegurar_columnas_mes(
        ws, fecha
    )

    col_nombre = _indice_columna_en_hoja(ws, "NOMBRE CONTRATISTA")
    col_cto = _indice_columna_en_hoja(
        ws, "No. de Cto", "Número Contrato", "Numero Contrato"
    )
    col_anio = _indice_columna_en_hoja(
        ws,
        "AÑO SUSCRIPCIÓN",
        "ANO SUSCRIPCION",
        "Año Suscripción",
        "Ano Suscripcion",
    )
    if not all([col_nombre, col_cto, col_anio]):
        raise ValueError(
            "Suspendidos: faltan columnas NOMBRE CONTRATISTA, No. de Cto o AÑO SUSCRIPCIÓN."
        )

    fila_ini = _fila_inicio_datos_contratos()

    for fila in range(fila_ini, ws.max_row + 1):
        if not _fila_tiene_contratista(ws, fila, col_nombre):
            continue

        nombre = ws.cell(fila, col_nombre).value
        contrato = ws.cell(fila, col_cto).value
        anio = ws.cell(fila, col_anio).value
        k3 = clave_tres(nombre, contrato, anio)
        datos = mapa_k3.get(k3, {"saldo": 0.0, "estado": ""})

        celda_saldo = ws.cell(fila, col_saldo)
        celda_estado = ws.cell(fila, col_estado)

        if col_prev_saldo:
            _copiar_estilo_celda(ws.cell(fila, col_prev_saldo), celda_saldo)
        celda_saldo.value = datos["saldo"]

        estado = datos.get("estado", "")
        prev_celda = None
        prev_estado = None
        if col_prev_estado:
            prev_celda = ws.cell(fila, col_prev_estado)
            prev_estado = prev_celda.value
            _copiar_estilo_celda(prev_celda, celda_estado)

        celda_estado.value = estado or None

        relleno = _resolver_relleno_estado(prev_estado, prev_celda, estado)
        if relleno:
            celda_estado.fill = relleno

    conteo_real, conteo_mostrar = _actualizar_resumen_suspendidos(
        ws, col_saldo, col_estado, col_prev_saldo, col_prev_estado
    )

    if col_prev_estado and conteo_real > conteo_mostrar:
        advertencias.append(
            f"Suspendidos: el conteo real ({conteo_real}) supera al mes anterior "
            f"({conteo_mostrar}); en el total se dejó el valor del mes anterior."
        )

    _autoajustar_columna_suspendidos(ws, col_saldo, titulo_saldo_suspendidos(fecha))
    _autoajustar_columna_suspendidos(ws, col_estado, titulo_estado_suspendidos(fecha))

    return advertencias


__all__ = [
    "actualizar_hoja_suspendidos",
    "preparar_mapa_k3_saldo_estado",
    "resolver_hoja_suspendidos",
    "titulo_estado_suspendidos",
    "titulo_saldo_suspendidos",
]
