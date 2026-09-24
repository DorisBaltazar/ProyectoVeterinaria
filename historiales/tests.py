from datetime import date, datetime, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from citas.models import Cita
from pacientes.models import Mascota, Propietario
from usuarios.models import Perfil

from .models import HistorialClinico, ResultadoLaboratorio


class HistorialClinicoModelTests(TestCase):
    """RF-03/RF-08: registrar consulta clínica y controles posteriores."""

    def setUp(self):
        self.propietario = Propietario.objects.create(ci="5551111", nombre_completo="Ines Vega", telefono="700")
        self.mascota = Mascota.objects.create(propietario=self.propietario, nombre="Toby", especie="PERRO")
        self.vet = User.objects.create_user("vet_hist", password="clave12345")
        self.vet.perfil.rol = Perfil.Rol.VETERINARIO
        self.vet.perfil.save()

    def test_crear_consulta_inicial(self):
        historial = HistorialClinico.objects.create(
            mascota=self.mascota, veterinario=self.vet, tipo_atencion="CONSULTA",
            fecha_atencion=timezone.now(), motivo="Chequeo general",
            sintomas="Decaimiento", diagnostico="Gastritis leve",
        )
        self.assertEqual(historial.mascota, self.mascota)
        self.assertIn("Toby", str(historial))

    def test_control_posterior_se_vincula_a_consulta_original(self):
        consulta = HistorialClinico.objects.create(
            mascota=self.mascota, veterinario=self.vet, tipo_atencion="CONSULTA",
            fecha_atencion=timezone.now(), motivo="Consulta", sintomas="X", diagnostico="Y",
        )
        control = HistorialClinico.objects.create(
            mascota=self.mascota, veterinario=self.vet, tipo_atencion="CONTROL",
            fecha_atencion=timezone.now(), motivo="Control", sintomas="Mejoría",
            diagnostico="Evolución favorable", consulta_relacionada=consulta,
        )
        self.assertEqual(control.consulta_relacionada, consulta)
        self.assertIn(control, consulta.controles.all())

    def test_timeline_ordena_por_fecha_descendente(self):
        HistorialClinico.objects.create(
            mascota=self.mascota, fecha_atencion=datetime(2026, 1, 1, tzinfo=timezone.get_current_timezone()),
            motivo="Antigua", sintomas="a", diagnostico="a",
        )
        HistorialClinico.objects.create(
            mascota=self.mascota, fecha_atencion=datetime(2026, 6, 1, tzinfo=timezone.get_current_timezone()),
            motivo="Reciente", sintomas="b", diagnostico="b",
        )
        historiales = list(self.mascota.historiales.all())
        self.assertEqual(historiales[0].motivo, "Reciente")


class ResultadoLaboratorioTests(TestCase):
    """RF-05: registrar resultados de laboratorio como variables estructuradas."""

    def setUp(self):
        propietario = Propietario.objects.create(ci="5552222", nombre_completo="Marco Diaz", telefono="700")
        mascota = Mascota.objects.create(propietario=propietario, nombre="Kira", especie="GATO")
        self.historial = HistorialClinico.objects.create(
            mascota=mascota, fecha_atencion=timezone.now(), motivo="Control",
            sintomas="Ninguno", diagnostico="Sano",
        )

    def test_resultado_queda_asociado_al_historial(self):
        resultado = ResultadoLaboratorio.objects.create(
            historial=self.historial, nombre_variable="Hematocrito", valor=42.5, unidad="%",
        )
        self.assertEqual(self.historial.resultados_lab.count(), 1)
        self.assertEqual(resultado.valor, 42.5)


class HistorialViewsPorRolTests(TestCase):
    """RF-03: solo personal médico (ADMIN/VET) registra historiales; RECEP solo lee."""

    def setUp(self):
        self.vet = User.objects.create_user("vet_views", password="clave12345")
        self.vet.perfil.rol = Perfil.Rol.VETERINARIO
        self.vet.perfil.save()

        self.recep = User.objects.create_user("recep_views", password="clave12345")
        self.recep.perfil.rol = Perfil.Rol.RECEPCIONISTA
        self.recep.perfil.save()

        self.propietario = Propietario.objects.create(ci="5553333", nombre_completo="Lucia Paz", telefono="700")
        self.mascota = Mascota.objects.create(propietario=self.propietario, nombre="Nube", especie="GATO")

    def test_veterinario_puede_registrar_consulta(self):
        self.client.login(username="vet_views", password="clave12345")
        response = self.client.post(f"/historiales/mascota/{self.mascota.pk}/nueva/", {
            "tipo_atencion": "CONSULTA", "fecha_atencion": "2026-08-20T10:00",
            "motivo": "Vacunación", "sintomas": "Ninguno", "diagnostico": "Sano",
            "tratamiento": "", "medicamentos": "", "observaciones": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(HistorialClinico.objects.count(), 1)

    def test_recepcionista_no_puede_registrar_consulta(self):
        self.client.login(username="recep_views", password="clave12345")
        response = self.client.get(f"/historiales/mascota/{self.mascota.pk}/nueva/")
        self.assertEqual(response.status_code, 403)

    def test_recepcionista_si_puede_ver_la_linea_de_tiempo(self):
        self.client.login(username="recep_views", password="clave12345")
        response = self.client.get(f"/historiales/mascota/{self.mascota.pk}/")
        self.assertEqual(response.status_code, 200)


# Create your tests here.
