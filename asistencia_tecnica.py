from __future__ import annotations

import calendar
import copy
import math
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable


LOCALIDADES_RADICADO = [
    "Usaquén",
    "Chapinero",
    "Santa Fe",
    "San Cristóbal",
    "Usme",
    "Tunjuelito",
    "Bosa",
    "Kennedy",
    "Fontibón",
    "Engativá",
    "Suba",
    "Barrios Unidos",
    "Teusaquillo",
    "Los Mártires",
    "Antonio Nariño",
    "Puente Aranda",
    "La Candelaria",
    "Rafael Uribe Uribe",
    "Ciudad Bolívar",
    "Sumapaz",
]

MESES_ES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)

ESTADOS_ASISTENCIA = (
    "EN PROCESO DE ANÁLISIS",
    "EN PROCESO DE APROBACIÓN",
    "ORFEADO",
    "EN BANDEJA DEL FDL",
)


def _es_vacio(valor) -> bool:
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    texto = str(valor).strip().lower()
    return texto in {"", "nan", "nat", "none"}


def _texto(valor) -> str:
    return "" if _es_vacio(valor) else str(valor)


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", _texto(texto).strip().lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", texto)


def _limpiar_texto(texto: str) -> str:
    if _es_vacio(texto):
        return ""
    texto = str(texto).replace("\xa0", " ")
    texto = re.sub(r"(?<=\w)-\s+(?=\w)", "-", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip(" \n\r\t:")


def _mes_numero(nombre: str) -> int | None:
    norm = _normalizar(nombre)
    for idx, mes in enumerate(MESES_ES, 1):
        if _normalizar(mes) == norm:
            return idx
    return None


def parsear_fecha(texto: str | date | datetime | None) -> date | None:
    if isinstance(texto, datetime):
        return texto.date()
    if isinstance(texto, date):
        return texto
    valor = _limpiar_texto(str(texto or ""))
    if not valor or valor.upper() in {"N/A", "NA"}:
        return None

    match = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", valor)
    if match:
        dia, mes, anio = [int(x) for x in match.groups()]
        if anio < 100:
            anio += 2000
        try:
            return date(anio, mes, dia)
        except ValueError:
            return None

    match = re.search(
        r"\b(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})\b",
        valor,
        flags=re.IGNORECASE,
    )
    if match:
        dia = int(match.group(1))
        mes = _mes_numero(match.group(2))
        anio = int(match.group(3))
        if mes:
            try:
                return date(anio, mes, dia)
            except ValueError:
                return None
    return None


def formato_fecha_larga(fecha: date | datetime | None) -> str:
    parsed = parsear_fecha(fecha)
    if not parsed:
        return ""
    return f"{parsed.day} de {MESES_ES[parsed.month - 1]} de {parsed.year}"


def formato_fecha_corta(fecha: date | datetime | None) -> str:
    parsed = parsear_fecha(fecha)
    if not parsed:
        return ""
    return parsed.strftime("%d/%m/%Y")


def formato_moneda(valor) -> str:
    numero = _a_numero(valor)
    if numero is None:
        return ""
    return "$" + f"{int(round(numero)):,.0f}".replace(",", ".")


def _a_numero(valor) -> int | None:
    if _es_vacio(valor):
        return None
    if isinstance(valor, (int, float)):
        if isinstance(valor, float) and math.isnan(valor):
            return None
        return int(round(float(valor)))
    texto = str(valor)
    if not texto.strip():
        return None
    texto = texto.replace("$", "").replace(".", "").replace(",", "")
    texto = re.sub(r"[^\d-]", "", texto)
    if not texto:
        return None
    try:
        return int(texto)
    except ValueError:
        return None


def _extraer_entre(texto: str, etiqueta: str, siguientes: Iterable[str]) -> str:
    cierre = "|".join(re.escape(s) for s in siguientes)
    patron = rf"{re.escape(etiqueta)}\s*:?\s*(.*?)(?=\s+(?:{cierre})(?:[^:]{{0,80}})?:|\s+[IVX]+\.\s|$)"
    match = re.search(patron, texto, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return _limpiar_texto(match.group(1))


def _extraer_fecha_entre(texto: str, etiqueta: str, siguientes: Iterable[str]) -> str:
    return formato_fecha_corta(parsear_fecha(_extraer_entre(texto, etiqueta, siguientes)))


def _duracion_desde_texto(texto: str) -> tuple[int, int]:
    texto_norm = _normalizar(texto)
    meses = 0
    dias = 0
    match = re.search(r"\((\d+)\)\s*mes", texto_norm)
    if match:
        meses = int(match.group(1))
    else:
        match = re.search(r"(\d+)\s*mes", texto_norm)
        if match:
            meses = int(match.group(1))
    match = re.search(r"(\d+)\s*d[ií]a", texto_norm)
    if match:
        dias = int(match.group(1))
    return meses, dias


def _formato_duracion(meses: int, dias: int) -> str:
    partes: list[str] = []
    if meses:
        partes.append(f"{meses} mes" + ("es" if meses != 1 else ""))
    if dias:
        partes.append(f"{dias} día" + ("s" if dias != 1 else ""))
    return " y ".join(partes) if partes else ""


def _sumar_meses(fecha: date, meses: int) -> date:
    mes_base = fecha.month - 1 + meses
    anio = fecha.year + mes_base // 12
    mes = mes_base % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def calcular_fecha_fin_inicial(fecha_inicio: date | None, plazo_texto: str) -> date | None:
    if not fecha_inicio:
        return None
    meses, dias = _duracion_desde_texto(plazo_texto)
    if meses == 0 and dias == 0:
        return None
    fin = _sumar_meses(fecha_inicio, meses)
    return date.fromordinal(fin.toordinal() - 1 + dias)


def calcular_fecha_fin_prorroga(fecha_fin_inicial: date | None, prorroga_texto: str) -> date | None:
    if not fecha_fin_inicial:
        return None
    meses, dias = _duracion_desde_texto(prorroga_texto)
    if meses == 0 and dias == 0:
        return None
    fin = _sumar_meses(fecha_fin_inicial, meses)
    return date.fromordinal(fin.toordinal() + dias)


def _canon_localidad(texto: str) -> str:
    norm = _normalizar(texto)
    norm = re.sub(r"^(la|los|las|el)\s+", "", norm)
    alias = {
        "usaquen": "Usaquén",
        "chapinero": "Chapinero",
        "santa fe": "Santa Fe",
        "san cristobal": "San Cristóbal",
        "usme": "Usme",
        "tunjuelito": "Tunjuelito",
        "bosa": "Bosa",
        "kennedy": "Kennedy",
        "fontibon": "Fontibón",
        "engativa": "Engativá",
        "suba": "Suba",
        "barrios unidos": "Barrios Unidos",
        "teusaquillo": "Teusaquillo",
        "martires": "Los Mártires",
        "antonio narino": "Antonio Nariño",
        "puente aranda": "Puente Aranda",
        "candelaria": "La Candelaria",
        "rafael uribe": "Rafael Uribe Uribe",
        "rafael uribe uribe": "Rafael Uribe Uribe",
        "ciudad bolivar": "Ciudad Bolívar",
        "sumapaz": "Sumapaz",
    }
    return alias.get(norm, texto.strip())


def _extraer_localidad(texto: str) -> str:
    match = re.search(
        r"Alcald[ií]a\s+Local\s+de\s+(?:la\s+|los\s+|las\s+|el\s+)?([A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]+)",
        texto,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    candidato = _limpiar_texto(match.group(1).split("Edificio")[0])
    candidato = candidato.split("Código")[0].strip()
    return _canon_localidad(candidato)


def _numero_contrato_corto(numero: str) -> str:
    texto = _limpiar_texto(numero).upper()
    match = re.search(r"(?:CPS|CPS-P|CD|SAMC|FDL[A-Z-]*)[-\s]*(\d{1,4})[-/](20\d{2})", texto)
    if match:
        return f"{match.group(1).zfill(3)}-{match.group(2)}"
    match = re.search(r"(\d{1,4})[-/](20\d{2})", texto)
    if match:
        return f"{match.group(1).zfill(3)}-{match.group(2)}"
    return texto


def _extraer_sipse(nombre_archivo: str, texto: str) -> str:
    candidatos = re.findall(r"\b1\d{5}\b", nombre_archivo)
    if candidatos:
        return candidatos[0]
    candidatos = re.findall(r"SIPSE\s*:?\s*(1\d{5})", texto, flags=re.IGNORECASE)
    return candidatos[0] if candidatos else ""


def extraer_texto_pdf(nombre_archivo: str, contenido: bytes) -> tuple[str, list[str]]:
    errores: list[str] = []
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(contenido))
        paginas = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(paginas), errores
    except Exception as exc:  # pragma: no cover - depende del PDF recibido.
        errores.append(f"{nombre_archivo}: no se pudo leer el PDF ({exc}).")
        return "", errores


def analizar_solicitud_pdf(nombre_archivo: str, contenido: bytes) -> tuple[dict, list[str]]:
    texto_pdf, errores = extraer_texto_pdf(nombre_archivo, contenido)
    texto = re.sub(r"\s+", " ", texto_pdf.replace("\xa0", " "))
    fila: dict = {
        "archivo": nombre_archivo,
        "sipse": _extraer_sipse(nombre_archivo, texto),
        "localidad": _extraer_localidad(texto),
        "fecha_solicitud": _extraer_fecha_entre(texto, "Fecha de Solicitud", ["Área de Origen", "Area de Origen"]),
        "area_origen": _extraer_entre(texto, "Área de Origen", ["I. RESUMEN CONTRACTUAL", "Número Contrato"]),
        "contrato": _extraer_entre(texto, "Número Contrato", ["Fecha de Suscripción"]),
        "fecha_suscripcion": _extraer_fecha_entre(texto, "Fecha de Suscripción", ["Tipo de Contrato"]),
        "tipo_contrato": _extraer_entre(texto, "Tipo de Contrato", ["Plazo Inicial"]),
        "plazo_inicial": _extraer_entre(texto, "Plazo Inicial", ["Fecha de Inicio"]),
        "fecha_inicio": _extraer_fecha_entre(texto, "Fecha de Inicio", ["Fecha de Terminación Inicial"]),
        "fecha_terminacion_inicial": _extraer_fecha_entre(texto, "Fecha de Terminación Inicial", ["Objeto"]),
        "objeto": _extraer_entre(texto, "Objeto", ["Contratista"]),
        "contratista": _extraer_entre(texto, "Contratista", ["Supervisor"]),
        "supervisor": _extraer_entre(texto, "Supervisor", ["Valor Inicial"]),
        "valor_inicial": _a_numero(_extraer_entre(texto, "Valor Inicial", ["Número del proceso", "Numero del proceso"])),
        "proceso_secop": _extraer_entre(texto, "Número del proceso SECOP I o II", ["Fecha de publicación"]),
        "fecha_publicacion_secop": _extraer_fecha_entre(texto, "Fecha de publicación del proceso en SECOP I o II", ["Link del proceso"]),
        "link_secop": "",
        "valor_adicion": None,
        "prorroga_solicitada": "",
        "fecha_terminacion_final": "",
        "estado": ESTADOS_ASISTENCIA[0],
        "observaciones": "NINGUNA",
    }

    url = re.search(r"https?://\S+", texto_pdf)
    if url:
        fila["link_secop"] = url.group(0).strip()

    valor_adicion = re.search(r"Valor\s+a\s+Adicionar\s*:\s*\$?\s*([\d\.\,]+)", texto, flags=re.IGNORECASE)
    if not valor_adicion:
        valor_adicion = re.search(r"Adici[oó]n\s+Valor\s+Pr[oó]rroga\s+Tiempo.*?\$\s*([\d\.\,]+)", texto, flags=re.IGNORECASE | re.DOTALL)
    if valor_adicion:
        fila["valor_adicion"] = _a_numero(valor_adicion.group(1))

    match_prorroga = re.search(
        r"Tiempo\s*:\s*(.*?)(?:Adici[oó]n\s+y\s+Pr[oó]rroga|Fecha\s+Terminaci[oó]n\s+Final|III\.)",
        texto,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match_prorroga:
        fila["prorroga_solicitada"] = _limpiar_texto(match_prorroga.group(1))

    fechas_finales = re.findall(
        r"Fecha\s+Terminaci[oó]n\s+Final\s*:\s*(.*?)(?=\s+(?:III\.|ESTADO FINANCIERO|Valor:|CDP|Tiempo:|N/A)|$)",
        texto,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for candidato in fechas_finales:
        fecha = parsear_fecha(candidato)
        if fecha:
            fila["fecha_terminacion_final"] = formato_fecha_corta(fecha)
            break

    fecha_inicio = parsear_fecha(fila["fecha_inicio"])
    if not fila["fecha_terminacion_inicial"]:
        fila["fecha_terminacion_inicial"] = formato_fecha_corta(
            calcular_fecha_fin_inicial(fecha_inicio, fila["plazo_inicial"])
        )
    if not fila["fecha_terminacion_final"]:
        fila["fecha_terminacion_final"] = formato_fecha_corta(
            calcular_fecha_fin_prorroga(
                parsear_fecha(fila["fecha_terminacion_inicial"]),
                fila["prorroga_solicitada"],
            )
        )

    for campo in ("contrato", "objeto", "contratista", "supervisor", "plazo_inicial", "prorroga_solicitada"):
        fila[campo] = _limpiar_texto(fila.get(campo, ""))
    fila["contrato"] = fila["contrato"].replace(" ", "")
    fila["objeto"] = fila["objeto"].strip(' "“”')

    requeridos = ("localidad", "contrato", "contratista", "fecha_inicio", "plazo_inicial")
    faltantes = [campo for campo in requeridos if not fila.get(campo)]
    if faltantes:
        errores.append(f"{nombre_archivo}: revise {', '.join(faltantes)}.")
    return fila, errores


def analizar_solicitudes(archivos: Iterable[tuple[str, bytes]]) -> tuple[list[dict], list[str]]:
    filas: list[dict] = []
    errores: list[str] = []
    for nombre, contenido in archivos:
        fila, err = analizar_solicitud_pdf(nombre, contenido)
        filas.append(fila)
        errores.extend(err)
    return filas, errores


def extraer_radicados(contenido_pdf: bytes) -> tuple[dict[str, str], date | None, list[str]]:
    texto, errores = extraer_texto_pdf("Listado de radicado", contenido_pdf)
    numeros = re.findall(r"\b20\d{12}\b", texto)
    mapa = {
        localidad: numeros[idx]
        for idx, localidad in enumerate(LOCALIDADES_RADICADO)
        if idx < len(numeros)
    }

    fecha = None
    match = re.search(r"Fecha\s*:\s*(\d{1,2})-(\d{1,2})-(\d{1,4})", texto, flags=re.IGNORECASE)
    if match:
        dia = int(match.group(1))
        mes = int(match.group(2))
        anio_txt = match.group(3)
        anio = int(anio_txt) if len(anio_txt) == 4 else None
        if not anio and numeros:
            anio = int(numeros[0][:4])
        if anio:
            try:
                fecha = date(anio, mes, dia)
            except ValueError:
                fecha = None
    if not mapa:
        errores.append("No se encontraron radicados de salida en el archivo general.")
    return mapa, fecha, errores


def enriquecer_con_radicados(filas: list[dict], mapa: dict[str, str], fecha_salida: date | None) -> list[dict]:
    resultado: list[dict] = []
    for fila in filas:
        copia = dict(fila)
        localidad = _canon_localidad(copia.get("localidad", ""))
        copia["localidad"] = localidad
        copia["radicado_salida"] = _texto(copia.get("radicado_salida")) or mapa.get(localidad, "")
        copia["fecha_salida"] = _texto(copia.get("fecha_salida")) or formato_fecha_corta(fecha_salida)
        resultado.append(copia)
    return resultado


def _orden_localidad(localidad: str) -> int:
    canon = _canon_localidad(localidad)
    try:
        return LOCALIDADES_RADICADO.index(canon)
    except ValueError:
        return 99


def ordenar_filas(filas: Iterable[dict]) -> list[dict]:
    return sorted(
        (dict(f) for f in filas),
        key=lambda f: (_orden_localidad(f.get("localidad", "")), _texto(f.get("sipse")), _texto(f.get("contrato"))),
    )


def _nombre_archivo_seguro(texto: str) -> str:
    texto = _normalizar(texto)
    texto = re.sub(r"[^a-z0-9]+", "_", texto).strip("_")
    return texto or "archivo"


def _descripcion_solicitud(fila: dict) -> str:
    tiene_adicion = (_a_numero(fila.get("valor_adicion")) or 0) > 0
    tiene_prorroga = bool(_texto(fila.get("prorroga_solicitada")).strip())
    if tiene_adicion and tiene_prorroga:
        return "ADICIÓN Y PRÓRROGA"
    if tiene_adicion:
        return "ADICIÓN"
    if tiene_prorroga:
        return "PRÓRROGA"
    return "MODIFICACIÓN"


def _mes_reporte(fila: dict) -> str:
    fecha = parsear_fecha(fila.get("fecha_solicitud"))
    return MESES_ES[fecha.month - 1].upper() if fecha else ""


def generar_excel_asistencia(filas: Iterable[dict], profesional: str = "") -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    wb = Workbook()
    ws_aux = wb.active
    ws_aux.title = "Hoja1"
    for idx, estado in enumerate(ESTADOS_ASISTENCIA, 5):
        ws_aux.cell(idx, 3, estado)
    ws_listas = wb.create_sheet("Hoja2")
    for idx, localidad in enumerate(LOCALIDADES_RADICADO, 3):
        ws_listas.cell(idx, 3, _normalizar(localidad).upper())
    ws = wb.create_sheet("CPS 2026")
    wb.active = wb.sheetnames.index("CPS 2026")
    ws.sheet_view.showGridLines = False

    rojo = PatternFill("solid", fgColor="C00000")
    amarillo = PatternFill("solid", fgColor="FFC000")
    borde = Border(
        left=Side(style="thin", color="808080"),
        right=Side(style="thin", color="808080"),
        top=Side(style="thin", color="808080"),
        bottom=Side(style="thin", color="808080"),
    )

    ws.merge_cells("C1:R1")
    ws["C1"] = "MATRIZ DE SEGUIMIENTO ASISTENCIA TÉCNICA DE LOS FDL - ADICIONES Y/O PRÓRROGA"
    ws["C1"].fill = rojo
    ws["C1"].font = Font(bold=True, color="FFFFFF", size=14)
    ws["C1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells("S1:T6")
    ws["S1"] = "Código: GET-AGL-F009\nVersión: 01\nVigencia:  27 de septiembre de 2022\nCaso HOLA: 268037"
    ws["S1"].alignment = Alignment(wrap_text=True, vertical="top")

    encabezados = [
        "CONSECUTIVO No.",
        "LOCALIDAD",
        "NÚMERO DE ORDEN",
        "FECHA DE INGRESO\nDD-MM-AAAA",
        "RADICADO DE ENTRADA FDL - SIPSE",
        "DEVUELTO SI / NO",
        "FECHA DE DEVOLUCIÓN\nDD-MM-AAAA",
        "DESCRIPCIÓN DE LA SOLICITUD ADICIÓN Y/O PRÓRROGA",
        "No. DE CONTRATO (EJ: XXX/2026)",
        "OBJETO ",
        "NOMBRES Y APELLIDOS CONTRATISTA CPS",
        "PLAZO INICIAL (MESES)",
        "VALOR INICIAL DEL CONTRATO ",
        "PLAZO DE LA PRÓRROGA SOLICITADA (MESES) ",
        "VALOR ADICIÓN SOLICITADA",
        "ESTADO / TRÁMITE",
        "RADICADO DE SALIDA",
        "FECHA SALIDA DGDL\nDD-MM-AAAA",
        "OBSERVACIONES",
        "MES A MES",
        "",
        "VENCE",
        "PROFESIONAL RESPONSABLE",
        "FECHA DIRECTORA",
        "DIAS HABILES",
        "DIAS SIN RESPUESTA",
    ]
    for col, titulo in enumerate(encabezados, 1):
        celda = ws.cell(7, col, titulo)
        celda.fill = amarillo
        celda.font = Font(bold=True)
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        celda.border = borde

    filas_ordenadas = ordenar_filas(filas)
    orden_por_localidad: dict[str, int] = {}
    for idx, fila in enumerate(filas_ordenadas, 8):
        localidad = _canon_localidad(fila.get("localidad", ""))
        orden_por_localidad[localidad] = orden_por_localidad.get(localidad, 0) + 1
        valores = [
            idx - 7,
            localidad.upper(),
            orden_por_localidad[localidad],
            parsear_fecha(fila.get("fecha_solicitud")),
            _texto(fila.get("sipse")),
            "NO",
            "N/A",
            _descripcion_solicitud(fila),
            _numero_contrato_corto(_texto(fila.get("contrato"))),
            _texto(fila.get("objeto")).upper(),
            _texto(fila.get("contratista")).upper(),
            _texto(fila.get("plazo_inicial")).upper(),
            _a_numero(fila.get("valor_inicial")),
            _texto(fila.get("prorroga_solicitada")).upper(),
            _a_numero(fila.get("valor_adicion")),
            (_texto(fila.get("estado")) or ESTADOS_ASISTENCIA[0]).upper(),
            _texto(fila.get("radicado_salida")),
            parsear_fecha(fila.get("fecha_salida")),
            (_texto(fila.get("observaciones")) or "NINGUNA").upper(),
            _mes_reporte(fila),
            "",
            "",
            str(profesional or "").upper(),
            "",
            "",
            "",
        ]
        for col, valor in enumerate(valores, 1):
            celda = ws.cell(idx, col, valor)
            celda.border = borde
            celda.alignment = Alignment(vertical="center", wrap_text=col in {10, 11})
            if col in {4, 18} and isinstance(valor, date):
                celda.number_format = "DD/MM/YYYY"
            if col in {13, 15}:
                celda.number_format = '"$"#,##0'

    widths = {
        "A": 12,
        "B": 18,
        "C": 13,
        "D": 15,
        "E": 18,
        "F": 14,
        "G": 15,
        "H": 28,
        "I": 20,
        "J": 55,
        "K": 34,
        "L": 18,
        "M": 18,
        "N": 24,
        "O": 18,
        "P": 24,
        "Q": 20,
        "R": 15,
        "S": 24,
        "T": 14,
        "V": 12,
        "W": 26,
        "X": 15,
        "Y": 14,
        "Z": 18,
    }
    for col, width in widths.items():
        ws.column_dimensions[col].width = width
    ws.row_dimensions[1].height = 32
    ws.row_dimensions[7].height = 48
    ws.freeze_panes = "A8"

    salida = BytesIO()
    wb.save(salida)
    return salida.getvalue()


def _set_paragraph_text(paragraph, texto: str) -> None:
    for run in paragraph.runs:
        run.text = ""
    if paragraph.runs:
        paragraph.runs[0].text = texto
    else:
        paragraph.add_run(texto)


def _copiar_parrafo_xml(sample_p, texto: str):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    p = copy.deepcopy(sample_p)
    primer_rpr = None
    for r in p.findall(qn("w:r")):
        rpr = r.find(qn("w:rPr"))
        if rpr is not None:
            primer_rpr = copy.deepcopy(rpr)
            break
    for child in list(p):
        if child.tag != qn("w:pPr"):
            p.remove(child)
    r = OxmlElement("w:r")
    if primer_rpr is not None:
        r.append(primer_rpr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = texto
    r.append(t)
    p.append(r)
    return p


def _insertar_parrafo(anchor, sample_p, texto: str) -> None:
    anchor.addprevious(_copiar_parrafo_xml(sample_p, texto))


def _insertar_blanco(anchor, sample_p) -> None:
    anchor.addprevious(copy.deepcopy(sample_p))


def _set_cell_text(cell, texto: str) -> None:
    cell.text = str(texto or "")
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.font.highlight_color = None


def _llenar_tabla_solicitud(table, fila: dict) -> None:
    valores = {
        2: _texto(fila.get("contrato")),
        3: _texto(fila.get("contratista")).upper(),
        4: _texto(fila.get("objeto")).upper(),
        5: formato_fecha_corta(parsear_fecha(fila.get("fecha_inicio"))),
        6: _texto(fila.get("plazo_inicial")),
        7: formato_moneda(fila.get("valor_inicial")),
        8: formato_fecha_corta(parsear_fecha(fila.get("fecha_terminacion_inicial"))),
        9: _texto(fila.get("prorroga_solicitada")),
        10: formato_moneda(fila.get("valor_adicion")),
        11: formato_fecha_corta(parsear_fecha(fila.get("fecha_terminacion_final"))),
    }
    for row_idx, valor in valores.items():
        _set_cell_text(table.rows[row_idx].cells[1], valor)
        _set_cell_text(table.rows[row_idx].cells[2], "X")
        _set_cell_text(table.rows[row_idx].cells[3], "")


def _quitar_resaltados(doc) -> None:
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            run.font.highlight_color = None
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.highlight_color = None


def _cargo_localidad(localidad: str, supervisor: str) -> str:
    nombre = _normalizar(supervisor)
    cargo = "Alcaldesa" if any(p in nombre.split() for p in ("maria", "angela", "angelica", "diana", "paola", "catherine", "claudia", "andrea", "luisa")) else "Alcalde(sa)"
    return f"{cargo} Local de {localidad}"


def _texto_observacion_vigencia(fila: dict) -> str:
    fin_inicial = parsear_fecha(fila.get("fecha_terminacion_inicial"))
    fin_final = parsear_fecha(fila.get("fecha_terminacion_final"))
    anio = fin_inicial.year if fin_inicial else (fin_final.year if fin_final else date.today().year)
    if fin_inicial and fin_final and fin_final.year <= fin_inicial.year:
        return (
            f"Prorroga: No supera la vigencia fiscal {anio}, según la fecha de terminación "
            "con prórroga registrada en la solicitud."
        )
    return (
        f"Prorroga: Supera la vigencia fiscal {anio}, si bien la regla general impide la ejecución "
        "contractual más allá de la vigencia fiscal en curso, existe habilitación legal para su prórroga "
        "excepcional, siempre y cuando se sustente en necesidades claramente justificadas, se respeten "
        "los límites establecidos para la contratación estatal y se observen estrictamente los procedimientos "
        "presupuestales correspondientes."
    )


def generar_documento_localidad(
    filas: list[dict],
    plantilla_docx: Path,
    fecha_respuesta: date,
    profesional: str,
) -> bytes:
    from docx import Document
    from docx.oxml.ns import qn
    from docx.table import Table

    filas = ordenar_filas(filas)
    localidad = _canon_localidad(filas[0].get("localidad", ""))
    supervisor = _texto(filas[0].get("supervisor")).upper()
    sipses = [_texto(f.get("sipse")).strip() for f in filas if _texto(f.get("sipse")).strip()]
    sipses_txt = ", ".join(sipses) if sipses else "SIN NÚMERO SIPSE"
    radicado = _texto(filas[0].get("radicado_salida")).strip()
    fecha_salida = parsear_fecha(filas[0].get("fecha_salida"))

    doc = Document(str(plantilla_docx))
    paragraphs = doc.paragraphs
    first_solicitud = next((p for p in paragraphs if p.text.strip().upper().startswith("SOLICITUD")), None)
    recomendaciones = next((p for p in paragraphs if "RECOMENDACIONES GENERALES" in p.text.upper()), None)
    if first_solicitud is None or recomendaciones is None or not doc.tables:
        raise ValueError("La plantilla Word no tiene la estructura esperada.")

    sample_heading = copy.deepcopy(first_solicitud._p)
    sample_blank = copy.deepcopy(doc.paragraphs[paragraphs.index(first_solicitud) + 1]._p)
    sample_normal = copy.deepcopy(next((p._p for p in paragraphs if p.text.strip().lower().startswith("prorroga:")), first_solicitud._p))
    sample_intro = copy.deepcopy(next((p._p for p in paragraphs if p.text.strip().lower().startswith("en cuanto")), first_solicitud._p))
    sample_table = copy.deepcopy(doc.tables[0]._tbl)

    for p in doc.paragraphs:
        texto = p.text.strip()
        if texto.startswith("Bogotá D.C."):
            _set_paragraph_text(p, f"Bogotá D.C., {formato_fecha_larga(fecha_respuesta)}")
        elif texto.startswith("PARA:"):
            _set_paragraph_text(p, f"PARA:\t{supervisor}")
        elif texto.startswith("Alcalde") or texto.startswith("Alcaldesa"):
            _set_paragraph_text(p, _cargo_localidad(localidad, supervisor))
        elif texto.startswith("ASUNTO:"):
            _set_paragraph_text(
                p,
                (
                    "ASUNTO:\tRESPUESTA A SOLICITUDES SIPSE: "
                    f"{sipses_txt}, SOBRE ADICIONES Y PRÓRROGAS A CONTRATOS DE PRESTACIÓN "
                    "DE SERVICIOS PROFESIONALES Y DE APOYO A LA GESTIÓN."
                ),
            )
        elif "mediante memorando de radicado" in texto:
            fecha_txt = formato_fecha_larga(fecha_salida) or formato_fecha_larga(fecha_respuesta)
            if radicado:
                _set_paragraph_text(
                    p,
                    (
                        "Importante resaltar que la Dirección para la Gestión del Desarrollo Local "
                        f"a través del radicado {radicado} del {fecha_txt}, emitió "
                        "“RECOMENDACIONES, SUGERENCIAS Y ALERTAS TEMPRANAS” con la finalidad de dar "
                        "seguridad técnica y jurídica a los Fondos de Desarrollo Local."
                    ),
                )
        elif texto.startswith("Proyectó:"):
            _set_paragraph_text(p, f"Proyectó: {profesional} - Profesional DGDL")

    body = doc.element.body
    borrar = False
    for child in list(body):
        if child is first_solicitud._p:
            borrar = True
        if child is recomendaciones._p:
            borrar = False
        if borrar:
            body.remove(child)

    anchor = recomendaciones._p
    for fila in filas:
        _insertar_parrafo(anchor, sample_heading, f"SOLICITUD {_texto(fila.get('sipse')) or _texto(fila.get('archivo'))}".strip())
        _insertar_blanco(anchor, sample_blank)
        tbl_xml = copy.deepcopy(sample_table)
        tabla = Table(tbl_xml, doc)
        _llenar_tabla_solicitud(tabla, fila)
        anchor.addprevious(tbl_xml)
        _insertar_blanco(anchor, sample_blank)
        _insertar_parrafo(anchor, sample_normal, "Observaciones respecto de se ajusta Si/No:")
        _insertar_blanco(anchor, sample_blank)
        _insertar_parrafo(anchor, sample_normal, _texto_observacion_vigencia(fila))
        _insertar_blanco(anchor, sample_blank)
        _insertar_parrafo(anchor, sample_intro, "En cuanto a la información que registra a la fecha en el contrato electrónico se observa que:")
        _insertar_blanco(anchor, sample_blank)
        _insertar_parrafo(anchor, sample_normal, "El contratista ha cargado la documentación e información que evidencia su ejecución contractual.")
        _insertar_blanco(anchor, sample_blank)
        _insertar_blanco(anchor, sample_blank)

    _quitar_resaltados(doc)
    salida = BytesIO()
    doc.save(salida)
    return salida.getvalue()


def generar_zip_asistencia(
    filas: Iterable[dict],
    plantilla_docx: Path,
    fecha_respuesta: date,
    profesional: str,
) -> tuple[bytes, str, list[dict]]:
    filas_ordenadas = ordenar_filas(filas)
    if not filas_ordenadas:
        raise ValueError("No hay solicitudes para generar.")

    resumen: list[dict] = []
    salida = BytesIO()
    with zipfile.ZipFile(salida, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        localidades = []
        for fila in filas_ordenadas:
            localidad = _canon_localidad(fila.get("localidad", ""))
            if localidad and localidad not in localidades:
                localidades.append(localidad)
        for localidad in localidades:
            grupo = [f for f in filas_ordenadas if _canon_localidad(f.get("localidad", "")) == localidad]
            docx = generar_documento_localidad(grupo, plantilla_docx, fecha_respuesta, profesional)
            nombre = f"Respuesta asistencia tecnica {localidad} {fecha_respuesta.year}.docx"
            zf.writestr(nombre, docx)
            resumen.append({"localidad": localidad, "solicitudes": len(grupo), "archivo": nombre})

        excel = generar_excel_asistencia(filas_ordenadas, profesional=profesional)
        zf.writestr("Matriz asistencia tecnica CPS.xlsx", excel)

    localidades_txt = ",".join(_canon_localidad(f.get("localidad", "")) for f in filas_ordenadas)
    nombre_zip = f"Asistencia tecnica CPS {fecha_respuesta.year} ({_nombre_archivo_seguro(localidades_txt)[:80]}).zip"
    return salida.getvalue(), nombre_zip, resumen
