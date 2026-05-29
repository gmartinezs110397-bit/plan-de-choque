"""Reporte técnico de incidencias durante carga y consolidación (para revisión y ajustes)."""

from __future__ import annotations

import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd

NIVEL_ERROR = "ERROR"
NIVEL_ADVERTENCIA = "ADVERTENCIA"
NIVEL_REVISAR = "REVISAR"
NIVEL_INFO = "INFO"


@dataclass
class Incidencia:
    nivel: str
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
    """Acumula lo ocurrido en validación y ejecución."""

    inicio: datetime = field(default_factory=datetime.now)
    fin: datetime | None = None
    incidencias: list[Incidencia] = field(default_factory=list)
    resumen_usuario: str = ""

    def registrar(
        self,
        nivel: str,
        codigo: str,
        mensaje: str,
        *,
        localidad: str = "",
        archivo: str = "",
        fase: str = "",
        detalle: str = "",
    ) -> None:
        self.incidencias.append(
            Incidencia(
                nivel=nivel,
                codigo=codigo,
                mensaje=mensaje,
                localidad=localidad,
                archivo=archivo,
                fase=fase,
                detalle=detalle,
            )
        )

    def error(self, codigo: str, mensaje: str, **kwargs) -> None:
        self.registrar(NIVEL_ERROR, codigo, mensaje, **kwargs)

    def advertencia(self, codigo: str, mensaje: str, **kwargs) -> None:
        self.registrar(NIVEL_ADVERTENCIA, codigo, mensaje, **kwargs)

    def revisar(self, codigo: str, mensaje: str, **kwargs) -> None:
        """Situación no prevista o que requiere ajuste en el sistema."""
        self.registrar(NIVEL_REVISAR, codigo, mensaje, **kwargs)

    def info(self, codigo: str, mensaje: str, **kwargs) -> None:
        self.registrar(NIVEL_INFO, codigo, mensaje, **kwargs)

    def desde_excepcion(
        self,
        exc: BaseException,
        *,
        localidad: str = "",
        archivo: str = "",
        fase: str = "",
    ) -> None:
        if isinstance(exc, ValueError):
            self.error(
                "VALIDACION",
                str(exc).strip(),
                localidad=localidad,
                archivo=archivo,
                fase=fase,
            )
            return
        self.revisar(
            "NO_PREVISTO",
            str(exc).strip() or type(exc).__name__,
            localidad=localidad,
            archivo=archivo,
            fase=fase,
            detalle=traceback.format_exc(),
        )

    def registrar_textos_error(
        self,
        errores: list[str],
        *,
        fase: str,
        nivel: str = NIVEL_ERROR,
    ) -> None:
        for texto in errores:
            limpio = str(texto).replace("**", "").strip()
            self.registrar(
                nivel,
                f"FALLA_{fase.upper()}",
                limpio,
                fase=fase,
            )

    def cerrar(self, exito: bool, localidades_ok: int = 0, total: int = 0) -> None:
        self.fin = datetime.now()
        if exito and not self.requiere_atencion_admin():
            self.resumen_usuario = (
                f"Ejecución correcta ({localidades_ok}/{total} localidades). "
                "Sin incidencias que requieran ajuste técnico."
            )
        elif exito:
            self.resumen_usuario = (
                f"Ejecución completada ({localidades_ok}/{total} localidades) "
                "con incidencias para revisión técnica."
            )
        else:
            self.resumen_usuario = (
                "La consolidación no finalizó correctamente. "
                "Revise el reporte técnico."
            )

    def requiere_atencion_admin(self) -> bool:
        return any(
            i.nivel in (NIVEL_ERROR, NIVEL_REVISAR) for i in self.incidencias
        ) or any(i.nivel == NIVEL_ADVERTENCIA for i in self.incidencias)

    def cantidad_por_nivel(self) -> dict[str, int]:
        conteo: dict[str, int] = {}
        for inc in self.incidencias:
            conteo[inc.nivel] = conteo.get(inc.nivel, 0) + 1
        return conteo

    def a_dataframe(self) -> pd.DataFrame:
        if not self.incidencias:
            return pd.DataFrame(
                columns=[
                    "Nivel",
                    "Código",
                    "Mensaje",
                    "Localidad",
                    "Archivo",
                    "Fase",
                    "Detalle",
                ]
            )
        filas = []
        for inc in self.incidencias:
            filas.append(
                {
                    "Nivel": inc.nivel,
                    "Código": inc.codigo,
                    "Mensaje": inc.mensaje,
                    "Localidad": inc.localidad,
                    "Archivo": inc.archivo,
                    "Fase": inc.fase,
                    "Detalle": inc.detalle,
                }
            )
        return pd.DataFrame(filas)

    def generar_texto(self) -> str:
        fin = self.fin or datetime.now()
        duracion = (fin - self.inicio).total_seconds()
        lineas = [
            "REPORTE TÉCNICO — PLAN DE CHOQUE",
            "=" * 60,
            f"Inicio: {self.inicio.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Fin:    {fin.strftime('%Y-%m-%d %H:%M:%S')} ({duracion:.1f} s)",
            f"Resumen: {self.resumen_usuario}",
            "",
        ]
        por_nivel = self.cantidad_por_nivel()
        if por_nivel:
            lineas.append("Totales por nivel:")
            for nivel in (NIVEL_ERROR, NIVEL_REVISAR, NIVEL_ADVERTENCIA, NIVEL_INFO):
                if nivel in por_nivel:
                    lineas.append(f"  - {nivel}: {por_nivel[nivel]}")
            lineas.append("")

        if not self.incidencias:
            lineas.append("Sin incidencias registradas.")
            return "\n".join(lineas)

        for indice, inc in enumerate(self.incidencias, start=1):
            lineas.append(f"[{indice}] {inc.nivel} | {inc.codigo}")
            if inc.localidad:
                lineas.append(f"    Localidad: {inc.localidad}")
            if inc.archivo:
                lineas.append(f"    Archivo: {inc.archivo}")
            if inc.fase:
                lineas.append(f"    Fase: {inc.fase}")
            lineas.append(f"    {inc.mensaje}")
            if inc.detalle:
                lineas.append("    --- detalle ---")
                for det_linea in inc.detalle.strip().splitlines():
                    lineas.append(f"    {det_linea}")
            lineas.append("")

        lineas.append(
            "Leyenda: ERROR = bloqueo o fallo; REVISAR = caso no previsto; "
            "ADVERTENCIA = regla de negocio; INFO = informativo."
        )
        return "\n".join(lineas)

    def to_serializable(self) -> dict[str, Any]:
        return {
            "inicio": self.inicio.isoformat(),
            "fin": self.fin.isoformat() if self.fin else None,
            "resumen_usuario": self.resumen_usuario,
            "incidencias": [i.a_dict() for i in self.incidencias],
        }


def registrar_observaciones_exportacion(
    reporte: ReporteEjecucion,
    localidad: str,
    nombre_contratos: str,
    observaciones: list[str],
    advertencias_hojas: list[str],
) -> None:
    for obs in observaciones:
        codigo = "OBS_EXPORTACION"
        nivel = NIVEL_INFO
        texto = str(obs)
        if "no previsto" in texto.lower() or "error" in texto.lower():
            nivel = NIVEL_REVISAR
            codigo = "EXPORTACION_NO_PREVISTA"
        elif "no se encontr" in texto.lower():
            codigo = "HOJA_NO_ENCONTRADA"
        reporte.registrar(
            nivel,
            codigo,
            texto,
            localidad=localidad,
            archivo=nombre_contratos,
            fase="exportacion_excel",
        )

    for aviso in advertencias_hojas:
        reporte.advertencia(
            "HOJA_SEGUIMIENTO",
            str(aviso),
            localidad=localidad,
            archivo=nombre_contratos,
            fase="suspendidos_proximos",
        )


def registrar_resultado_localidad(
    reporte: ReporteEjecucion,
    item_cola: dict,
    resultado: dict[str, Any],
) -> None:
    loc = resultado.get("localidad", item_cola.get("localidad", ""))
    nc = resultado.get("nombre_contratos", item_cola.get("contratos", {}).get("name", ""))
    nm = resultado.get("nombre_matriz", item_cola.get("matriz", {}).get("name", ""))

    registrar_observaciones_exportacion(
        reporte,
        loc,
        nc,
        resultado.get("observaciones") or [],
        resultado.get("advertencias_hojas")
        or resultado.get("advertencias_suspendidos")
        or [],
    )

    sin_resolver = int(resultado.get("sin_resolver") or 0)
    if sin_resolver > 0:
        reporte.revisar(
            "CONTRATOS_SIN_RESOLVER",
            f"{sin_resolver} contrato(s) sin saldo asignado (verificar / sin matriz).",
            localidad=loc,
            archivo=nc,
            fase="cruce_matriz",
        )

    conteo = resultado.get("conteo") or {}
    for codigo in ("verificar", "sin_matriz"):
        cantidad = int(conteo.get(codigo) or 0)
        if cantidad > 0:
            reporte.revisar(
                f"CRUCE_{codigo.upper()}",
                f"{cantidad} contrato(s) con método «{codigo}».",
                localidad=loc,
                archivo=f"Contratos: {nc} | Matriz: {nm}",
                fase="cruce_matriz",
            )

    from cxp_cruce import METODOS_LABEL

    for codigo, cantidad in conteo.items():
        if cantidad and codigo not in METODOS_LABEL:
            reporte.revisar(
                "METODO_CRUCE_DESCONOCIDO",
                f"Método de cruce no catalogado: «{codigo}» ({cantidad} contrato(s)).",
                localidad=loc,
                fase="cruce_matriz",
            )
