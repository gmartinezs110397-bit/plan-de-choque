"""Pestaña Liquidados con saldo: saldo mensual desde Matriz con apropiación (k4)."""

from __future__ import annotations

from datetime import date, datetime

from openpyxl.styles import PatternFill

from constantes import HOJAS_LIQUIDADOS_CON_SALDO
from cxp_cruce import (
    _celda_tiene_formula,
    _copiar_estilo_celda,
    _fila_encabezado_contratos,
    _fila_inicio_datos_contratos,
    _fila_tiene_contratista,
    _indice_columna_en_hoja,
    _normalizar,
    _ultima_columna_con_datos,
    clave_cuatro,
    _fecha_datetime,
    preparar_indice_matriz,
)
from hoja_suspendidos import (
    FILL_ENCABEZADO_AZUL,
    FILL_ENCABEZADO_AMARILLO,
    _autoajustar_columna_suspendidos,
    _copiar_ancho_columna,
    _copiar_estilo_columna,
    _es_columna_saldo_mes,
    _fill_encabezado_alterno,
    _indice_columna_titulos,
    _mes_desde_titulo,
    _titulos_saldo_equivalentes,
    titulo_saldo_suspendidos,
)

# En esta hoja: fila 1 = suma de saldos, fila 2 = conteo (sin saldo $0)
FILA_SUMA_LIQUIDADOS = 1
FILA_CONTEO_LIQUIDADOS = 2


def resolver_hoja_liquidados_con_saldo(nombres_hojas: list[str]) -> str | None:
    for candidato in HOJAS_LIQUIDADOS_CON_SALDO:
        if candidato in nombres_hojas:
            return candidato
    for nombre in nombres_hojas:
        norm = _normalizar(nombre)
        if norm in ("liquidados con saldo", "liquidado con saldo"):
            return nombre
    return None


def preparar_mapa_k4_saldo_matriz(df_matriz, localidad: str) -> dict[str, float]:
    """Saldo por nombre+contrato+año+apropiación (suma si hay varias filas k4 en Matriz)."""
    df_loc, _, _ = preparar_indice_matriz(df_matriz, localidad)
    mapa: dict[str, float] = {}
    for k4, grupo in df_loc.groupby("_k4", sort=False):
        mapa[k4] = float(grupo["_saldo"].sum())
    return mapa


def _listar_columnas_saldo_mes(ws) -> list[tuple[int, int]]:
    """(columna, número de mes) ordenados por mes."""
    fila_hdr = _fila_encabezado_contratos()
    columnas: dict[int, int] = {}
    for col in range(1, ws.max_column + 1):
        val = ws.cell(fila_hdr, col).value
        if val is None or not str(val).strip():
            continue
        titulo = str(val).strip()
        if not _es_columna_saldo_mes(titulo):
            continue
        mes = _mes_desde_titulo(titulo)
        if mes is not None:
            columnas[mes] = col
    return [(columnas[m], m) for m in sorted(columnas)]


def _columna_saldo_mes_anterior(
    ws,
    fecha: datetime | date,
    col_saldo: int,
) -> int | None:
    mes_actual = _fecha_datetime(fecha).month
    cols = _listar_columnas_saldo_mes(ws)
    previas = [c for c in cols if c[1] < mes_actual]
    if previas:
        return previas[-1][0]
    if cols:
        idx = next((i for i, c in enumerate(cols) if c[0] == col_saldo), None)
        if idx is not None and idx > 0:
            return cols[idx - 1][0]
        if cols[-1][0] != col_saldo and len(cols) >= 1:
            return cols[-1][0]
        if len(cols) >= 2:
            return cols[-2][0]
    return None


def _aplicar_encabezados_saldo_alternos(ws) -> None:
    fila_hdr = _fila_encabezado_contratos()
    cols = _listar_columnas_saldo_mes(ws)
    if not cols:
        return
    col_plantilla = _indice_columna_en_hoja(ws, "SALDO FINAL", "Saldo Final")
    for indice, (col, _) in enumerate(cols):
        celda = ws.cell(fila_hdr, col)
        if indice > 0:
            col_prev = cols[indice - 1][0]
            _copiar_estilo_celda(ws.cell(fila_hdr, col_prev), celda)
            fill_titulo = _fill_encabezado_alterno(ws.cell(fila_hdr, col_prev))
        elif col_plantilla:
            _copiar_estilo_celda(ws.cell(fila_hdr, col_plantilla), celda)
            fill_titulo = FILL_ENCABEZADO_AZUL
        else:
            fill_titulo = FILL_ENCABEZADO_AZUL
        celda.fill = fill_titulo


def _asegurar_columna_saldo_mes(
    ws,
    fecha: datetime | date,
) -> tuple[int, int | None]:
    """Devuelve (col_saldo_actual, col_saldo_mes_anterior)."""
    col_saldo = _indice_columna_titulos(ws, _titulos_saldo_equivalentes(fecha))
    col_prev = None
    if col_saldo is not None:
        col_prev = _columna_saldo_mes_anterior(ws, fecha, col_saldo)

    if col_saldo is None:
        siguiente = _ultima_columna_con_datos(ws) + 1
        col_saldo = siguiente
        col_prev = _columna_saldo_mes_anterior(ws, fecha, col_saldo)

    fila_hdr = _fila_encabezado_contratos()
    titulo = titulo_saldo_suspendidos(fecha)
    if _normalizar(str(ws.cell(fila_hdr, col_saldo).value or "")) != _normalizar(titulo):
        ws.cell(fila_hdr, col_saldo, value=titulo)

    if col_prev:
        _copiar_estilo_columna(ws, col_prev, col_saldo)
        for fila in (FILA_SUMA_LIQUIDADOS, FILA_CONTEO_LIQUIDADOS):
            _copiar_estilo_celda(ws.cell(fila, col_prev), ws.cell(fila, col_saldo))
    else:
        col_sf = _indice_columna_en_hoja(ws, "SALDO FINAL", "Saldo Final")
        if col_sf:
            _copiar_estilo_columna(ws, col_sf, col_saldo)
            for fila in (FILA_SUMA_LIQUIDADOS, FILA_CONTEO_LIQUIDADOS):
                _copiar_estilo_celda(ws.cell(fila, col_sf), ws.cell(fila, col_saldo))

    if col_prev:
        _copiar_ancho_columna(ws, col_prev, col_saldo)

    _aplicar_encabezados_saldo_alternos(ws)
    return col_saldo, col_prev


def _saldo_es_cero(valor) -> bool:
    if valor is None or valor == "":
        return True
    try:
        return abs(float(valor)) < 1e-9
    except (TypeError, ValueError):
        return True


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


def _conteo_con_saldo_distinto_cero(ws, col_saldo: int) -> int:
    col_nombre = _indice_columna_en_hoja(ws, "NOMBRE CONTRATISTA")
    fila_ini = _fila_inicio_datos_contratos()
    total = 0
    for fila in range(fila_ini, ws.max_row + 1):
        if col_nombre and not _fila_tiene_contratista(ws, fila, col_nombre):
            continue
        if not _saldo_es_cero(ws.cell(fila, col_saldo).value):
            total += 1
    return total


def _actualizar_resumen_liquidados(
    ws,
    col_saldo: int,
    col_prev_saldo: int | None,
) -> None:
    suma = _suma_saldos_columna(ws, col_saldo)
    conteo = _conteo_con_saldo_distinto_cero(ws, col_saldo)

    celda_suma = ws.cell(FILA_SUMA_LIQUIDADOS, col_saldo)
    celda_conteo = ws.cell(FILA_CONTEO_LIQUIDADOS, col_saldo)

    if col_prev_saldo:
        _copiar_estilo_celda(ws.cell(FILA_SUMA_LIQUIDADOS, col_prev_saldo), celda_suma)
        _copiar_estilo_celda(ws.cell(FILA_CONTEO_LIQUIDADOS, col_prev_saldo), celda_conteo)

    if not _celda_tiene_formula(celda_suma):
        celda_suma.value = suma
    if not _celda_tiene_formula(celda_conteo):
        celda_conteo.value = conteo
        celda_conteo.fill = PatternFill(fill_type=None)


def actualizar_hoja_liquidados_con_saldo(
    ws,
    mapa_k4: dict[str, float],
    fecha: datetime | date,
) -> list[str]:
    """
    Escribe SALDO MES con saldo Matriz por k4 (con apropiación).
    Fila 1: suma de todos los saldos. Fila 2: conteo con saldo ≠ 0.
    """
    advertencias: list[str] = []
    col_saldo, col_prev = _asegurar_columna_saldo_mes(ws, fecha)

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
    col_aprop = _indice_columna_en_hoja(
        ws, "APROPIACION DISPONIBLE", "Apropiación", "Apropiacion"
    )
    if not all([col_nombre, col_cto, col_anio, col_aprop]):
        raise ValueError(
            "Liquidados con saldo: faltan columnas NOMBRE CONTRATISTA, "
            "No. de Cto, AÑO SUSCRIPCIÓN o APROPIACION DISPONIBLE."
        )

    fila_ini = _fila_inicio_datos_contratos()

    for fila in range(fila_ini, ws.max_row + 1):
        if not _fila_tiene_contratista(ws, fila, col_nombre):
            continue

        nombre = ws.cell(fila, col_nombre).value
        contrato = ws.cell(fila, col_cto).value
        anio = ws.cell(fila, col_anio).value
        aprop = ws.cell(fila, col_aprop).value
        k4 = clave_cuatro(nombre, contrato, anio, aprop)
        saldo = mapa_k4.get(k4, 0.0)

        celda_saldo = ws.cell(fila, col_saldo)
        if col_prev:
            _copiar_estilo_celda(ws.cell(fila, col_prev), celda_saldo)
        celda_saldo.value = saldo

    _actualizar_resumen_liquidados(ws, col_saldo, col_prev)
    _autoajustar_columna_suspendidos(ws, col_saldo, titulo_saldo_suspendidos(fecha))

    return advertencias


__all__ = [
    "actualizar_hoja_liquidados_con_saldo",
    "preparar_mapa_k4_saldo_matriz",
    "resolver_hoja_liquidados_con_saldo",
]
