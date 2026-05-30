"""Pestaña Estrategias: resumen de conteos y montos de las hojas de seguimiento."""

from __future__ import annotations

import calendar
import re
from datetime import date, datetime

from constantes import HOJAS_ESTRATEGIAS
from cxp_cruce import (
    FILA_CONTEO_CONTRATOS,
    FILA_SUMA_CONTRATOS,
    MESES_ES,
    _celda_tiene_formula,
    _fecha_datetime,
    _normalizar,
)
from hoja_liquidados_con_saldo import (
    FILA_CONTEO_LIQUIDADOS,
    FILA_SUMA_LIQUIDADOS,
    resolver_hoja_liquidados_con_saldo,
)
from hoja_proximos_a_perder import resolver_hoja_proximos_a_perder
from hoja_suspendidos import (
    _indice_columna_titulos,
    _titulos_estado_equivalentes,
    _titulos_saldo_equivalentes,
    resolver_hoja_suspendidos,
)
from hoja_tramites_sectores import resolver_hoja_tramites_sectores

COL_NOMBRE_PESTANA = 2  # B
COL_CONTRATOS = 5  # E
COL_MONTO = 6  # F
FILA_TITULOS = 3
FILA_INICIO_DATOS = 4


def resolver_hoja_estrategias(nombres_hojas: list[str]) -> str | None:
    for candidato in HOJAS_ESTRATEGIAS:
        if candidato in nombres_hojas:
            return candidato
    for nombre in nombres_hojas:
        if _normalizar(nombre) == "estrategias":
            return nombre
    return None


def titulo_contratos_estrategias(fecha: datetime | date) -> str:
    f = _fecha_datetime(fecha)
    dia = calendar.monthrange(f.year, f.month)[1]
    mes = MESES_ES[f.month - 1]
    return f"No. de contratos {dia} de {mes}"


def titulo_monto_total_estrategias(fecha: datetime | date) -> str:
    f = _fecha_datetime(fecha)
    dia = calendar.monthrange(f.year, f.month)[1]
    mes = MESES_ES[f.month - 1]
    return f"Monto Total {dia} de {mes}"


def _valor_numerico(valor) -> float | int | None:
    if valor is None or valor == "":
        return None
    try:
        n = float(valor)
        if abs(n - round(n)) < 1e-9:
            return int(round(n))
        return n
    except (TypeError, ValueError):
        return None


def _escribir_valor(celda, valor) -> None:
    if _celda_tiene_formula(celda):
        return
    celda.value = valor


def _leer_totales_hoja_par(ws, fecha: datetime | date) -> tuple[float | int | None, float | int | None]:
    """Conteo fila 1 col estado; suma fila 2 col saldo (Suspendidos, Próximos, Trámites)."""
    col_saldo = _indice_columna_titulos(ws, _titulos_saldo_equivalentes(fecha))
    col_estado = _indice_columna_titulos(ws, _titulos_estado_equivalentes(fecha))
    if not col_saldo or not col_estado:
        return None, None
    conteo = _valor_numerico(ws.cell(FILA_CONTEO_CONTRATOS, col_estado).value)
    suma = _valor_numerico(ws.cell(FILA_SUMA_CONTRATOS, col_saldo).value)
    return conteo, suma


def _leer_totales_hoja_liquidados(
    ws,
    fecha: datetime | date,
) -> tuple[float | int | None, float | int | None]:
    """Fila 1 suma; fila 2 conteo (solo columna saldo del mes)."""
    col_saldo = _indice_columna_titulos(ws, _titulos_saldo_equivalentes(fecha))
    if not col_saldo:
        return None, None
    suma = _valor_numerico(ws.cell(FILA_SUMA_LIQUIDADOS, col_saldo).value)
    conteo = _valor_numerico(ws.cell(FILA_CONTEO_LIQUIDADOS, col_saldo).value)
    return conteo, suma


def _construir_totales_desde_libro(
    wb,
    nombres_hojas: list[str],
    fecha: datetime | date,
) -> dict[str, tuple[float | int | None, float | int | None]]:
    """Clave lógica -> (conteo contratos, monto total)."""
    totales: dict[str, tuple[float | int | None, float | int | None]] = {}

    nombre = resolver_hoja_suspendidos(nombres_hojas)
    if nombre:
        totales["suspendidos"] = _leer_totales_hoja_par(wb[nombre], fecha)

    nombre = resolver_hoja_proximos_a_perder(nombres_hojas)
    if nombre:
        totales["proximos"] = _leer_totales_hoja_par(wb[nombre], fecha)

    nombre = resolver_hoja_tramites_sectores(nombres_hojas)
    if nombre:
        totales["tramites"] = _leer_totales_hoja_par(wb[nombre], fecha)

    nombre = resolver_hoja_liquidados_con_saldo(nombres_hojas)
    if nombre:
        totales["liquidados"] = _leer_totales_hoja_liquidados(wb[nombre], fecha)

    return totales


def _identificar_fuente_por_texto(texto: str) -> str | None:
    norm = _normalizar(texto)
    if not norm:
        return None
    if re.search(r"\btotal\b", norm) and "suspend" not in norm:
        return "_total"
    if "suspend" in norm:
        return "suspendidos"
    if "proxim" in norm and "perd" in norm:
        return "proximos"
    if "tramit" in norm and "sector" in norm:
        return "tramites"
    if "liquid" in norm and "saldo" in norm:
        return "liquidados"
    return None


def actualizar_hoja_estrategias(
    ws,
    fecha: datetime | date,
    totales_fuentes: dict[str, tuple[float | int | None, float | int | None]],
) -> list[str]:
    """
    Actualiza títulos en E3/F3 y valores en E/F según nombre en columna B.
    No agrega columnas; solo reemplaza valores (respeta fórmulas existentes).
    """
    advertencias: list[str] = []

    _escribir_valor(ws.cell(FILA_TITULOS, COL_CONTRATOS), titulo_contratos_estrategias(fecha))
    _escribir_valor(ws.cell(FILA_TITULOS, COL_MONTO), titulo_monto_total_estrategias(fecha))

    filas_datos: list[int] = []
    fila_total: int | None = None
    suma_conteos = 0.0
    suma_montos = 0.0
    hubo_conteo = False
    hubo_monto = False

    for fila in range(FILA_INICIO_DATOS, ws.max_row + 1):
        raw_b = ws.cell(fila, COL_NOMBRE_PESTANA).value
        if raw_b is None or not str(raw_b).strip():
            continue

        fuente = _identificar_fuente_por_texto(str(raw_b))
        if fuente == "_total":
            fila_total = fila
            continue

        if fuente is None or fuente not in totales_fuentes:
            continue

        conteo, monto = totales_fuentes[fuente]
        if conteo is None and monto is None:
            advertencias.append(
                f"Estrategias: no se leyeron totales para «{raw_b}» "
                f"(falta columna del mes en la pestaña origen)."
            )
            continue

        if conteo is not None:
            _escribir_valor(ws.cell(fila, COL_CONTRATOS), conteo)
            suma_conteos += float(conteo)
            hubo_conteo = True
        if monto is not None:
            _escribir_valor(ws.cell(fila, COL_MONTO), monto)
            suma_montos += float(monto)
            hubo_monto = True

        filas_datos.append(fila)

    if fila_total is None and filas_datos:
        fila_total = max(filas_datos) + 1

    if fila_total is not None:
        if hubo_conteo:
            valor_c = int(suma_conteos) if abs(suma_conteos - round(suma_conteos)) < 1e-9 else suma_conteos
            _escribir_valor(ws.cell(fila_total, COL_CONTRATOS), valor_c)
        if hubo_monto:
            _escribir_valor(ws.cell(fila_total, COL_MONTO), suma_montos)

    if not filas_datos:
        advertencias.append(
            "Estrategias: no se identificó ninguna fila en columna B "
            "(Suspendidos, Próximos a perder, Trámites sectores, Liquidados con saldo)."
        )

    return advertencias


def actualizar_estrategias_en_libro(
    wb,
    fecha: datetime | date,
) -> list[str]:
    nombres = list(wb.sheetnames)
    nombre_est = resolver_hoja_estrategias(nombres)
    if not nombre_est:
        return []
    totales = _construir_totales_desde_libro(wb, nombres, fecha)
    return actualizar_hoja_estrategias(wb[nombre_est], fecha, totales)


__all__ = [
    "actualizar_estrategias_en_libro",
    "actualizar_hoja_estrategias",
    "resolver_hoja_estrategias",
    "titulo_contratos_estrategias",
    "titulo_monto_total_estrategias",
]
