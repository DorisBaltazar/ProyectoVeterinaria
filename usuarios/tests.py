from django.contrib.auth.models import User
from django.test import TestCase, Client

from .models import Perfil, Bitacora
from .bitacora import registrar_bitacora


class PerfilModelTests(TestCase):
    def test_perfil_se_crea_automaticamente_al_crear_usuario(self):
        user = User.objects.create_user("nuevo", password="clave12345")
        self.assertTrue(hasattr(user, "perfil"))
        self.assertIsInstance(user.perfil, Perfil)

    def test_rol_por_defecto_es_recepcionista(self):
        user = User.objects.create_user("nuevo2", password="clave12345")
        self.assertEqual(user.perfil.rol, Perfil.Rol.RECEPCIONISTA)

    def test_propiedades_de_rol(self):
        user = User.objects.create_user("admin_test", password="clave12345")
        user.perfil.rol = Perfil.Rol.ADMINISTRADOR
        user.perfil.save()
        self.assertTrue(user.perfil.es_administrador)
        self.assertFalse(user.perfil.es_veterinario)


class BitacoraTests(TestCase):
    def test_registrar_bitacora_crea_un_registro(self):
        user = User.objects.create_user("admin_bit", password="clave12345")
        registrar_bitacora(user, "Acción de prueba", "detalle de prueba")
        self.assertEqual(Bitacora.objects.count(), 1)

    def test_login_exitoso_queda_registrado_en_bitacora(self):
        admin = User.objects.create_user("admin_login", password="clave12345")
        admin.perfil.rol = Perfil.Rol.ADMINISTRADOR
        admin.perfil.save()
        client = Client()
        client.post("/login/", {"username": "admin_login", "password": "clave12345"})
        self.assertTrue(Bitacora.objects.filter(accion="Inició sesión").exists())


class RolRequeridoMixinTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin_rbac", password="clave12345")
        self.admin.perfil.rol = Perfil.Rol.ADMINISTRADOR
        self.admin.perfil.save()
        self.recep = User.objects.create_user("recep_rbac", password="clave12345")
        self.recep.perfil.rol = Perfil.Rol.RECEPCIONISTA
        self.recep.perfil.save()

    def test_usuario_anonimo_es_redirigido_al_login(self):
        response = self.client.get("/usuarios/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_recepcionista_no_puede_ver_gestion_de_usuarios(self):
        self.client.login(username="recep_rbac", password="clave12345")
        response = self.client.get("/usuarios/")
        self.assertEqual(response.status_code, 403)

    def test_administrador_si_puede_ver_gestion_de_usuarios(self):
        self.client.login(username="admin_rbac", password="clave12345")
        response = self.client.get("/usuarios/")
        self.assertEqual(response.status_code, 200)

    def test_recepcionista_no_puede_ver_bitacora(self):
        self.client.login(username="recep_rbac", password="clave12345")
        response = self.client.get("/bitacora/")
        self.assertEqual(response.status_code, 403)


class UsuarioCreateFormTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin_uc", password="clave12345")
        self.admin.perfil.rol = Perfil.Rol.ADMINISTRADOR
        self.admin.perfil.save()

    def test_crear_usuario_con_rol_veterinario(self):
        self.client.login(username="admin_uc", password="clave12345")
        response = self.client.post("/usuarios/nuevo/", {
            "username": "vet_nuevo", "first_name": "Ana", "last_name": "Paz",
            "email": "ana@ciac.com", "rol": "VET",
            "password1": "Clinica2026*", "password2": "Clinica2026*",
        })
        self.assertEqual(response.status_code, 302)
        creado = User.objects.get(username="vet_nuevo")
        self.assertEqual(creado.perfil.rol, "VET")

    def test_no_se_pueden_repetir_nombres_de_usuario(self):
        User.objects.create_user("duplicado", password="clave12345")
        self.client.login(username="admin_uc", password="clave12345")
        response = self.client.post("/usuarios/nuevo/", {
            "username": "duplicado", "first_name": "X", "last_name": "Y",
            "email": "x@ciac.com", "rol": "RECEP",
            "password1": "Clinica2026*", "password2": "Clinica2026*",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ya existe un usuario")
