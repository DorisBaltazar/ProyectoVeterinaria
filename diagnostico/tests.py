from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from pacientes.models import Mascota, Propietario
from usuarios.models import Bitacora, Perfil

from .ml.inferencia import predecir
from .models import DiagnosticoIA


class InferenciaServicioTests(TestCase):
    """Pruebas unitarias (UT) del servicio de inferencia del modelo."""

    def test_prediccion_parvovirus_perro_cachorro(self):
        datos = {
            "especie": "Perro", "edad_meses": 3, "temperatura_c": 39.8,
            "leucocitos_mil_mm3": 2.8, "hidratacion_pct": 65,
            "fiebre": 1, "vomito": 1, "diarrea": 1, "diarrea_con_sangre": 1,
            "letargo": 1, "perdida_apetito": 1, "deshidratacion": 1, "tos": 0,
            "estornudos": 0, "secrecion_nasal": 0, "secrecion_ocular": 0,
            "dificultad_respiratoria": 0, "convulsiones": 0, "temblores": 0,
            "engrosamiento_almohadillas": 0, "picazon": 0, "lesiones_piel": 0,
        }
        resultado = predecir(datos)
        self.assertEqual(resultado["prediccion"], "Parvovirus canino")
        self.assertGreater(resultado["confianza"], 50)
        self.assertEqual(len(resultado["probabilidades"]), 6)

    def test_prediccion_devuelve_distribucion_ordenada_descendente(self):
        datos = {
            "especie": "Gato", "edad_meses": 24, "temperatura_c": 38.3,
            "leucocitos_mil_mm3": 9.0, "hidratacion_pct": 97,
            "fiebre": 0, "vomito": 0, "diarrea": 0, "diarrea_con_sangre": 0,
            "letargo": 0, "perdida_apetito": 0, "deshidratacion": 0, "tos": 0,
            "estornudos": 0, "secrecion_nasal": 0, "secrecion_ocular": 0,
            "dificultad_respiratoria": 0, "convulsiones": 0, "temblores": 0,
            "engrosamiento_almohadillas": 0, "picazon": 0, "lesiones_piel": 0,
        }
        resultado = predecir(datos)
        valores = list(resultado["probabilidades"].values())
        self.assertEqual(valores, sorted(valores, reverse=True))


class DiagnosticoModeloTests(TestCase):
    def setUp(self):
        self.p = Propietario.objects.create(ci="900", nombre_completo="Zoe", telefono="700")
        self.m = Mascota.objects.create(propietario=self.p, nombre="Firulais", especie="PERRO")
        self.vet = User.objects.create_user("vetdiag", password="x")
        self.vet.perfil.rol = Perfil.Rol.VETERINARIO
        self.vet.perfil.save()

    def test_diagnostico_final_usa_prediccion_si_no_hay_correccion(self):
        d = DiagnosticoIA.objects.create(
            mascota=self.m, veterinario=self.vet, edad_meses=12,
            temperatura_c=38.5, leucocitos_mil_mm3=9.0, hidratacion_pct=90,
            prediccion="Dermatitis alergica", confianza=72.3, probabilidades={"Dermatitis alergica": 72.3},
        )
        self.assertEqual(d.diagnostico_final, "Dermatitis alergica")

    def test_diagnostico_final_usa_correccion_del_veterinario(self):
        d = DiagnosticoIA.objects.create(
            mascota=self.m, veterinario=self.vet, edad_meses=12,
            temperatura_c=38.5, leucocitos_mil_mm3=9.0, hidratacion_pct=90,
            prediccion="Dermatitis alergica", confianza=55.0, probabilidades={"Dermatitis alergica": 55.0},
            retroalimentacion=DiagnosticoIA.Retroalimentacion.CORREGIDO,
            diagnostico_real="Otitis externa",
        )
        self.assertEqual(d.diagnostico_final, "Otitis externa")


class DiagnosticoFlujoPorRolTests(TestCase):
    """Pruebas de aceptación (PA): el módulo de IA solo es accesible para
    el rol Veterinario (sección II.C.1 del documento)."""

    def setUp(self):
        self.p = Propietario.objects.create(ci="901", nombre_completo="Lia", telefono="700")
        self.m = Mascota.objects.create(propietario=self.p, nombre="Toby", especie="PERRO")
        self.recep = User.objects.create_user("recepdiag", password="x")
        self.recep.perfil.rol = Perfil.Rol.RECEPCIONISTA
        self.recep.perfil.save()
        self.vet = User.objects.create_user("vetdiag2", password="x")
        self.vet.perfil.rol = Perfil.Rol.VETERINARIO
        self.vet.perfil.save()

    def test_recepcionista_no_accede_al_formulario_de_diagnostico(self):
        self.client.login(username="recepdiag", password="x")
        resp = self.client.get(reverse("diagnostico:crear"))
        self.assertEqual(resp.status_code, 403)

    def test_recepcionista_no_accede_al_listado(self):
        self.client.login(username="recepdiag", password="x")
        resp = self.client.get(reverse("diagnostico:lista"))
        self.assertEqual(resp.status_code, 403)

    def test_veterinario_accede_al_formulario(self):
        self.client.login(username="vetdiag2", password="x")
        resp = self.client.get(reverse("diagnostico:crear"))
        self.assertEqual(resp.status_code, 200)


class DiagnosticoIntegracionTests(TestCase):
    """Prueba de integración: flujo completo síntomas → inferencia →
    persistencia → retroalimentación → bitácora."""

    def setUp(self):
        self.p = Propietario.objects.create(ci="902", nombre_completo="Nico", telefono="700")
        self.m = Mascota.objects.create(propietario=self.p, nombre="Kira", especie="PERRO")
        self.vet = User.objects.create_user("vetdiag3", password="x")
        self.vet.perfil.rol = Perfil.Rol.VETERINARIO
        self.vet.perfil.save()
        self.client.login(username="vetdiag3", password="x")

    def test_flujo_completo_diagnostico_y_retroalimentacion(self):
        datos_form = {
            "mascota": self.m.pk, "edad_meses": 3, "temperatura_c": "39.8",
            "leucocitos_mil_mm3": "2.8", "hidratacion_pct": "65",
            "fiebre": "on", "vomito": "on", "diarrea": "on", "diarrea_con_sangre": "on",
            "letargo": "on", "perdida_apetito": "on", "deshidratacion": "on",
        }
        resp = self.client.post(reverse("diagnostico:crear"), datos_form)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(DiagnosticoIA.objects.count(), 1)

        diagnostico = DiagnosticoIA.objects.first()
        self.assertEqual(diagnostico.prediccion, "Parvovirus canino")
        self.assertEqual(diagnostico.veterinario, self.vet)
        self.assertTrue(
            Bitacora.objects.filter(usuario=self.vet, accion__icontains="diagnóstico asistido").exists()
        )

        # El veterinario confirma la sugerencia.
        resp2 = self.client.post(reverse("diagnostico:feedback", args=[diagnostico.pk]), {
            "retroalimentacion": DiagnosticoIA.Retroalimentacion.CONFIRMADO,
            "diagnostico_real": "", "observaciones_feedback": "Coincide con la exploración física.",
        })
        self.assertEqual(resp2.status_code, 302)
        diagnostico.refresh_from_db()
        self.assertEqual(diagnostico.retroalimentacion, DiagnosticoIA.Retroalimentacion.CONFIRMADO)
        self.assertIsNotNone(diagnostico.fecha_feedback)

    def test_reporte_calcula_precision_percibida(self):
        DiagnosticoIA.objects.create(
            mascota=self.m, veterinario=self.vet, edad_meses=12,
            temperatura_c=38.5, leucocitos_mil_mm3=9.0, hidratacion_pct=90,
            prediccion="Dermatitis alergica", confianza=72.3, probabilidades={"Dermatitis alergica": 72.3},
            retroalimentacion=DiagnosticoIA.Retroalimentacion.CONFIRMADO,
        )
        DiagnosticoIA.objects.create(
            mascota=self.m, veterinario=self.vet, edad_meses=12,
            temperatura_c=38.5, leucocitos_mil_mm3=9.0, hidratacion_pct=90,
            prediccion="Dermatitis alergica", confianza=55.0, probabilidades={"Dermatitis alergica": 55.0},
            retroalimentacion=DiagnosticoIA.Retroalimentacion.CORREGIDO,
            diagnostico_real="Otitis externa",
        )
        resp = self.client.get(reverse("diagnostico:reporte"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total"], 2)
        self.assertEqual(resp.context["confirmados"], 1)
        self.assertEqual(resp.context["corregidos"], 1)
        self.assertEqual(resp.context["precision_percibida"], 50.0)
