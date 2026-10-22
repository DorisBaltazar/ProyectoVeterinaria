"""Pruebas de INTEGRACIÓN (PI): verifican que varios módulos trabajan juntos
en un flujo completo de punta a punta, usando el cliente HTTP de Django."""
from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from citas.models import Cita
from diagnostico.models import DiagnosticoIA
from historiales.models import HistorialClinico
from inventario.models import Insumo, MovimientoInventario
from pacientes.models import Mascota, Propietario
from usuarios.models import Bitacora, Perfil

CLAVE = "clave12345"


def crear_usuario(nombre, rol):
    u = User.objects.create_user(nombre, password=CLAVE)
    u.perfil.rol = rol
    u.perfil.save()
    return u


class PI01RecepcionACitaYConsultaTests(TestCase):
    """PI-01: Recepción registra propietario, mascota y cita; el veterinario
    asignado la ve en su agenda y registra la consulta en el historial."""

    def setUp(self):
        self.recep = crear_usuario("pi1_recep", Perfil.Rol.RECEPCIONISTA)
        self.vet = crear_usuario("pi1_vet", Perfil.Rol.VETERINARIO)

    def test_flujo_recepcion_cita_consulta(self):
        self.client.login(username="pi1_recep", password=CLAVE)
        r = self.client.post(reverse("pacientes:propietario_crear"), {
            "ci": "7001001", "nombre_completo": "Rosa Mamani", "telefono": "70011223",
            "correo": "", "direccion": "Vinto"})
        self.assertEqual(r.status_code, 302)
        prop = Propietario.objects.get(ci="7001001")

        r = self.client.post(reverse("pacientes:crear"), {
            "propietario": prop.pk, "nombre": "Canela", "especie": "PERRO",
            "raza": "", "sexo": "H", "fecha_nacimiento": "", "peso_kg": "", "notas": ""})
        self.assertEqual(r.status_code, 302)
        mascota = Mascota.objects.get(nombre="Canela")
        self.assertTrue(mascota.codigo)

        r = self.client.post(reverse("citas:crear"), {
            "propietario_nombre": "Rosa Mamani", "propietario_telefono": "70011223",
            "mascota_nombre": "Canela", "especie": "PERRO",
            "fecha": date.today().isoformat(), "hora": "09:30", "motivo": "Control",
            "veterinario": self.vet.pk, "estado": Cita.Estado.PENDIENTE, "observaciones": ""})
        self.assertEqual(r.status_code, 302)
        cita = Cita.objects.get(mascota_nombre="Canela")

        # El veterinario asignado ve la cita en su agenda.
        self.client.logout()
        self.client.login(username="pi1_vet", password=CLAVE)
        r = self.client.get(reverse("citas:lista"))
        self.assertContains(r, "Canela")

        # Registra la consulta en el historial de la mascota.
        r = self.client.post(reverse("historiales:crear", args=[mascota.pk]), {
            "tipo_atencion": "CONSULTA", "fecha_atencion": "2026-08-20T09:30",
            "motivo": "Control", "sintomas": "Ninguno", "diagnostico": "Sano",
            "tratamiento": "", "medicamentos": "", "observaciones": ""})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(HistorialClinico.objects.filter(mascota=mascota).count(), 1)
        self.assertTrue(cita.pk)


class PI02ConsultaInventarioYAlertaTests(TestCase):
    """PI-02: la recepcionista registra una salida de inventario; el stock se
    descuenta y, al llegar al mínimo, aparece la alerta en el panel."""

    def setUp(self):
        self.recep = crear_usuario("pi2_recep", Perfil.Rol.RECEPCIONISTA)
        self.insumo = Insumo.objects.create(nombre="Vacuna Triple", stock_actual=6, stock_minimo=5)
        self.client.login(username="pi2_recep", password=CLAVE)

    def test_salida_descuenta_stock_y_genera_alerta(self):
        r = self.client.get(reverse("usuarios:dashboard"))
        self.assertNotContains(r, "Vacuna Triple")

        r = self.client.post(reverse("inventario:movimiento_crear"), {
            "insumo": self.insumo.pk, "tipo": "SALIDA", "cantidad": "2", "motivo": "Uso en consulta"})
        self.assertEqual(r.status_code, 302)
        self.insumo.refresh_from_db()
        self.assertEqual(self.insumo.stock_actual, 4)
        self.assertEqual(MovimientoInventario.objects.count(), 1)

        r = self.client.get(reverse("usuarios:dashboard"))
        self.assertContains(r, "Vacuna Triple")


class PI03DiagnosticoIAYControlDeAccesoTests(TestCase):
    """PI-03: flujo IA completo (síntomas → predicción → feedback → reporte)
    y bloqueo del módulo para personal no médico."""

    def setUp(self):
        self.vet = crear_usuario("pi3_vet", Perfil.Rol.VETERINARIO)
        self.recep = crear_usuario("pi3_recep", Perfil.Rol.RECEPCIONISTA)
        p = Propietario.objects.create(ci="7003003", nombre_completo="Luis Rojas", telefono="700")
        self.mascota = Mascota.objects.create(propietario=p, nombre="Rex", especie="PERRO")

    def test_flujo_ia_y_reporte(self):
        self.client.login(username="pi3_vet", password=CLAVE)
        r = self.client.post(reverse("diagnostico:crear"), {
            "mascota": self.mascota.pk, "edad_meses": 3, "temperatura_c": "39.8",
            "leucocitos_mil_mm3": "2.8", "hidratacion_pct": "65",
            "fiebre": "on", "vomito": "on", "diarrea": "on", "diarrea_con_sangre": "on",
            "letargo": "on", "perdida_apetito": "on", "deshidratacion": "on"})
        self.assertEqual(r.status_code, 302)
        d = DiagnosticoIA.objects.get()
        self.assertEqual(d.prediccion, "Parvovirus canino")

        r = self.client.get(reverse("diagnostico:detalle", args=[d.pk]))
        self.assertEqual(len(r.context["top3"]), 3)
        probs = [p for _, p in r.context["top3"]]
        self.assertEqual(probs, sorted(probs, reverse=True))

        self.client.post(reverse("diagnostico:feedback", args=[d.pk]), {
            "retroalimentacion": "CONFIRMADO", "diagnostico_real": "", "observaciones_feedback": ""})
        r = self.client.get(reverse("diagnostico:reporte"))
        self.assertEqual(r.context["confirmados"], 1)
        self.assertEqual(r.context["precision_percibida"], 100.0)
        self.assertTrue(Bitacora.objects.filter(accion__icontains="retroalimentación").exists())

    def test_recepcionista_no_accede_al_modulo_ia(self):
        self.client.login(username="pi3_recep", password=CLAVE)
        for nombre in ("diagnostico:lista", "diagnostico:crear"):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 403)

    def test_anonimo_es_redirigido_al_login(self):
        r = self.client.get(reverse("diagnostico:lista"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r["Location"])
