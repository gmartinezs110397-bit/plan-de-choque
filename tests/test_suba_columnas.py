"""Numeral II con encabezados partidos y tres columnas intercaladas."""
import unittest
from asistencia_tecnica import _extraer_adicion_numeral_dos, _extraer_prorroga_numeral_dos


class SubaColumnasTest(unittest.TestCase):
    CUERPO = '''Adición Valor Prórroga Tiempo Modificación o aclaración otras cláusulas
    DIECIOCHO MILLONES Tiempo: SOLICITUD ADICIÓN Y PRORROGA
    EN CONSECUENCIA, SE MODIFICA SU CLÁUSULA TERCERA Y QUINTA
    TRESCIENTOS SETENTA Y TRES (3) MESES Y CINCO
    NUEVE MIL TRESCIENTOS TREINTA Y TRES PESOS M/CTE
    ($18.379.333) (5) DIAS Fecha Terminación Final: 31/12/2026
    III. INFORMACIÓN DE MODIFICACIONES ANTERIORES
    Adición Valor $99.000 Tiempo: 1 mes Fecha Terminación Final: 01/01/2025'''

    def test_encabezados_partidos_lecturas_lineal_y_visual(self):
        for titulo in (
            'II. INFORMACIÓN SOLICITADA DE LA MODIFICACIÓN MODIFICACIÓN No.02 ',
            'II. INFORMACIÓN DE LA MODIFICACIÓN MODIFICACIÓN No.02 SOLICITADA ',
            'II. INFORMACIÓN DE LA MODIFICACIÓN SOLICITADA ',
        ):
            with self.subTest(titulo=titulo):
                texto = titulo + self.CUERPO
                self.assertEqual(_extraer_adicion_numeral_dos(texto)[1], 18379333)
                self.assertEqual(_extraer_prorroga_numeral_dos(texto), '3 meses y 5 días')

    def test_no_usa_prorroga_del_numeral_tres(self):
        texto = ('II. INFORMACIÓN SOLICITADA DE LA MODIFICACIÓN Tiempo: N/A '
                 'III. INFORMACIÓN DE MODIFICACIONES ANTERIORES Tiempo: 4 meses')
        self.assertEqual(_extraer_prorroga_numeral_dos(texto), '')

    def test_no_usa_valor_del_estado_financiero(self):
        texto = ('II. INFORMACIÓN SOLICITADA DE LA MODIFICACIÓN Adición Valor Prórroga Tiempo '
                 'ESTADO FINANCIERO Valor a Adicionar: $18.379.333')
        self.assertEqual(_extraer_adicion_numeral_dos(texto), ('', None))

    def test_duracion_repetida_y_conflictos(self):
        titulo = 'II. INFORMACIÓN DE LA MODIFICACIÓN SOLICITADA Tiempo: '
        self.assertEqual(_extraer_prorroga_numeral_dos((titulo + '3 meses y 5 días ') * 2), '3 meses y 5 días')
        self.assertEqual(_extraer_prorroga_numeral_dos(titulo + '3 meses ' + titulo + '5 meses'), '')
