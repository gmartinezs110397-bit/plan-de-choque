from io import BytesIO
import importlib.util
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from asistencia_tecnica import extraer_texto_pdf, extraer_radicados, _texto_pdf_necesita_ocr, _extraer_localidad
from pdf_ocr import extraer_paginas_ocr


TEXTO_LEGIBLE = (
    "SOLICITUD DE MODIFICACION CONTRACTUAL. Numero Contrato: FDLC-CPS-024-2026. "
    "Fecha de inicio: 16/01/2026. Plazo inicial: 9 meses. Prorroga solicitada: 3 meses."
)


def pdf_con_paginas(textos):
    writer = PdfWriter()
    for texto in textos:
        pagina = writer.add_blank_page(width=612, height=792)
        if texto:
            fuente = DictionaryObject({
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            })
            pagina[NameObject("/Resources")] = DictionaryObject({
                NameObject("/Font"): DictionaryObject({NameObject("/F1"): fuente})
            })
            stream = DecodedStreamObject()
            # Una cadena hexadecimal evita escapes propios del contenido PDF.
            texto_hex = texto.encode("latin1").hex()
            stream.set_data(f"BT /F1 11 Tf 30 700 Td <{texto_hex}> Tj ET".encode("ascii"))
            pagina[NameObject("/Contents")] = writer._add_object(stream)
    salida = BytesIO()
    writer.write(salida)
    return salida.getvalue()


class RespaldoPDFTest(unittest.TestCase):
    def test_pdf_legible_no_invoca_ocr(self):
        with patch("pdf_ocr.extraer_paginas_ocr") as ocr:
            texto, avisos = extraer_texto_pdf("solicitud.pdf", pdf_con_paginas([TEXTO_LEGIBLE]))
        self.assertIn("Prorroga solicitada: 3 meses", texto)
        self.assertEqual(avisos, [])
        ocr.assert_not_called()

    def test_pdf_mixto_conserva_texto_y_orden(self):
        contenido = pdf_con_paginas([TEXTO_LEGIBLE, "", TEXTO_LEGIBLE.replace("024", "060")])
        with patch("pdf_ocr.extraer_paginas_ocr", return_value=({1: "PAGINA ESCANEADA 30/12/2026"}, [])) as ocr:
            texto, avisos = extraer_texto_pdf("mixto.pdf", contenido)
        ocr.assert_called_once_with(contenido, [1])
        self.assertLess(texto.index("024-2026"), texto.index("PAGINA ESCANEADA"))
        self.assertLess(texto.index("PAGINA ESCANEADA"), texto.index("060-2026"))
        self.assertIn("página(s) 2", avisos[0])

    def test_texto_codificado_con_reparacion_no_invoca_ocr(self):
        self.assertFalse(_texto_pdf_necesita_ocr(TEXTO_LEGIBLE.replace("9 meses", "\x1c PHVHV")))
        self.assertTrue(_texto_pdf_necesita_ocr("\ufffd" * 200))
        self.assertTrue(_texto_pdf_necesita_ocr("XYZABC " * 100))

    def test_localidad_no_absorbe_etiquetas_del_encabezado(self):
        self.assertEqual(
            _extraer_localidad("Alcaldía Local de la Candelaria Fecha de Solicitud: 19/08/2026"),
            "La Candelaria",
        )

    def test_fallo_pypdf_intenta_ocr_completo(self):
        contenido = pdf_con_paginas([TEXTO_LEGIBLE])
        with patch("pypdf.PdfReader", side_effect=ValueError("fuente ilegible")):
            with patch("pdf_ocr.extraer_paginas_ocr", return_value=({0: TEXTO_LEGIBLE}, [])) as ocr:
                texto, avisos = extraer_texto_pdf("solicitud.pdf", contenido)
        ocr.assert_called_once_with(contenido, None)
        self.assertEqual(texto, TEXTO_LEGIBLE)
        self.assertFalse(any("fuente ilegible" in aviso for aviso in avisos))

    def test_pdf_con_password_deja_aviso_sin_ocr(self):
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.encrypt("password-de-prueba")
        contenido = BytesIO()
        writer.write(contenido)
        with patch("pdf_ocr.extraer_paginas_ocr") as ocr:
            texto, avisos = extraer_texto_pdf("protegido.pdf", contenido.getvalue())
        self.assertEqual(texto, "")
        self.assertIn("contraseña", avisos[0])
        ocr.assert_not_called()

    def test_fallo_ocr_conserva_paginas_legibles(self):
        with patch("pdf_ocr.extraer_paginas_ocr", return_value=({}, ["No se pudo leer la página 2."])):
            texto, avisos = extraer_texto_pdf("mixto.pdf", pdf_con_paginas([TEXTO_LEGIBLE, ""]))
        self.assertIn("FDLC-CPS-024-2026", texto)
        self.assertIn("mixto.pdf: No se pudo", avisos[0])

    def test_radicado_legible_corto_no_invoca_ocr(self):
        self.assertFalse(_texto_pdf_necesita_ocr("Radicado: 20262100323333"))

    def test_listado_ocr_incompleto_no_desplaza_radicados(self):
        with patch("asistencia_tecnica.extraer_texto_pdf", return_value=("20262100323333", ["Listado (OCR)"])):
            mapa, _, avisos = extraer_radicados(b"pdf")
        self.assertEqual(mapa, {})
        self.assertTrue(any("20 radicados" in aviso for aviso in avisos))

    def test_listado_ocr_completo_asigna_radicados(self):
        texto = " ".join(str(20262100323333 + i) for i in range(20))
        with patch("asistencia_tecnica.extraer_texto_pdf", return_value=(texto, ["Listado (OCR)"])):
            mapa, _, _ = extraer_radicados(b"pdf")
        self.assertEqual(len(mapa), 20)
        self.assertEqual(mapa["Kennedy"], "20262100323340")

    def test_fallo_una_pagina_ocr_continua_con_la_siguiente(self):
        if not importlib.util.find_spec("pytesseract") or not importlib.util.find_spec("pypdfium2"):
            self.skipTest("Dependencias OCR no instaladas")
        with patch("pdf_ocr.shutil.which", return_value="tesseract"):
            with patch("pytesseract.get_languages", return_value=["spa", "eng"]):
                with patch("pdf_ocr._leer_imagen_en_orden", side_effect=[RuntimeError("timeout"), TEXTO_LEGIBLE]):
                    textos, avisos = extraer_paginas_ocr(pdf_con_paginas(["", ""]))
        self.assertEqual(textos, {1: TEXTO_LEGIBLE})
        self.assertIn("página 1", avisos[0])

    def test_ocr_real_lee_cada_casilla_completa(self):
        instalado = shutil.which("tesseract") or (Path.home() / "AppData/Local/Programs/Tesseract-OCR/tesseract.exe").is_file()
        if not instalado or not importlib.util.find_spec("pytesseract") or not importlib.util.find_spec("pypdfium2"):
            self.skipTest("Motor OCR no instalado")
        from PIL import Image, ImageDraw, ImageFont

        imagen = Image.new("RGB", (1600, 900), "white")
        dibujar = ImageDraw.Draw(imagen)
        fuente = ImageFont.load_default(size=30)
        dibujar.rectangle((80, 100, 1520, 500), outline="black", width=3)
        dibujar.line((800, 100, 800, 500), fill="black", width=3)
        dibujar.line((80, 300, 1520, 300), fill="black", width=3)
        dibujar.text((110, 130), "Numero Contrato: FDLC-", fill="black", font=fuente)
        dibujar.text((110, 180), "CPS-024-2026", fill="black", font=fuente)
        dibujar.text((830, 130), "Fecha de Suscripcion: 14 de", fill="black", font=fuente)
        dibujar.text((830, 180), "enero de 2026", fill="black", font=fuente)
        dibujar.text((110, 330), "Plazo Inicial: 9 meses", fill="black", font=fuente)
        dibujar.text((830, 330), "Fecha de Inicio: 16/01/2026", fill="black", font=fuente)
        contenido = BytesIO()
        imagen.save(contenido, format="PDF", resolution=150)
        imagen.close()
        texto, avisos = extraer_texto_pdf("escaneado.pdf", contenido.getvalue())
        if any("idioma español" in aviso for aviso in avisos):
            self.skipTest("Idioma español no instalado")
        self.assertIn("CPS-024-2026", texto)
        self.assertIn("16/01/2026", texto)
        self.assertLess(texto.index("CPS-024-2026"), texto.index("Fecha de Suscripcion"))
        self.assertTrue(any("OCR" in aviso for aviso in avisos))

    def test_motor_no_disponible_informa_y_no_aborta(self):
        with patch("pdf_ocr.shutil.which", return_value=None), patch("pdf_ocr.Path.is_file", return_value=False):
            texto, avisos = extraer_texto_pdf("escaneado.pdf", pdf_con_paginas([""]))
        self.assertEqual(texto, "")
        self.assertTrue(avisos)


if __name__ == "__main__":
    unittest.main()
