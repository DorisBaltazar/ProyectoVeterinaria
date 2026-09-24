from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase

from usuarios.models import Perfil
from .models import Cita


class CitaModelTests(TestCase):
    def test_estado_por_defecto_es_pendiente(self):
        cita = Cita.objects.create(
            propietario_nombre="Juan Perez", mascota_nombre="Firulais",
            fecha=date.today(), hora=time(10, 0), motivo="Vacunación",
        )
        self.assertEqual(cita.estado, Cita.Estado.PENDIENTE)

    def test_se_puede_cancelar_una_cita(self):
        cita = Cita.objects.create(
            propietario_nombre="Juan Perez", mascota_nombre="Firulais",
            fecha=date.today(), hora=time(10, 0), motivo="Vacunación",
        )
        cita.estado = Cita.Estado.CANCELADA
        cita.save()
        cita.refresh_from_db()
        self.assertEqual(cita.estado, "CANCELADA")

    def test_str_incluye_mascota(self):
        cita = Cita.objects.create(
            propietario_nombre="Juan Perez", mascota_nombre="Firulais",
            fecha=date.today(), hora=time(10, 0), motivo="Vacunación",
        )
        self.assertIn("Firulais", str(cita))


class CitaFlujoPorRolTests(TestCase):
    def setUp(self):
        self.recep = User.objects.create_user("recep_c", password="clave12345")
        self.recep.perfil.rol = Perfil.Rol.RECEPCIONISTA
        self.recep.perfil.save()
        self.vet = User.objects.create_user("vet_c", password="clave12345")
        self.vet.perfil.rol = Perfil.Rol.VETERINARIO
        self.vet.perfil.save()
        self.admin = User.objects.create_user("admin_c", password="clave12345")
        self.admin.perfil.rol = Perfil.Rol.ADMINISTRADOR
        self.admin.perfil.save()
        self.cita = Cita.objects.create(
            propietario_nombre="Juan Perez", mascota_nombre="Firulais",
            fecha=date.today(), hora=time(10, 0), motivo="Vacunación",
            veterinario=self.vet,
        )

    def test_recepcionista_puede_crear_citas(self):
        self.client.login(username="recep_c", password="clave12345")
        response = self.client.post("/citas/nueva/", {
            "propietario_nombre": "Ana Diaz", "propietario_telefono": "700",
            "mascota_nombre": "Luna", "especie": "GATO",
            "fecha": date.today().isoformat(), "hora": "11:00", "motivo": "Control",
            "veterinario": self.vet.pk, "estado": "PENDIENTE", "observaciones": "",
        })
        self.assertEqual(response.status_code, 302)

    def test_recepcionista_no_puede_eliminar_citas(self):
        self.client.login(username="recep_c", password="clave12345")
        response = self.client.get(f"/citas/{self.cita.pk}/eliminar/")
        self.assertEqual(response.status_code, 403)

    def test_veterinario_solo_ve_sus_citas_asignadas(self):
        Cita.objects.create(
            propietario_nombre="Otro", mascota_nombre="Otra Mascota",
            fecha=date.today(), hora=time(12, 0), motivo="Otro motivo",
        )
        self.client.login(username="vet_c", password="clave12345")
        response = self.client.get("/citas/")
        self.assertContains(response, "Firulais")
        self.assertNotContains(response, "Otra Mascota")

    def test_administrador_puede_eliminar_citas(self):
        self.client.login(username="admin_c", password="clave12345")
        response = self.client.post(f"/citas/{self.cita.pk}/eliminar/")
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Cita.objects.filter(pk=self.cita.pk).exists())


class DashboardRecordatorioTests(TestCase):
    def setUp(self):
        self.recep = User.objects.create_user("recep_dash", password="clave12345")
        self.recep.perfil.rol = Perfil.Rol.RECEPCIONISTA
        self.recep.perfil.save()
        self.client.login(username="recep_dash", password="clave12345")

    def test_dashboard_muestra_citas_de_hoy(self):
        Cita.objects.create(
            propietario_nombre="Juan Perez", mascota_nombre="Firulais",
            fecha=date.today(), hora=time(15, 0), motivo="Control",
        )
        response = self.client.get("/")
        self.assertContains(response, "Firulais")

    def test_dashboard_sin_citas_hoy_muestra_mensaje(self):
        response = self.client.get("/")
        self.assertContains(response, "No tienes citas programadas para hoy")
