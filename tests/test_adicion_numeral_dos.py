"""Regresiones de adiciones en solicitudes con tablas partidas entre páginas."""
import unittest
from asistencia_tecnica import _extraer_adicion_numeral_dos


class AdicionNumeralDosTest(unittest.TestCase):
    TITULO = 'II. INFORMACIÓN DE LA MODIFICACIÓN SOLICITADA '

    def test_tabla_continua_tras_pagina_y_resumen_duplicado(self):
        for inicial, adicion in (('24.760.000', '8.975.500'), ('44.000.000', '16.133.333')):
            with self.subTest(adicion=adicion):
                texto = (
                    'I. RESUMEN CONTRACTUAL Valor inicial $' + inicial + ' '
                    + self.TITULO + 'Adición Valor Prórroga Tiempo '
                    + 'I. RESUMEN CONTRACTUAL Valor inicial $' + inicial + ' '
                    + self.TITULO + 'Adición Valor Prórroga Tiempo '
                    + 'Página 1 de 5 Página 2 de 5 $' + adicion + ' 2 meses y 27 días '
                    + 'III. INFORMACIÓN DE MODIFICACIONES ANTERIORES Valor Adición $1.000'
                )
                self.assertEqual(_extraer_adicion_numeral_dos(texto)[1], int(adicion.replace('.', '')))

    def test_formato_numeracion_arabiga(self):
        self.assertEqual(_extraer_adicion_numeral_dos(
            '2. INFORMACION DE LA MODIFICACION SOLICITADA Valor a Adicionar: $19.500.000'
        )[1], 19500000)

    def test_repeticion_del_mismo_valor_no_es_conflicto(self):
        texto = (self.TITULO + 'Valor Adición $8.975.500 ') * 2
        self.assertEqual(_extraer_adicion_numeral_dos(texto)[1], 8975500)

    def test_lecturas_con_valores_distintos_no_se_adivinan(self):
        texto = self.TITULO + 'Valor Adición $8.975.500 ' + self.TITULO + 'Valor Adición $8.975.000'
        self.assertEqual(_extraer_adicion_numeral_dos(texto), ('', None))

    def test_no_toma_valores_de_otros_numerales(self):
        for texto in (
            'I. RESUMEN CONTRACTUAL Valor Adición $24.760.000',
            self.TITULO + 'Adición Valor Prórroga Tiempo I. RESUMEN CONTRACTUAL $24.760.000',
            self.TITULO + 'Sin adición III. INFORMACIÓN DE MODIFICACIONES ANTERIORES Valor Adición $1.000',
            self.TITULO + 'Sin adición ESTADO FINANCIERO Valor Adición $1.000',
        ):
            with self.subTest(texto=texto):
                self.assertEqual(_extraer_adicion_numeral_dos(texto), ('', None))


if __name__ == '__main__':
    unittest.main()
