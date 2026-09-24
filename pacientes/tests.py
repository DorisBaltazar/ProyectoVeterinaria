from django.contrib.auth.models import User
from django.test import TestCase

from usuarios.models import Perfil
from .forms import PropietarioForm
from .models import Mascota, Propietario


class PropietarioModelTests(TestCase):
    def test_no_permite_dos_propietarios_con_la_misma_ci(self):
        Propietario.objects.create(ci="1234567", nombre_completo="Juan Perez", telefono="700")
        form = PropietarioForm(data={
            "ci": "1234567", "nombre_completo": "Otro Nombre",
            "telefono": "701", "correo": "", "direccion": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("ci", form.errors)

    def test_permite_editar_el_mismo_propietario_sin_marcar_error_de_duplicado(self):
        propietario = Propietario.objects.create(ci="7654321", nombre_completo="Maria Lopez", telefono="700")
        form = PropietarioForm(
            data={"ci": "7654321", "nombre_completo": "Maria Lopez Editada", "telefono": "700", "correo": "", "direccion": ""},
            instance=propietario,
        )
        self.assertTrue(form.is_valid())


class MascotaModelTests(TestCase):
    def setUp(self):
        self.propietario = Propietario.objects.create(ci="1111111", nombre_completo="Carlos Gomez", telefono="700")

    def test_codigo_se_genera_automaticamente_al_guardar(self):
        mascota = Mascota.objects.create(propietario=self.propietario, nombre="Rex", especie="PERRO")
        self.assertTrue(mascota.codigo.startswith("M-"))

    def test_codigos_son_unicos_entre_mascotas(self):
        m1 = Mascota.objects.create(propietario=self.propietario, nombre="Rex", especie="PERRO")
        m2 = Mascota.objects.create(propietario=self.propietario, nombre="Michi", especie="GATO")
        self.assertNotEqual(m1.codigo, m2.codigo)

    def test_edad_aproximada_calculada_desde_fecha_nacimiento(self):
        from datetime import date
        mascota = Mascota.objects.create(
            propietario=self.propietario, nombre="Rex", especie="PERRO",
            fecha_nacimiento=date(date.today().year - 3, 1, 1),
        )
        self.assertEqual(mascota.edad_aproximada, 3)


class MascotaBusquedaViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin_busq", password="clave12345")
        self.admin.perfil.rol = Perfil.Rol.ADMINISTRADOR
        self.admin.perfil.save()
        self.propietario = Propietario.objects.create(ci="9998887", nombre_completo="Elena Rojas", telefono="700")
        self.mascota = Mascota.objects.create(propietario=self.propietario, nombre="Firulais", especie="PERRO")
        self.client.login(username="admin_busq", password="clave12345")

    def test_busqueda_por_nombre(self):
        response = self.client.get("/mascotas/?q=Firulais")
        self.assertContains(response, "Firulais")

    def test_busqueda_por_codigo(self):
        response = self.client.get(f"/mascotas/?q={self.mascota.codigo}")
        self.assertContains(response, "Firulais")

    def test_busqueda_por_ci_del_propietario(self):
        response = self.client.get("/mascotas/?q=9998887")
        self.assertContains(response, "Firulais")

    def test_busqueda_sin_resultados(self):
        response = self.client.get("/mascotas/?q=noexiste123")
        self.assertNotContains(response, "Firulais")