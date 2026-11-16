"""Pruebas automatizadas de requerimientos no funcionales (RNF) medibles dentro
del propio proyecto: seguridad, integridad, validación y rendimiento básico.
Las pruebas de carga y de seguridad dinámica (k6, OWASP ZAP) están en pruebas_nfr/."""
import io
import time
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from citas.models import Cita
from diagnostico.ml import inferencia
from historiales.models import HistorialClinico
from pacientes.forms import MascotaForm
from pacientes.models import Mascota, Propietario
from usuarios.test_correcciones import BaseCorrecciones, crear_usuario


def _png(bytes_extra=0):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(buf, "PNG")
    return buf.getvalue() + b"0" * bytes_extra


class SeguridadRNFTests(BaseCorrecciones):
    def test_rnf02_contrasenas_cifradas(self):
        u = crear_usuario("seg1", "VET")
        u.set_password("ClaveSegura2026")
        u.save()
        self.assertNotIn("ClaveSegura2026", u.password)
        self.assertTrue(u.password.startswith(("pbkdf2_", "argon2", "bcrypt", "scrypt")))

    def test_rnf02_vistas_internas_exigen_sesion(self):
        for ruta in ("/panel/", "/mascotas/", "/citas/", "/historiales/", "/inventario/", "/reportes/",
                     "/diagnostico/", "/usuarios/", "/bitacora/"):
            r = self.client.get(ruta)
            self.assertEqual(r.status_code, 302, ruta)
            self.assertIn("/login/", r["Location"], ruta)

    def test_rnf02_recepcionista_no_accede_a_ia_ni_usuarios(self):
        self.entrar(self.recep)
        self.assertEqual(self.client.get("/diagnostico/nuevo/").status_code, 403)
        self.assertEqual(self.client.get("/usuarios/").status_code, 403)

    def test_rnf02_cabeceras_de_seguridad_basicas(self):
        r = self.client.get("/login/")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
        self.assertIn(r["X-Frame-Options"], ("DENY", "SAMEORIGIN"))

    def test_rnf02_bitacora_registra_acciones(self):
        from usuarios.models import Bitacora
        self.entrar(self.admin)
        antes = Bitacora.objects.count()
        self.client.get(f"/reportes/pacientes/?formato=csv")
        self.assertGreater(Bitacora.objects.count(), antes)


class ValidacionFotoTests(BaseCorrecciones):
    def _datos(self):
        return {"propietario": self.prop.pk, "nombre": "Foto", "especie": "PERRO", "raza": "x", "sexo": "M",
                "edad_anios": 1, "edad_meses": 0}

    def test_rnf_i1_05_acepta_png_pequeno(self):
        f = MascotaForm(self._datos(), {"foto": SimpleUploadedFile("a.png", _png(), "image/png")})
        self.assertTrue(f.is_valid(), f.errors)

    def test_rnf_i1_05_rechaza_mayor_a_5mb(self):
        f = MascotaForm(self._datos(), {"foto": SimpleUploadedFile("a.png", _png(5 * 1024 * 1024 + 10), "image/png")})
        self.assertFalse(f.is_valid())
        self.assertIn("foto", f.errors)

    def test_rnf_i1_05_rechaza_archivos_que_no_son_imagen(self):
        f = MascotaForm(self._datos(), {"foto": SimpleUploadedFile("a.png", b"esto no es una imagen", "image/png")})
        self.assertFalse(f.is_valid())
        self.assertIn("foto", f.errors)


class IntegridadRNFTests(BaseCorrecciones):
    def test_rnf10_ci_unica_a_nivel_de_base_de_datos(self):
        Propietario.objects.create(ci="777", nombre_completo="A", telefono="70012345")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Propietario.objects.create(ci="777", nombre_completo="B", telefono="70012345")

    def test_rnf10_codigo_de_mascota_unico_y_autogenerado(self):
        a = Mascota.objects.create(propietario=self.prop, nombre="A")
        b = Mascota.objects.create(propietario=self.prop, nombre="B")
        self.assertTrue(a.codigo)
        self.assertNotEqual(a.codigo, b.codigo)

    def test_rnf10_eliminar_mascota_elimina_sus_atenciones(self):
        m = Mascota.objects.create(propietario=self.prop, nombre="A")
        HistorialClinico.objects.create(mascota=m, veterinario=self.vet, creado_por=self.vet,
                                        fecha_atencion=timezone.now(), motivo="x", sintomas="x", diagnostico="x")
        m.delete()
        self.assertEqual(HistorialClinico.objects.count(), 0)

    def test_rnf10_cita_se_conserva_al_borrar_veterinario(self):
        v = crear_usuario("vet_tmp", "VET")
        c = Cita.objects.create(propietario_nombre="A", mascota_nombre="B", fecha=date.today(), hora="10:00",
                                motivo="x", veterinario=v)
        v.delete()
        c.refresh_from_db()
        self.assertIsNone(c.veterinario)


class RendimientoRNFTests(BaseCorrecciones):
    """RNF-03: operaciones habituales en menos de 3 s (medición básica en proceso)."""

    CASO = {"especie": "Perro", "edad_meses": 3, "temperatura_c": 39.8, "leucocitos_mil_mm3": 2.8,
            "hidratacion_pct": 65, **{k: 0 for k in (
                "tos", "estornudos", "secrecion_nasal", "secrecion_ocular", "dificultad_respiratoria",
                "convulsiones", "temblores", "engrosamiento_almohadillas", "picazon", "lesiones_piel")},
            "fiebre": 1, "vomito": 1, "diarrea": 1, "diarrea_con_sangre": 1, "letargo": 1,
            "perdida_apetito": 1, "deshidratacion": 1}

    def test_rnf03_inferencia_menor_a_3_segundos(self):
        inferencia.predecir(self.CASO)  # carga única del modelo
        t = time.perf_counter()
        for _ in range(20):
            res = inferencia.predecir(self.CASO)
        promedio = (time.perf_counter() - t) / 20
        self.assertLess(promedio, 3.0)
        self.assertAlmostEqual(sum(res["probabilidades"].values()), 100, delta=0.5)

    def test_rnf03_modelo_se_carga_una_sola_vez(self):
        a = inferencia._cargar_artefacto()
        b = inferencia._cargar_artefacto()
        self.assertIs(a, b)

    def test_rnf03_modelo_tiene_las_seis_clases(self):
        self.assertEqual(len(inferencia._cargar_artefacto()["label_encoder"].classes_), 6)

    def test_rnf03_busqueda_con_volumen_alto_menor_a_3_segundos(self):
        Mascota.objects.bulk_create([Mascota(propietario=self.prop, nombre=f"Mascota{i}", codigo=f"T{i:05d}")
                                     for i in range(500)])
        self.entrar(self.recep)
        t = time.perf_counter()
        r = self.client.get("/mascotas/?q=Mascota49")
        self.assertEqual(r.status_code, 200)
        self.assertLess(time.perf_counter() - t, 3.0)
        t = time.perf_counter()
        self.assertEqual(self.client.get("/reportes/pacientes/").status_code, 200)
        self.assertLess(time.perf_counter() - t, 3.0)


class ConsultasRNFTests(BaseCorrecciones):
    def test_rnf03_reporte_de_pacientes_no_hace_consultas_por_fila(self):
        """Regresión hallada con k6: el reporte hacía varias consultas por mascota (N+1)."""
        Mascota.objects.bulk_create([Mascota(propietario=self.prop, nombre=f"M{i}", codigo=f"Q{i:04d}")
                                     for i in range(60)])
        self.entrar(self.admin)
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as q:
            self.assertEqual(self.client.get("/reportes/pacientes/").status_code, 200)
        self.assertLess(len(q), 25, f"{len(q)} consultas: probable N+1")
