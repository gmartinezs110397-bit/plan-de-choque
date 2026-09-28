"""Los centavos no deben multiplicar por cien los valores contractuales."""
from io import BytesIO
import unittest
from docx import Document
from asistencia_tecnica import _a_numero, formato_moneda, _calcular_validacion_solicitud
from test_asistencia_tecnica_word import generar, solicitud


class MonedaDecimalesTest(unittest.TestCase):
    def test_separadores_miles_y_decimales(self):
        for texto in (
            '$37.136.000,00', '$ 37,136,000.00', '37136000,00', '37136000.00',
            '$37.136.000', '$37,136,000', 37136000, 37136000.0,
            'TREINTA Y SIETE MILLONES CIENTO TREINTA Y SEIS MIL PESOS M/CTE ($37.136.000,00)',
        ):
            with self.subTest(texto=texto):
                self.assertEqual(_a_numero(texto), 37136000)
                self.assertEqual(formato_moneda(texto), '$37.136.000')

    def test_redondeo_a_pesos_sin_agregar_ceros(self):
        for texto, esperado in (
            ('$1.234,49',1234), ('$1.234,51',1235), ('1234,5',1234),
            ('0,00',0), ('-1.234,51',-1235), ('$1.234',1234),
            ('1,234',1234), ('100',100), ('N/A',None), ('',None), (None,None),
        ):
            with self.subTest(texto=texto):
                self.assertEqual(_a_numero(texto), esperado)

    def test_calculo_adicion_no_multiplica_centavos(self):
        fila=solicitud(
            fecha_inicio='23/01/2026', fecha_terminacion_inicial='22/09/2026',
            plazo_inicial='8 meses', valor_inicial_texto='$37.136.000,00',
            valor_inicial=37136000, prorroga_solicitada='3 meses y 8 días',
            fecha_terminacion_final='31/12/2026',
            valor_adicion_texto='$15.163.867,00', valor_adicion=15163867,
        )
        validacion=_calcular_validacion_solicitud(fila)
        self.assertEqual(validacion['valor_adicion_teorico'],15163867)
        self.assertTrue(validacion['se_ajusta_adicion'])

    def test_word_desde_valor_numerico_del_editor(self):
        fila=solicitud(valor_inicial=_a_numero('$37.136.000,00'), valor_inicial_texto='')
        doc=Document(BytesIO(generar([fila])))
        self.assertEqual(doc.tables[0].rows[7].cells[1].text,'$37.136.000')
