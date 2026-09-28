from datetime import date
from io import BytesIO
import unittest
from unittest.mock import patch
from docx import Document
from asistencia_tecnica import extraer_radicados, enriquecer_con_radicados, LOCALIDADES_RADICADO
from test_asistencia_tecnica_word import generar, solicitud


def tabla(orden=range(1,21), nombres=None):
    nombres=nombres or {}
    return 'LISTADO DE RADICACION MASIVA\nUsuario Responsable: NOMBRE QUE NO ES SUPERVISOR\nFecha: 31-08-31\n# Radicado Nombre Dirección\n'+'\n'.join(
        f'{i} {20262100323000+i} {nombres.get(i,"NOMBRE APELLIDO PERSONA")} Despacho Alcaldia Local de Su D.C. BOGOTA'
        for i in orden
    )


def leer(texto):
    nombres={}
    with patch('asistencia_tecnica.extraer_texto_pdf',return_value=(texto,[])):
        mapa,fecha,avisos=extraer_radicados(b'pdf',nombres)
    return mapa,fecha,avisos,nombres


class SupervisorRadicadosTest(unittest.TestCase):
    def test_veinte_filas_y_nombres_de_su_radicado(self):
        mapa,fecha,avisos,nombres=leer(tabla(nombres={11:'CESAR AUGUSTO SALAMANCA ROJAS',20:'OTRA PERSONA'}))
        self.assertEqual(len(mapa),20)
        self.assertEqual(len(nombres),20)
        self.assertEqual(nombres[mapa['Suba']],['CESAR AUGUSTO SALAMANCA ROJAS'])
        self.assertEqual(nombres[mapa['Sumapaz']],['OTRA PERSONA'])
        self.assertEqual(fecha,date(2026,8,31))
        self.assertEqual(avisos,[])

    def test_lecturas_repetidas_no_duplican(self):
        texto=tabla()
        mapa,_,avisos,nombres=leer(texto+'\n'+texto)
        self.assertEqual(len(mapa),20)
        self.assertTrue(all(len(n)==1 for n in nombres.values()))
        self.assertEqual(avisos,[])

    def test_orden_de_extraccion_no_cambia_localidad(self):
        mapa,_,_,_=leer(tabla(reversed(range(1,21))))
        for i,localidad in enumerate(LOCALIDADES_RADICADO,1):
            self.assertEqual(mapa[localidad],str(20262100323000+i))

    def test_fila_ausente_no_desplaza_localidades(self):
        mapa,_,avisos,_=leer(tabla(i for i in range(1,21) if i!=4))
        self.assertEqual(mapa,{})
        self.assertTrue(avisos)

    def test_nombre_solicitud_incompleto_no_exige_match_exacto(self):
        mapa,fecha,_,nombres=leer(tabla(nombres={11:'CESAR AUGUSTO SALAMANCA ROJAS'}))
        for original in ['CÉSAR SALAMANCA ROJAS','Cesar Salamanca','OTRO SUPERVISOR / APOYO A LA SUPERVISIÓN']:
            with self.subTest(original=original):
                entrada=solicitud(localidad='Suba',supervisor=original)
                errores=[]
                fila=enriquecer_con_radicados([entrada],mapa,fecha,nombres,errores)[0]
                self.assertEqual(fila['supervisor'],'CESAR AUGUSTO SALAMANCA ROJAS')
                self.assertEqual(entrada['supervisor'],original)
                self.assertEqual(errores,[])

    def test_nombre_truncado_del_listado_se_conserva(self):
        mapa,fecha,_,nombres=leer(tabla(nombres={1:'DANIEL HERNANDO ORTIZ QUINTER'}))
        fila=enriquecer_con_radicados([solicitud(localidad='Usaquén',supervisor='DANIEL HERNANDO ORTIZ QUINTERO')],mapa,fecha,nombres)[0]
        self.assertEqual(fila['supervisor'],'DANIEL HERNANDO ORTIZ QUINTER')

    def test_nombre_partido_en_linea_y_tildes(self):
        texto=tabla(nombres={11:'CÉSAR\nAUGUSTO SALAMANCA ROJAS'})
        mapa,_,_,nombres=leer(texto+'\n'+tabla(nombres={11:'CESAR AUGUSTO SALAMANCA ROJAS'}))
        self.assertEqual(nombres[mapa['Suba']],['CÉSAR AUGUSTO SALAMANCA ROJAS'])

    def test_nombres_contradictorios_no_elige_al_azar(self):
        mapa,fecha,_,nombres=leer(tabla(nombres={11:'PERSONA UNO'})+'\n'+tabla(nombres={11:'PERSONA DOS'}))
        errores=[]
        fila=enriquecer_con_radicados([solicitud(localidad='Suba',supervisor='PERSONA UNO')],mapa,fecha,nombres,errores)[0]
        self.assertEqual(fila['supervisor'],'')
        self.assertIn('varios nombres',errores[0])

    def test_sin_listado_no_conserva_supervisor_de_solicitud(self):
        errores=[]
        fila=enriquecer_con_radicados([solicitud()],{},None,{},errores)[0]
        self.assertEqual(fila['supervisor'],'')
        self.assertTrue(errores)

    def test_radicado_explicito_manda_sobre_nombre_solicitud(self):
        mapa,fecha,_,nombres=leer(tabla(nombres={11:'NOMBRE DEL RADICADO'}))
        fila=enriquecer_con_radicados([solicitud(localidad='Suba',radicado_salida=mapa['Suba'],supervisor='SUPERVISOR VIEJO')],mapa,fecha,nombres)[0]
        self.assertEqual(fila['supervisor'],'NOMBRE DEL RADICADO')

    def test_word_destinatario_usa_solo_nombre_radicado(self):
        mapa,fecha,_,nombres=leer(tabla(nombres={11:'NOMBRE DEL RADICADO'}))
        fila=enriquecer_con_radicados([solicitud(localidad='Suba',supervisor='SUPERVISOR VIEJO')],mapa,fecha,nombres)[0]
        doc=Document(BytesIO(generar([fila])))
        textos=' '.join(p.text for p in doc.paragraphs)
        self.assertIn('NOMBRE DEL RADICADO',textos)
        self.assertNotIn('SUPERVISOR VIEJO',textos)
