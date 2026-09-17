import ast
import hashlib
import os
from pathlib import Path
import pickle
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
ARBOL = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
CONSTANTES = {
    "CLAVE_VERSION_SESION_APP", "CLAVE_AVISO_VERSION_REFRESCADA",
    "CLAVES_LIMPIAR_AL_CAMBIAR_VERSION", "PREFIJOS_LIMPIAR_AL_CAMBIAR_VERSION",
}
FUNCIONES = {
    "_calcular_version_sesion_app", "_invalidar_resultados_versionados",
    "init_session_state", "_cargar_snapshot_consolidacion_cache",
    "_cargar_snapshot_consolidacion", "_informe_para_ui",
    "_inicializar_dependencias_modulo",
    "_recargar_modulos_locales",
}


class Sesion(dict):
    def __getattr__(self, nombre):
        return self[nombre]

    def __setattr__(self, nombre, valor):
        self[nombre] = valor


def contexto_app(sesion=None):
    nodos = []
    for nodo in ARBOL.body:
        if isinstance(nodo, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in CONSTANTES for t in nodo.targets
        ):
            nodos.append(nodo)
        elif isinstance(nodo, ast.FunctionDef) and nodo.name in FUNCIONES:
            nodo.decorator_list = []
            nodos.append(nodo)
    contexto = {
        "st": SimpleNamespace(session_state=sesion if sesion is not None else Sesion(), cache_data=Mock()),
        "Path": Path, "pickle": pickle, "hashlib": hashlib,
        "_APP_DIR": ROOT, "APP_SESSION_VERSION": "build-actual",
        "_CLAVE_SNAPSHOT": "_pc_snapshot_consolidacion_ruta",
    }
    exec(compile(ast.Module(body=nodos, type_ignores=[]), "app.py", "exec"), contexto)
    return contexto


class VersionSesionAppTest(unittest.TestCase):
    def test_version_depende_del_contenido_no_del_tamano_y_fecha(self):
        contexto = contexto_app()
        with TemporaryDirectory() as carpeta:
            contexto["_APP_DIR"] = Path(carpeta)
            archivo = Path(carpeta) / "app.py"
            archivo.write_bytes(b"aaaa")
            stat = archivo.stat()
            anterior = contexto["_calcular_version_sesion_app"]()
            archivo.write_bytes(b"bbbb")
            os.utime(archivo, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            actual = contexto["_calcular_version_sesion_app"]()
            self.assertNotEqual(actual, anterior)
            os.utime(archivo, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1000000000))
            self.assertEqual(contexto["_calcular_version_sesion_app"](), actual)

    def test_dependencias_y_plantillas_tambien_cambian_la_version(self):
        contexto = contexto_app()
        with TemporaryDirectory() as carpeta:
            contexto["_APP_DIR"] = Path(carpeta)
            anterior = contexto["_calcular_version_sesion_app"]()
            (Path(carpeta) / "requirements.txt").write_text("streamlit", encoding="utf-8")
            actual = contexto["_calcular_version_sesion_app"]()
            self.assertNotEqual(actual, anterior)
            (Path(carpeta) / "templates").mkdir()
            (Path(carpeta) / "templates/prueba.docx").write_bytes(b"plantilla")
            self.assertNotEqual(contexto["_calcular_version_sesion_app"](), actual)

    def test_actualizacion_quita_todas_las_referencias_a_salidas_antiguas(self):
        sesion = Sesion(
            _pc_app_session_version="build-anterior", processed=True,
            consolidacion_work={"indice": 2}, zip_descarga_contratos={"path": "viejo.zip"},
            zip_descarga_listo=True, _pc_snapshot_consolidacion_ruta="viejo.pkl",
            _pc_cruce_detalle_ruta="detalle.pkl", _pc_reporte_ejecucion_ruta="reporte.pkl",
            _pc_resumen_consolidado={"n_localidades": 1},
            _pc_at_zip=b"viejo", desempate_contrato_1="opcion vieja",
            _pc_validacion_entrada_errores=["error viejo"],
            cola_localidades=[{"localidad": "La Candelaria"}], acceso_autorizado=True,
            _pc_sid_archivos="sesion", _pc_seccion_activa="Plan de Choque",
        )
        contexto = contexto_app(sesion)
        contexto["init_session_state"]()
        self.assertFalse(sesion["processed"])
        for clave in (
            "consolidacion_work", "zip_descarga_contratos", "zip_descarga_listo",
            "_pc_snapshot_consolidacion_ruta", "_pc_cruce_detalle_ruta",
            "_pc_reporte_ejecucion_ruta", "_pc_resumen_consolidado", "_pc_at_zip",
            "desempate_contrato_1", "_pc_validacion_entrada_errores",
        ):
            self.assertNotIn(clave, sesion)
        self.assertEqual(sesion["cola_localidades"], [{"localidad": "La Candelaria"}])
        self.assertTrue(sesion["acceso_autorizado"])
        self.assertEqual(sesion["_pc_sid_archivos"], "sesion")
        self.assertTrue(sesion["_pc_app_version_refrescada"])
        contexto["st"].cache_data.clear.assert_called_once_with()

    def test_sesion_legacy_sin_version_tambien_se_invalida(self):
        sesion = Sesion(processed=True, _pc_snapshot_consolidacion_ruta="viejo.pkl")
        contexto = contexto_app(sesion)
        contexto["init_session_state"]()
        self.assertFalse(sesion["processed"])
        self.assertNotIn("_pc_snapshot_consolidacion_ruta", sesion)

    def test_recarga_de_la_misma_version_conserva_resultados(self):
        sesion = Sesion(_pc_app_session_version="build-actual", processed=True,
                        zip_descarga_contratos={"path": "actual.zip"})
        contexto = contexto_app(sesion)
        contexto["init_session_state"]()
        self.assertTrue(sesion["processed"])
        self.assertEqual(sesion["zip_descarga_contratos"], {"path": "actual.zip"})
        contexto["st"].cache_data.clear.assert_not_called()

    def test_sesion_nueva_no_limpia_cache_compartida(self):
        contexto = contexto_app()
        contexto["init_session_state"]()
        contexto["st"].cache_data.clear.assert_not_called()
        self.assertFalse(contexto["st"].session_state["processed"])

    def test_snapshot_actual_se_lee_y_el_antiguo_o_sin_version_se_rechaza(self):
        for version in ("build-actual", "build-anterior", None):
            with self.subTest(version=version), TemporaryDirectory() as carpeta:
                ruta = Path(carpeta) / "snapshot.pkl"
                snapshot = {"informe": [{"localidad": "La Candelaria"}]}
                if version:
                    snapshot["app_version"] = version
                with ruta.open("wb") as f:
                    pickle.dump(snapshot, f)
                sesion = Sesion(_pc_app_session_version="build-actual", processed=True,
                                _pc_snapshot_consolidacion_ruta=str(ruta),
                                zip_descarga_contratos={"path": "viejo.zip"})
                contexto = contexto_app(sesion)
                informe = contexto["_informe_para_ui"]()
                if version == "build-actual":
                    self.assertEqual(informe, snapshot["informe"])
                    self.assertTrue(sesion["processed"])
                else:
                    self.assertEqual(informe, [])
                    self.assertFalse(sesion["processed"])
                    self.assertNotIn("zip_descarga_contratos", sesion)
                self.assertTrue(ruta.is_file())

    def test_dependencias_se_inicializan_una_vez_por_version(self):
        contexto = contexto_app()
        funcion = next(n for n in ARBOL.body if isinstance(n, ast.FunctionDef)
                       and n.name == "_dependencias_consolidacion")
        retorno = next(n for n in funcion.body if isinstance(n, ast.Return))
        deps = {clave.value: Mock() for clave in retorno.value.keys}
        contexto["_dependencias_consolidacion"] = cargar = Mock(return_value=deps)
        contexto["_DEPS_MODULO_LISTAS"] = True
        contexto["_DEPS_MODULO_VERSION"] = "build-anterior"
        contexto["_inicializar_dependencias_modulo"]()
        cargar.assert_called_once_with("build-actual")
        contexto["_inicializar_dependencias_modulo"]()
        self.assertEqual(cargar.call_count, 1)
        contexto["APP_SESSION_VERSION"] = "build-siguiente"
        contexto["_inicializar_dependencias_modulo"]()
        cargar.assert_called_with("build-siguiente")
        self.assertEqual(cargar.call_count, 2)

    def test_recarga_imports_en_orden_sin_importar_modulos_no_usados(self):
        contexto = contexto_app()
        nombres = ["constantes", "cxp_cruce", "hoja_suspendidos", "hoja_estrategias", "pdf_ocr", "asistencia_tecnica"]
        modulos = {nombre: ModuleType(nombre) for nombre in nombres}
        contexto["sys"] = SimpleNamespace(modules=modulos)
        with patch("importlib.reload") as recargar, patch("importlib.import_module") as importar:
            self.assertEqual(contexto["_recargar_modulos_locales"]("build-actual"), "build-actual")
            self.assertEqual([c.args[0] for c in recargar.call_args_list], list(modulos.values()))
            importar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
