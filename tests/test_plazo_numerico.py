from io import BytesIO
import unittest
from docx import Document
from asistencia_tecnica import _normalizar_plazo
from test_asistencia_tecnica_word import generar, solicitud


class PlazoNumericoTest(unittest.TestCase):
    def test_formatos_del_plazo(self):
        for original, esperado in (
            ('ocho (8) meses','8 meses'), ('OCHO(8)MESES','8 meses'),
            ('SEIS (06) MESES','6 meses'), ('ocho meses','8 meses'),
            ('ocho (8) meses y quince (15) días','8 meses y 15 días'),
            ('un (1) mes y un (1) día','1 mes y 1 día'),
            ('(8) meses y (15) días','8 meses y 15 días'),
            ('treinta y un (31) días','31 días'), ('15 días','15 días'),
            ('8 meses','8 meses'), ('',''), ('N/A','n/a'),
            ('hasta el 31/12/2026','hasta el 31/12/2026'),
        ):
            with self.subTest(original=original):
                self.assertEqual(_normalizar_plazo(original), esperado)

    def test_word_normaliza_incluso_datos_editados(self):
        d=Document(BytesIO(generar([solicitud(plazo_inicial='nueve (9) meses')])))
        self.assertEqual(d.tables[0].rows[6].cells[1].text,'9 meses')
