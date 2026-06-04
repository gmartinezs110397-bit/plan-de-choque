"""Ajusta encabezados SALDO (azul/amarillo) en Cps por depurar de un .xlsx de Contratos."""
from __future__ import annotations

import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook

import cxp_cruce as cxp

DEFAULT_ENTRADA = Path(
    r"c:\Users\f1rac\Downloads\Copia de 08. Contratos plan de choque Kennedy 2026 - Junio.xlsx"
)
DEFAULT_SALIDA = DEFAULT_ENTRADA.with_name(
    DEFAULT_ENTRADA.stem + " (encabezados Cps).xlsx"
)


def ajustar_contratos_cps(entrada: Path, salida: Path) -> None:
    with entrada.open("rb") as f:
        raw = f.read()

    wb = load_workbook(BytesIO(raw))
    nombre = cxp.resolver_hoja_cruce_cxp(wb.sheetnames)
    ws = wb[nombre]
    cxp._liberar_tablas_excel_cps(ws)
    cxp._aplicar_encabezados_saldo_mes_alternos(ws, datetime.now())
    out = BytesIO()
    wb.save(out)
    out.seek(0)
    salida.write_bytes(cxp._finalizar_xlsx_contratos(out.getvalue()))
    print(f"Guardado: {salida}")

    wb2 = load_workbook(salida)
    ws2 = wb2[cxp.resolver_hoja_cruce_cxp(wb2.sheetnames)]
    fila_hdr = cxp._fila_encabezado_hoja_datos(ws2)
    print(f"Verificación fila {fila_hdr} (SALDO por mes):")
    for col, mes in cxp._listar_columnas_saldo_mes(ws2):
        celda = ws2.cell(fila_hdr, col)
        rgb = getattr(getattr(celda.fill, "fgColor", None), "rgb", None)
        print(f"  {celda.coordinate} mes={mes} rgb={rgb}")


if __name__ == "__main__":
    entrada = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ENTRADA
    salida = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_SALIDA
    ajustar_contratos_cps(entrada, salida)
