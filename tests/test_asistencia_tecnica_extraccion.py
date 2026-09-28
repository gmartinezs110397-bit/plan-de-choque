import unittest
from unittest.mock import patch

from asistencia_tecnica import (
    analizar_solicitud_pdf, enriquecer_con_radicados, extraer_radicados,
    _normalizar_plazo,
)
from test_pdf_ocr import pdf_con_paginas

RESUMEN = '''1. RESUMEN CONTRACTUAL
Número Contrato: CPS-123 Fecha de Suscripción: 01/01/2026
Tipo de Contrato: CPS Plazo Inicial: OCHO (8) MESES Fecha de Inicio: 01/01/2026
Fecha de Terminación Inicial: 31/08/2026 Objeto: APOYO LOCAL
Contratista: ANA PEREZ Supervisor: JUAN CARLOS PEREZ LOPEZ
Valor Inicial: $80.000.000 Valor Total Actual: $80.000.000
'''
MODIFICACION = '''Prórroga: 3 meses Valor a Adicionar: $30.000.000
Fecha de Terminación con la Prórroga: 30/11/2026
'''


class FuentesSolicitudTest(unittest.TestCase):
    def analizar(self, texto):
        with patch('asistencia_tecnica.extraer_texto_pdf', return_value=(texto, [])):
            return analizar_solicitud_pdf('solicitud.pdf', b'pdf')

    def test_numerales_separan_fuentes_y_preservan_tres_meses(self):
        fila, _ = self.analizar(RESUMEN + '2. INFORMACIÓN DE LA MODIFICACIÓN SOLICITADA\n' + MODIFICACION
                                + '3. INFORMACIÓN DE MODIFICACIONES ANTERIORES Prórroga: 9 meses')
        self.assertEqual(fila['contrato'], 'CPS-123')
        self.assertEqual(fila['objeto'], 'APOYO LOCAL')
        self.assertEqual(fila['plazo_inicial'], '8 meses')
        self.assertEqual(fila['prorroga_solicitada'], '3 meses')
        self.assertEqual(fila['valor_adicion'], 30000000)
        self.assertEqual(fila['fecha_terminacion_final'], '30/11/2026')
        self.assertEqual(fila['supervisor'], '')

    def test_no_recupera_modificacion_de_otras_secciones(self):
        fila, avisos = self.analizar(RESUMEN + MODIFICACION)
        self.assertEqual(fila['prorroga_solicitada'], '')
        self.assertIsNone(fila['valor_adicion'])
        self.assertEqual(fila['fecha_terminacion_final'], '')
        self.assertTrue(any('numeral 2' in a for a in avisos))

    def test_sin_resumen_no_usa_datos_del_resto(self):
        fila, _ = self.analizar('2. INFORMACIÓN DE LA MODIFICACIÓN SOLICITADA ' + RESUMEN.split('\n', 1)[1])
        for campo in ('contrato', 'contratista', 'objeto', 'plazo_inicial', 'fecha_inicio', 'fecha_terminacion_inicial'):
            self.assertEqual(fila[campo], '')

    def test_titulo_en_pagina_anterior(self):
        contenido = pdf_con_paginas([
            RESUMEN + 'II. INFORMACIÓN DE LA MODIFICACIÓN SOLICITADA',
            MODIFICACION + 'III. INFORMACIÓN DE MODIFICACIONES ANTERIORES Prórroga: 9 meses',
        ])
        fila, _ = analizar_solicitud_pdf('dos_paginas.pdf', contenido)
        self.assertEqual(fila['prorroga_solicitada'], '3 meses')
        self.assertEqual(fila['valor_adicion'], 30000000)

    def test_tabla_continua_con_encabezados_y_valores_en_letras(self):
        # Estructura de Sumapaz: encabezado en página 1 y celdas en página 2.
        from docx import Document
        from asistencia_tecnica import _llenar_tabla_solicitud
        casos = (
            ('24.760.000', '8.975.500', 'VEINTISIETE (27) DIAS', '2 meses y 27 días'),
            ('44.000.000', '16.133.333', 'VEINTIOCHO (28) DÍAS', '2 meses y 28 días'),
        )
        for inicial, adicion, dias, prorroga in casos:
            with self.subTest(adicion=adicion):
                resumen = RESUMEN.replace('$80.000.000 Valor Total Actual: $80.000.000',
                    f'IMPORTE EN LETRAS (${inicial}) Apoyo a la supervisión: PERSONA DE APOYO '
                    'Número del proceso: PROCESO-001')
                paginas = [
                    resumen + 'II. INFORMACIÓN DE LA MODIFICACIÓN SOLICITADA MODIFICACIÓN No. 002 '
                    'Adición Valor Prórroga Tiempo Modificación o aclaración otras cláusulas',
                    'SOLICITUD DE MODIFICACIÓN CONTRACTUAL Edificio Liévano Código: GCO-GCI-F017 '
                    'Página 2 de 5 IMPORTE EN LETRAS ($' + adicion + ') Tiempo: DOS (2) MESES Y '
                    + dias + ' Fecha Terminación Final: 30/12/2026 '
                    'III. INFORMACIÓN DE MODIFICACIONES ANTERIORES Adición Valor Prórroga Tiempo '
                    'Valor: $99.000.000 Tiempo: 9 meses Fecha Terminación Final: 01/01/2027 '
                    'ESTADO FINANCIERO DEL CONTRATO Valor total: $' + inicial,
                ]
                fila, _ = analizar_solicitud_pdf('ejemplo.pdf', pdf_con_paginas(paginas))
                self.assertEqual(fila['valor_adicion_texto'], '$' + adicion)
                self.assertEqual(fila['prorroga_solicitada'], prorroga)
                self.assertEqual(fila['fecha_terminacion_final'], '30/12/2026')
                self.assertNotIn('PERSONA DE APOYO', fila['valor_inicial_texto'])
                doc = Document()
                tabla = doc.add_table(rows=12, cols=4)
                _llenar_tabla_solicitud(tabla, fila)
                self.assertEqual(tabla.rows[6].cells[1].text, '8 meses')
                self.assertEqual(tabla.rows[9].cells[1].text, prorroga)
                self.assertEqual(tabla.rows[10].cells[1].text, '$' + adicion)
                self.assertEqual(tabla.rows[11].cells[1].text, '30/12/2026')

    def test_plazo(self):
        for texto in ('OCHO (8) MESES', 'ocho meses', '8 meses contados desde el acta de inicio'):
            self.assertEqual(_normalizar_plazo(texto), '8 meses')


class SupervisorRadicadoTest(unittest.TestCase):
    def test_fuente_y_nombre_parcial(self):
        texto = '20260000000001\nSupervisor: Juan Pérez\nSupervisor: Pedro Gómez\n20260000000002\nSupervisor: Otra Persona'
        nombres = {}
        with patch('asistencia_tecnica.extraer_texto_pdf', return_value=(texto, [])):
            mapa, fecha, _ = extraer_radicados(b'pdf', supervisores=nombres)
        fila = {'localidad': 'Usaquén', 'supervisor_solicitud': 'Juan Carlos Pérez López', 'supervisor': 'NO USAR'}
        resultado = enriquecer_con_radicados([fila], mapa, fecha, nombres)
        self.assertEqual(resultado[0]['supervisor'], 'Juan Pérez')

    def test_ambiguo_o_ausente_queda_vacio(self):
        fila = {'localidad': 'Usaquén', 'supervisor_solicitud': 'Juan Pérez', 'supervisor': 'NO USAR'}
        for candidatos in ([], ['Juan Carlos Pérez', 'Juan Andrés Pérez'], ['Otra Persona', 'Pedro Gómez']):
            avisos = []
            resultado = enriquecer_con_radicados([fila], {'Usaquén': '123'}, None, {'123': candidatos}, avisos)
            self.assertEqual(resultado[0]['supervisor'], '')
            self.assertTrue(avisos)

    def test_unico_del_radicado_prevalece_aunque_solicitud_difiera(self):
        resultado = enriquecer_con_radicados(
            [{'localidad': 'Usaquén', 'supervisor_solicitud': 'Nombre Anterior'}],
            {'Usaquén': '123'}, None, {'123': ['Nombre Vigente']})
        self.assertEqual(resultado[0]['supervisor'], 'Nombre Vigente')


if __name__ == '__main__':
    unittest.main()
