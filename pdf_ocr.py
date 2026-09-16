from __future__ import annotations

import math
import shutil
from contextlib import closing
from pathlib import Path
from threading import Lock
from typing import Iterable


# PDFium comparte estado nativo entre las sesiones de Streamlit.
_PDFIUM_LOCK = Lock()
_OCR_MAX_PIXELES = 12_000_000
_OCR_TIMEOUT_SEGUNDOS = 45


def _leer_imagen_en_orden(imagen, pytesseract, idioma: str) -> str:
    import cv2
    import numpy as np

    gris = np.asarray(imagen.convert("L"))
    binaria = cv2.adaptiveThreshold(
        gris, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 15
    )
    alto, ancho = gris.shape
    horizontales = cv2.morphologyEx(
        binaria, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(40, ancho // 30), 1)),
    )
    verticales = cv2.morphologyEx(
        binaria, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(80, alto // 25))),
    )
    rejilla = cv2.bitwise_or(horizontales, verticales)
    contornos, jerarquia = cv2.findContours(rejilla, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    celdas = []
    if jerarquia is not None:
        for indice, contorno in enumerate(contornos):
            if jerarquia[0][indice][3] < 0:
                continue
            x, y, w, h = cv2.boundingRect(contorno)
            if w >= 40 and h >= 25:
                celdas.append((x, y, w, h))
    celdas.sort(key=lambda celda: celda[2] * celda[3])
    sin_lineas = cv2.bitwise_or(gris, rejilla)
    datos = pytesseract.image_to_data(
        sin_lineas,
        lang=idioma,
        config="--psm 3",
        output_type=pytesseract.Output.DICT,
        timeout=_OCR_TIMEOUT_SEGUNDOS,
    )
    grupos: dict[tuple, list[int]] = {}
    for indice, texto in enumerate(datos["text"]):
        if not texto.strip() or texto.strip() == "|":
            continue
        centro_x = datos["left"][indice] + datos["width"][indice] / 2
        centro_y = datos["top"][indice] + datos["height"][indice] / 2
        celda = next((
            numero for numero, (x, y, w, h) in enumerate(celdas)
            if x <= centro_x <= x + w and y <= centro_y <= y + h
        ), None)
        linea = tuple(datos[campo][indice] for campo in ("block_num", "par_num", "line_num"))
        clave = ("celda", celda) if celda is not None else ("linea", *linea)
        grupos.setdefault(clave, []).append(indice)

    bloques = []
    for clave, palabras in grupos.items():
        lineas: dict[tuple, list[int]] = {}
        for indice in palabras:
            linea = tuple(datos[campo][indice] for campo in ("block_num", "par_num", "line_num"))
            lineas.setdefault(linea, []).append(indice)
        ordenadas = sorted(lineas.values(), key=lambda lista: min(datos["top"][i] for i in lista))
        texto = " ".join(
            " ".join(datos["text"][i] for i in sorted(lista, key=lambda i: datos["left"][i]))
            for lista in ordenadas
        )
        if clave[0] == "celda":
            x, y, w, h = celdas[clave[1]]
            if any(float(datos["conf"][i]) < 30 for i in palabras):
                recorte = sin_lineas[y + 3:y + h - 3, x + 3:x + w - 3]
                try:
                    releido = pytesseract.image_to_string(
                        recorte, lang=idioma, config="--psm 6",
                        timeout=_OCR_TIMEOUT_SEGUNDOS,
                    ).strip()
                    if releido:
                        texto = releido
                except RuntimeError:
                    pass
        else:
            x = min(datos["left"][i] for i in palabras)
            y = min(datos["top"][i] for i in palabras)
        bloques.append((y, x, texto))
    # Leer cada casilla completa evita entrelazar las columnas de las solicitudes.
    bloques.sort(key=lambda bloque: (round(bloque[0] / 10), bloque[1]))
    return "\n".join(texto for _, _, texto in bloques)


def extraer_paginas_ocr(
    contenido: bytes, indices: Iterable[int] | None = None
) -> tuple[dict[int, str], list[str]]:
    textos: dict[int, str] = {}
    avisos: list[str] = []
    try:
        import cv2
        import numpy
        import pytesseract
        with _PDFIUM_LOCK:
            import pypdfium2 as pdfium
    except ImportError:
        return {}, ["El lector de PDF escaneado no está disponible en este entorno."]

    ejecutable = shutil.which("tesseract")
    if not ejecutable:
        carpetas = (
            Path("C:/Program Files/Tesseract-OCR"),
            Path("C:/Program Files (x86)/Tesseract-OCR"),
            Path.home() / "AppData/Local/Programs/Tesseract-OCR",
        )
        for carpeta in carpetas:
            candidato = carpeta / "tesseract.exe"
            if candidato.is_file():
                ejecutable = str(candidato)
                break
    if not ejecutable:
        return {}, ["No está instalado el lector de PDF escaneado (Tesseract)."]
    pytesseract.pytesseract.tesseract_cmd = ejecutable
    try:
        idiomas = pytesseract.get_languages()
        if "spa" not in idiomas:
            return {}, ["El lector de PDF escaneado necesita el idioma español instalado."]
        idioma = "spa+eng" if "eng" in idiomas else "spa"
        with _PDFIUM_LOCK:
            documento = pdfium.PdfDocument(contenido)
    except Exception as exc:
        return {}, [f"No se pudo abrir el PDF para leerlo como imagen ({exc})."]

    try:
        with _PDFIUM_LOCK:
            seleccion = range(len(documento)) if indices is None else sorted(set(indices))
        for indice in seleccion:
            try:
                with _PDFIUM_LOCK:
                    with closing(documento[indice]) as pagina:
                        ancho, alto = pagina.get_size()
                        escala = min(300 / 72, math.sqrt(_OCR_MAX_PIXELES / (ancho * alto)))
                        with closing(pagina.render(scale=escala)) as bitmap:
                            with bitmap.to_pil() as original:
                                imagen = original.copy()
                with imagen:
                    texto = _leer_imagen_en_orden(imagen, pytesseract, idioma).strip()
                if texto:
                    textos[indice] = texto
                else:
                    avisos.append(f"No se reconoció texto en la página {indice + 1}; revise la solicitud.")
            except Exception as exc:
                avisos.append(f"No se pudo leer la página {indice + 1} como imagen ({exc}).")
    finally:
        with _PDFIUM_LOCK:
            documento.close()
    return textos, avisos
