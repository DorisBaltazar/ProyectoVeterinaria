"""Pruebas de las correcciones pedidas tras la prueba de aceptación con el personal
de la clínica (observaciones del 10/11/2026) y de las funciones nuevas:
edad aproximada, curva de peso, alerta médica, citas, laboratorio e inventario."""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from citas.models import Cita
from historiales.models import HistorialClinico, ResultadoLaboratorio
from inventario.models import Insumo, MovimientoInventario
from pacientes.models import Mascota, Propietario, RegistroPeso
from usuarios.models import Perfil


def crear_usuario(nombre, rol, clave="ClaveSegura2026"):
    u = User.objects.create_user(nombre, email=f"{nombre}@ciac.com", password=clave)
    u.perfil.rol = rol
    u.perfil.save()
    return u


class BaseCorrecciones(TestCase):
    def setUp(self):
        self.admin = crear_usuario("admin_c", Perfil.Rol.ADMINISTRADOR)
        self.recep = crear_usuario("recep_c", Perfil.Rol.RECEPCIONISTA)
        self.vet = crear_usuario("vet_c", Perfil.Rol.VETERINARIO)
        self.prop = Propietario.objects.create(ci="5550001", nombre_completo="Ana Rojas", telefono="700")

    def entrar(self, usuario, clave="ClaveSegura2026"):
        self.client.logout()
        self.assertTrue(self.client.login(username=usuario.username, password=clave))

    def datos_mascota(self, **extra):
        datos = {"propietario": self.prop.pk, "nombre": "Firulais", "especie": "PERRO", "sexo": "M"}
        datos.update(extra)
        return datos


class EdadYPesoTests(BaseCorrecciones):
    def test_ut_c01_edad_aproximada_en_anios_y_meses_se_guarda(self):
        self.entrar(self.recep)
        r = self.client.post("/mascotas/nueva/", self.datos_mascota(edad_anios=3, edad_meses=2))
        self.assertEqual(r.status_code, 302)
        m = Mascota.objects.get(nombre="Firulais")
        self.assertTrue(m.fecha_nacimiento_estimada)
        self.assertEqual(m.edad_en_meses, 38)
        self.assertEqual(m.edad_texto, "≈ 3 años y 2 meses")

    def test_ut_c02_fecha_exacta_tiene_prioridad_y_no_es_estimada(self):
        self.entrar(self.recep)
        nacimiento = date.today() - timedelta(days=800)
        self.client.post("/mascotas/nueva/", self.datos_mascota(fecha_nacimiento=nacimiento.isoformat(), edad_anios=9))
        m = Mascota.objects.get(nombre="Firulais")
        self.assertEqual(m.fecha_nacimiento, nacimiento)
        self.assertFalse(m.fecha_nacimiento_estimada)

    def test_ut_c03_al_editar_la_fecha_de_nacimiento_aparece_cargada(self):
        m = Mascota.objects.create(propietario=self.prop, nombre="Rex", fecha_nacimiento=date(2023, 5, 17))
        self.entrar(self.recep)
        r = self.client.get(f"/mascotas/{m.pk}/editar/")
        self.assertContains(r, 'value="2023-05-17"')

    def test_ut_c04_editar_la_edad_actualiza_la_fecha_estimada(self):
        m = Mascota.objects.create(propietario=self.prop, nombre="Rex", fecha_nacimiento=date(2023, 5, 17))
        self.entrar(self.recep)
        datos = self.datos_mascota(nombre="Rex", fecha_nacimiento="2023-05-17", edad_anios=5, edad_meses=0)
        self.client.post(f"/mascotas/{m.pk}/editar/", datos)
        m.refresh_from_db()
        self.assertEqual(m.edad_en_meses, 60)
        self.assertTrue(m.fecha_nacimiento_estimada)

    def test_ut_c05_peso_inicial_crea_la_primera_medicion(self):
        self.entrar(self.recep)
        self.client.post("/mascotas/nueva/", self.datos_mascota(peso_kg="3.80"))
        m = Mascota.objects.get(nombre="Firulais")
        self.assertEqual(m.pesos.count(), 1)
        self.assertEqual(float(m.peso_actual), 3.8)

    def test_ut_c06_pesar_hoy_actualiza_peso_y_variacion(self):
        m = Mascota.objects.create(propietario=self.prop, nombre="Rex", peso_kg="3.20")
        m.registrar_peso("3.20", fecha=date.today() - timedelta(days=23))
        self.entrar(self.vet)
        r = self.client.post(f"/mascotas/{m.pk}/peso/", {"peso_kg": "4.20", "fecha": date.today().isoformat()})
        self.assertEqual(r.status_code, 302)
        m.refresh_from_db()
        self.assertEqual(float(m.peso_kg), 4.2)
        diferencia, _ = m.variacion_peso()
        self.assertEqual(float(diferencia), 1.0)

    def test_ut_c07_con_dos_mediciones_se_dibuja_la_curva(self):
        m = Mascota.objects.create(propietario=self.prop, nombre="Rex")
        m.registrar_peso("3.20", fecha=date.today() - timedelta(days=10))
        m.registrar_peso("3.60", fecha=date.today())
        self.entrar(self.recep)
        r = self.client.get(f"/mascotas/{m.pk}/")
        self.assertContains(r, "<polyline")
        self.assertContains(r, '<polyline points="44.0,')  # coordenadas con punto decimal (no coma)
        self.assertContains(r, "Pesar hoy")
        self.assertContains(r, "+0,40 kg desde el")

    def test_ut_c08_con_una_sola_medicion_se_pide_otra(self):
        m = Mascota.objects.create(propietario=self.prop, nombre="Rex")
        m.registrar_peso("3.80")
        self.entrar(self.recep)
        r = self.client.get(f"/mascotas/{m.pk}/")
        self.assertContains(r, "Con una medición más aparece la curva.")
        self.assertNotContains(r, "<polyline")

    def test_ut_c09_un_solo_pesaje_por_dia(self):
        m = Mascota.objects.create(propietario=self.prop, nombre="Rex")
        m.registrar_peso("3.80")
        m.registrar_peso("3.90")
        self.assertEqual(RegistroPeso.objects.filter(mascota=m).count(), 1)
        self.assertEqual(float(m.peso_actual), 3.9)

    def test_ut_c10_no_se_acepta_peso_en_fecha_futura_ni_negativo(self):
        m = Mascota.objects.create(propietario=self.prop, nombre="Rex")
        self.entrar(self.recep)
        manana = (date.today() + timedelta(days=1)).isoformat()
        r = self.client.post(f"/mascotas/{m.pk}/peso/", {"peso_kg": "4", "fecha": manana})
        self.assertEqual(r.status_code, 200)
        r = self.client.post(f"/mascotas/{m.pk}/peso/", {"peso_kg": "-1", "fecha": date.today().isoformat()})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(m.pesos.count(), 0)

    def test_ut_c11_el_peso_de_la_consulta_alimenta_la_curva(self):
        m = Mascota.objects.create(propietario=self.prop, nombre="Rex")
        self.entrar(self.vet)
        r = self.client.post(f"/historiales/mascota/{m.pk}/nueva/", {
            "tipo_atencion": "CONSULTA", "fecha_atencion": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "motivo": "Control", "sintomas": "Ninguno", "diagnostico": "Sano", "peso_kg": "5.10",
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(float(m.peso_actual), 5.1)


class AlertaMedicaTests(BaseCorrecciones):
    def setUp(self):
        super().setUp()
        self.m = Mascota.objects.create(propietario=self.prop, nombre="Gato McQueen", especie="GATO")

    def test_ut_c12_sin_alerta_se_ofrece_anadirla(self):
        self.entrar(self.recep)
        self.assertContains(self.client.get(f"/mascotas/{self.m.pk}/"), "Añadir alerta médica")

    def test_ut_c13_alerta_guardada_se_muestra_en_el_detalle(self):
        self.entrar(self.vet)
        self.client.post(f"/mascotas/{self.m.pk}/alerta/", {"alerta_medica": "Cuidado al cortar las uñas"})
        r = self.client.get(f"/mascotas/{self.m.pk}/")
        self.assertContains(r, "Alerta médica")
        self.assertContains(r, "Cuidado al cortar las uñas")

    def test_ut_c14_dejarla_vacia_quita_la_alerta(self):
        self.m.alerta_medica = "Alérgico"
        self.m.save()
        self.entrar(self.recep)
        self.client.post(f"/mascotas/{self.m.pk}/alerta/", {"alerta_medica": ""})
        self.m.refresh_from_db()
        self.assertEqual(self.m.alerta_medica, "")

    def test_ut_c15_usuario_sin_sesion_no_puede_editar_alertas(self):
        r = self.client.post(f"/mascotas/{self.m.pk}/alerta/", {"alerta_medica": "x"})
        self.assertEqual(r.status_code, 302)
        self.m.refresh_from_db()
        self.assertEqual(self.m.alerta_medica, "")


class CitasCorreccionesTests(BaseCorrecciones):
    def datos_cita(self, **extra):
        d = {"propietario_nombre": "Ana Rojas", "mascota_nombre": "Rex", "especie": "PERRO",
             "fecha": (date.today() + timedelta(days=3)).isoformat(), "hora": "10:30", "motivo": "Vacuna"}
        d.update(extra)
        return d

    def test_pa_c01_cita_nueva_no_pide_estado_y_nace_pendiente(self):
        self.entrar(self.recep)
        self.assertNotContains(self.client.get("/citas/nueva/"), 'id="id_estado"')
        self.client.post("/citas/nueva/", self.datos_cita(estado="ATENDIDA"))
        self.assertEqual(Cita.objects.get().estado, Cita.Estado.PENDIENTE)

    def test_pa_c02_al_editar_se_ven_fecha_y_hora_guardadas(self):
        c = Cita.objects.create(propietario_nombre="Ana", mascota_nombre="Rex", fecha=date(2026, 12, 5),
                                hora="09:15", motivo="Control", creado_por=self.recep)
        self.entrar(self.recep)
        r = self.client.get(f"/citas/{c.pk}/editar/")
        self.assertContains(r, 'value="2026-12-05"')
        self.assertContains(r, 'value="09:15"')

    def test_pa_c03_fecha_y_hora_quedan_fijas_si_no_esta_pendiente(self):
        c = Cita.objects.create(propietario_nombre="Ana", mascota_nombre="Rex", fecha=date(2026, 12, 5),
                                hora="09:15", motivo="Control", creado_por=self.recep)
        self.entrar(self.recep)
        self.client.post(f"/citas/{c.pk}/editar/", self.datos_cita(estado="ATENDIDA", fecha="2027-01-01", hora="18:00"))
        c.refresh_from_db()
        self.assertEqual(c.estado, "ATENDIDA")
        self.assertEqual(c.fecha, date(2026, 12, 5))
        self.assertEqual(str(c.hora)[:5], "09:15")

    def test_pa_c04_con_estado_pendiente_se_puede_reprogramar(self):
        c = Cita.objects.create(propietario_nombre="Ana", mascota_nombre="Rex", fecha=date(2026, 12, 5),
                                hora="09:15", motivo="Control", creado_por=self.recep)
        self.entrar(self.recep)
        self.client.post(f"/citas/{c.pk}/editar/", self.datos_cita(estado="PENDIENTE", fecha="2027-01-10", hora="16:00"))
        c.refresh_from_db()
        self.assertEqual(c.fecha, date(2027, 1, 10))

    def test_pa_c05_cambio_rapido_de_estado_desde_el_listado(self):
        c = Cita.objects.create(propietario_nombre="Ana", mascota_nombre="Rex", fecha=date(2026, 12, 5),
                                hora="09:15", motivo="Control", creado_por=self.recep)
        self.entrar(self.recep)
        self.assertContains(self.client.get("/citas/"), "Cambiar estado")
        self.client.post(f"/citas/{c.pk}/estado/", {"estado": "CONFIRMADA"})
        c.refresh_from_db()
        self.assertEqual(c.estado, "CONFIRMADA")
        self.assertContains(self.client.get(f"/citas/{c.pk}/"), "Cambiar estado:")

    def test_pa_c06_volver_a_pendiente_lleva_a_reprogramar(self):
        c = Cita.objects.create(propietario_nombre="Ana", mascota_nombre="Rex", fecha=date(2026, 12, 5),
                                hora="09:15", motivo="Control", estado="CANCELADA", creado_por=self.recep)
        self.entrar(self.recep)
        r = self.client.post(f"/citas/{c.pk}/estado/", {"estado": "PENDIENTE"})
        self.assertRedirects(r, f"/citas/{c.pk}/editar/")
        c.refresh_from_db()
        self.assertEqual(c.estado, "CANCELADA")

    def test_pa_c07_estado_invalido_o_metodo_get_no_modifican_la_cita(self):
        c = Cita.objects.create(propietario_nombre="Ana", mascota_nombre="Rex", fecha=date(2026, 12, 5),
                                hora="09:15", motivo="Control", creado_por=self.recep)
        self.entrar(self.recep)
        self.client.post(f"/citas/{c.pk}/estado/", {"estado": "XXX"})
        self.assertEqual(self.client.get(f"/citas/{c.pk}/estado/").status_code, 405)
        c.refresh_from_db()
        self.assertEqual(c.estado, "PENDIENTE")

    def test_pa_c08_cambio_de_estado_no_redirige_a_sitios_externos(self):
        c = Cita.objects.create(propietario_nombre="Ana", mascota_nombre="Rex", fecha=date(2026, 12, 5),
                                hora="09:15", motivo="Control", creado_por=self.recep)
        self.entrar(self.recep)
        r = self.client.post(f"/citas/{c.pk}/estado/", {"estado": "CONFIRMADA", "next": "https://malo.example"})
        self.assertRedirects(r, "/citas/", fetch_redirect_response=False)


class LaboratorioEInventarioTests(BaseCorrecciones):
    def test_pa_c09_resultado_de_laboratorio_guarda_el_tipo_de_examen(self):
        m = Mascota.objects.create(propietario=self.prop, nombre="Rex")
        h = HistorialClinico.objects.create(
            mascota=m, fecha_atencion=timezone.now(), motivo="Control", sintomas="-", diagnostico="-",
            creado_por=self.vet, veterinario=self.vet,
        )
        self.entrar(self.vet)
        form = self.client.get(f"/historiales/{h.pk}/laboratorio/nuevo/")
        self.assertContains(form, "Hemograma (sangre)")
        self.client.post(f"/historiales/{h.pk}/laboratorio/nuevo/", {
            "tipo_examen": "HEMOGRAMA", "nombre_variable": "Leucocitos", "valor": "12.5", "unidad": "x10^3/µL",
        })
        r = ResultadoLaboratorio.objects.get()
        self.assertEqual(r.tipo_examen, "HEMOGRAMA")
        self.assertContains(self.client.get(f"/historiales/{h.pk}/"), "Hemograma (sangre)")

    def test_pa_c10_recepcion_ve_el_boton_y_registra_salidas(self):
        ins = Insumo.objects.create(nombre="Suero", unidad_medida="unidad", stock_actual=10, stock_minimo=2)
        self.entrar(self.recep)
        self.assertContains(self.client.get("/inventario/"), "Registrar movimiento")
        r = self.client.post("/inventario/movimientos/nuevo/",
                             {"insumo": ins.pk, "tipo": "SALIDA", "cantidad": "3", "motivo": "Uso en consulta"})
        self.assertEqual(r.status_code, 302)
        ins.refresh_from_db()
        self.assertEqual(float(ins.stock_actual), 7.0)

    def test_pa_c11_salida_mayor_al_stock_se_rechaza_con_mensaje(self):
        ins = Insumo.objects.create(nombre="Suero", unidad_medida="unidad", stock_actual=2, stock_minimo=1)
        self.entrar(self.recep)
        r = self.client.post("/inventario/movimientos/nuevo/",
                             {"insumo": ins.pk, "tipo": "SALIDA", "cantidad": "5", "motivo": "Uso"})
        self.assertContains(r, "Stock insuficiente")
        self.assertEqual(MovimientoInventario.objects.count(), 0)

    def test_pa_c12_recepcion_no_puede_registrar_entradas(self):
        ins = Insumo.objects.create(nombre="Suero", unidad_medida="unidad", stock_actual=2, stock_minimo=1)
        self.entrar(self.recep)
        r = self.client.post("/inventario/movimientos/nuevo/",
                             {"insumo": ins.pk, "tipo": "ENTRADA", "cantidad": "5", "motivo": "Compra"})
        self.assertEqual(r.status_code, 200)
        ins.refresh_from_db()
        self.assertEqual(float(ins.stock_actual), 2.0)


class UsuariosCorreccionesTests(BaseCorrecciones):
    def crear_desde_el_sistema(self, **extra):
        self.entrar(self.admin)
        datos = {"username": "NuevaPersona", "first_name": "Nueva", "last_name": "Persona",
                 "email": "nueva@ciac.com", "rol": "RECEP", "password1": "ClaveNueva2026", "password2": "ClaveNueva2026"}
        datos.update(extra)
        return self.client.post("/usuarios/nuevo/", datos)

    def test_pa_c13_usuario_creado_por_el_administrador_puede_iniciar_sesion(self):
        self.assertEqual(self.crear_desde_el_sistema().status_code, 302)
        self.client.logout()
        r = self.client.post("/login/", {"username": "NuevaPersona", "password": "ClaveNueva2026"})
        self.assertRedirects(r, "/panel/", fetch_redirect_response=False)

    def test_pa_c14_el_acceso_no_distingue_mayusculas_en_el_usuario(self):
        self.crear_desde_el_sistema()
        self.client.logout()
        r = self.client.post("/login/", {"username": "nuevapersona", "password": "ClaveNueva2026"})
        self.assertRedirects(r, "/panel/", fetch_redirect_response=False)

    def test_pa_c15_tambien_se_puede_entrar_con_el_correo(self):
        self.crear_desde_el_sistema()
        self.client.logout()
        r = self.client.post("/login/", {"username": "nueva@ciac.com", "password": "ClaveNueva2026"})
        self.assertRedirects(r, "/panel/", fetch_redirect_response=False)

    def test_pa_c16_clave_incorrecta_sigue_sin_dejar_entrar(self):
        self.crear_desde_el_sistema()
        self.client.logout()
        r = self.client.post("/login/", {"username": "NuevaPersona", "password": "otra"})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_pa_c17_clave_debil_se_rechaza_y_se_explica(self):
        r = self.crear_desde_el_sistema(password1="12345678", password2="12345678")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="NuevaPersona").exists())
        self.assertContains(r, "text-error")

    def test_pa_c18_no_se_permiten_usuarios_repetidos_con_distinta_capitalizacion(self):
        r = self.crear_desde_el_sistema(username="ADMIN_C")
        self.assertEqual(r.status_code, 200)


class CamposObligatoriosTests(BaseCorrecciones):
    def test_pa_c19_los_formularios_marcan_los_campos_obligatorios_con_asterisco(self):
        self.entrar(self.recep)
        r = self.client.get("/mascotas/nueva/")
        self.assertContains(r, "marca-obligatorio")
        self.assertContains(r, 'name="nombre"')
        self.assertContains(r, "required")
