"""Reporte solo de casos no previstos (fallos del sistema), para ajuste técnico."""

from __future__ import annotations

import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd


@dataclass
class CasoNoPrevisto:
    codigo: str
    mensaje: str
    localidad: str = ""
    archivo: str = ""
    fase: str = ""
    detalle: str = ""

    def a_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class ReporteEjecucion:
    """Solo acumula situaciones que el sistema no tenía contempladas."""

    inicio: datetime = field(default_factory=datetime.now)
    fin: datetime | None = None
    casos: list[CasoNoPrevisto] = field(default_factory=list)
    resumen: str = ""

    def no_previsto(
        self,
        codigo: str,
        mensaje: str,
        *,
        localidad: str = "",
        archivo: str = "",
        fase: str = "",
        detalle: str = "",
    ) -> None:
        self.casos.append(
            CasoNoPrevisto(
                codigo=codigo,
                mensaje=mensaje,
                localidad=localidad,
                archivo=archivo,
                fase=fase,
                detalle=detalle,
            )
        )

    def desde_excepcion(
        self,
        exc: BaseException,
        *,
        localidad: str = "",
        archivo: str = "",
        fase: str = "",
    ) -> None:
        """ValueError = dato/archivo del usuario; no se reporta aquí."""
        if isinstance(exc, ValueError):
            return
        self.no_previsto(
            "EXCEPCION",
            str(exc).strip() or type(exc).__name__,
            localidad=localidad,
            archivo=archivo,
            fase=fase,
            detalle=traceback.format_exc(),
        )

    def cerrar(self, exito: bool, localidades_ok: int = 0, total: int = 0) -> None:
        self.fin = datetime.now()
        if not self.casos:
            self.resumen = (
                f"Sin casos no previstos ({localidades_ok}/{total} localidades procesadas)."
                if exito
                else "Sin casos no previstos registrados en esta ejecución."
            )
            return
        self.resumen = (
            f"{len(self.casos)} caso(s) no previsto(s) — requiere revisión técnica."
        )

    def tiene_casos(self) -> bool:
        return len(self.casos) > 0

    def requiere_atencion_admin(self) -> bool:
        return self.tiene_casos()

    def a_dataframe(self) -> pd.DataFrame:
        columnas = ["Código", "Mensaje", "Localidad", "Archivo", "Fase", "Detalle"]
        if not self.casos:
            return pd.DataFrame(columns=columnas)
        return pd.DataFrame(
            [
                {
                    "Código": c.codigo,
                    "Mensaje": c.mensaje,
                    "Localidad": c.localidad,
                    "Archivo": c.archivo,
                    "Fase": c.fase,
                    "Detalle": c.detalle,
                }
                for c in self.casos
            ]
        )

    def generar_texto(self) -> str:
        fin = self.fin or datetime.now()
        duracion = (fin - self.inicio).total_seconds()
        lineas = [
            "CASOS NO PREVISTOS — PLAN DE CHOQUE",
            "=" * 60,
            f"Inicio: {self.inicio.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Fin:    {fin.strftime('%Y-%m-%d %H:%M:%S')} ({duracion:.1f} s)",
            f"Resumen: {self.resumen}",
            "",
        ]
        if not self.casos:
            lineas.append(
                "No hubo fallos del sistema fuera de lo contemplado en esta ejecución."
            )
            return "\n".join(lineas)

        for indice, caso in enumerate(self.casos, start=1):
            lineas.append(f"[{indice}] {caso.codigo}")
            if caso.localidad:
                lineas.append(f"    Localidad: {caso.localidad}")
            if caso.archivo:
                lineas.append(f"    Archivo: {caso.archivo}")
            if caso.fase:
                lineas.append(f"    Fase: {caso.fase}")
            lineas.append(f"    {caso.mensaje}")
            if caso.detalle:
                lineas.append("    --- detalle técnico ---")
                for det_linea in caso.detalle.strip().splitlines():
                    lineas.append(f"    {det_linea}")
            lineas.append("")

        lineas.append(
            "Solo aparecen fallos del sistema. Errores de archivos, contraseña "
            "o contratos sin resolver los ve la operadora en pantalla."
        )
        return "\n".join(lineas)


def _clasificar_observacion_reporte(texto: str) -> tuple[str, str] | None:
    """Devuelve (código, mensaje) si la observación debe ir al reporte de soporte."""
    norm = str(texto).lower()
    if "no se encontr" in norm and ("pestaña" in norm or "pestaña" in norm or "hoja" in norm):
        return "PESTAÑA_NO_ENCONTRADA", str(texto)
    if "no previsto" in norm or "no contemplad" in norm:
        return "EXPORTACION_EXCEL", str(texto)
    return None


def registrar_resultado_localidad(
    reporte: ReporteEjecucion,
    item_cola: dict,
    resultado: dict[str, Any],
) -> None:
    loc = resultado.get("localidad", item_cola.get("localidad", ""))
    nc = resultado.get("nombre_contratos", item_cola.get("contratos", {}).get("name", ""))

    for obs in resultado.get("observaciones") or []:
        clasificado = _clasificar_observacion_reporte(str(obs))
        if clasificado:
            codigo, mensaje = clasificado
            reporte.no_previsto(
                codigo,
                mensaje,
                localidad=loc,
                archivo=nc,
                fase="exportacion_excel",
            )

    from cxp_cruce import METODOS_LABEL

    conteo = resultado.get("conteo") or {}
    for codigo, cantidad in conteo.items():
        if cantidad and codigo not in METODOS_LABEL:
            reporte.no_previsto(
                "METODO_CRUCE_DESCONOCIDO",
                f"Método de cruce no catalogado: «{codigo}» ({cantidad} contrato(s)).",
                localidad=loc,
                fase="cruce_matriz",
            )
