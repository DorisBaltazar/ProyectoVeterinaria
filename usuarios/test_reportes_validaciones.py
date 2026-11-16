"""Pruebas de los reportes exportables (RP-xx) y del rechazo de valores
negativos / fuera de rango (VAL-xx)."""
from datetime import date, timedelta

from django.contrib.auth.models import User
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from citas.models import Cita
from diagnostico.models import DiagnosticoIA
from historiales.models import HistorialClinico
from inventario.models import Insumo, MovimientoInventario
from pacientes.models import Mascota, Propietario
from usuarios.models import Bitacora, Perfil
from usuarios.test_correcciones import BaseCorrecciones, crear_usuario


class ReportesTests(BaseCorrecciones):
    def setUp(self):
        super().setUp()
        self.m = Mascota.objects.create(propietario=self.prop, nombre="Rex", peso_kg=Decimal("12.5"),
                                        alerta_medica="Alérgico a penicilina")
        HistorialClinico.objects.create(
            mascota=self.m, veterinario=self.vet, creado_por=self.vet, fecha_atencion=timezone.now(),
            motivo="Control", sintomas="Ninguno", diagnostico="Sano")
        Cita.objects.create(propietario_nombre="Ana", mascota_nombre="Rex", fecha=date.today(),
                            hora="10:00", motivo="Vacuna")
        self.ins = Insumo.objects.create(nombre="Amoxicilina", stock_actual=2, stock_minimo=5,
                                         precio_unitario=Decimal("10"))

    def test_rp01_indice_segun_rol(self):
        self.entrar(self.recep)
        r = self.client.get("/reportes/")
        self.assertContains(r, "Listado de pacientes")
        self.assertContains(r, "Estado del inventario")
        self.assertNotContains(r, "Atenciones clínicas")
        self.entrar(self.vet)
        r = self.client.get("/reportes/")
        self.assertContains(r, "Atenciones clínicas")
        self.assertNotContains(r, "Estado del inventario")

    def test_rp02_acceso_denegado_por_rol(self):
        self.entrar(self.recep)
        self.assertEqual(self.client.get("/reportes/atenciones/").status_code, 403)
        self.entrar(self.vet)
        self.assertEqual(self.client.get("/reportes/inventario/").status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get("/reportes/pacientes/").status_code, 302)

    def test_rp03_csv_pacientes(self):
        self.entrar(self.admin)
        r = self.client.get("/reportes/pacientes/?formato=csv")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r["Content-Type"])
        texto = r.content.decode("utf-8-sig")
        self.assertIn("Rex", texto)
        self.assertIn("Alérgico a penicilina", texto)
        self.assertIn("Propietario", texto)
        self.assertTrue(Bitacora.objects.filter(accion="Exportó reporte").exists())

    def test_rp04_inventario_marca_stock_bajo_y_valor(self):
        self.entrar(self.admin)
        r = self.client.get("/reportes/inventario/")
        self.assertContains(r, "Stock bajo")
        self.assertContains(r, "20.00")

    def test_rp05_filtro_de_fechas_invalido(self):
        self.entrar(self.admin)
        r = self.client.get("/reportes/citas/?desde=2026-12-01&hasta=2026-01-01")
        self.assertContains(r, "no puede ser anterior")

    def test_rp06_filtro_de_citas_por_estado_y_fecha(self):
        self.entrar(self.admin)
        hoy = date.today().isoformat()
        r = self.client.get(f"/reportes/citas/?desde={hoy}&hasta={hoy}&estado=PENDIENTE&formato=csv")
        self.assertIn("Vacuna", r.content.decode("utf-8-sig"))
        r = self.client.get(f"/reportes/citas/?desde={hoy}&hasta={hoy}&estado=CANCELADA&formato=csv")
        self.assertNotIn("Vacuna", r.content.decode("utf-8-sig"))

    def test_rp07_version_imprimible(self):
        self.entrar(self.admin)
        r = self.client.get("/reportes/atenciones/?formato=imprimir")
        self.assertContains(r, "Imprimir / Guardar como PDF")
        self.assertContains(r, "Control")

    def test_rp08_ficha_del_paciente_html_y_csv(self):
        self.entrar(self.recep)
        r = self.client.get(f"/reportes/ficha/{self.m.pk}/")
        self.assertContains(r, "ALERTA MÉDICA")
        self.assertContains(r, "Alérgico a penicilina")
        r = self.client.get(f"/reportes/ficha/{self.m.pk}/?formato=csv")
        self.assertIn("Rex", r.content.decode("utf-8-sig"))

    def test_rp09_movimientos_e_ia_y_resumen_ia_se_conservan(self):
        self.entrar(self.admin)
        for clave in ("movimientos", "ia", "citas", "pacientes", "inventario", "atenciones"):
            self.assertEqual(self.client.get(f"/reportes/{clave}/").status_code, 200, clave)
            self.assertEqual(self.client.get(f"/reportes/{clave}/?formato=csv").status_code, 200, clave)
        self.assertEqual(self.client.get("/diagnostico/reporte/").status_code, 200)
        self.assertEqual(self.client.get("/reportes/noexiste/").status_code, 404)


class ValidacionesTests(BaseCorrecciones):
    def setUp(self):
        super().setUp()
        self.m = Mascota.objects.create(propietario=self.prop, nombre="Rex")

    def test_val01_mascota_rechaza_peso_negativo_cero_y_excesivo(self):
        self.entrar(self.recep)
        for peso in ("-5", "0", "-0.01", "500"):
            r = self.client.post("/mascotas/nueva/", self.datos_mascota(peso_kg=peso))
            self.assertEqual(r.status_code, 200, peso)
        self.assertEqual(Mascota.objects.filter(nombre="Firulais").count(), 0)

    def test_val02_edad_negativa_y_nacimiento_futuro(self):
        self.entrar(self.recep)
        r = self.client.post("/mascotas/nueva/", self.datos_mascota(edad_anios=-3, edad_meses=0))
        self.assertEqual(r.status_code, 200)
        futuro = (date.today() + timedelta(days=10)).isoformat()
        r = self.client.post("/mascotas/nueva/", self.datos_mascota(fecha_nacimiento=futuro))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Mascota.objects.filter(nombre="Firulais").count(), 0)

    def test_val03_peso_negativo_en_pesaje(self):
        self.entrar(self.recep)
        r = self.client.post(f"/mascotas/{self.m.pk}/peso/", {"peso_kg": "-3", "fecha": date.today().isoformat()})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.m.pesos.count(), 0)

    def test_val04_historial_rechaza_peso_y_temperatura_invalidos(self):
        self.entrar(self.vet)
        base = {"tipo_atencion": "CONSULTA", "fecha_atencion": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
                "motivo": "x", "sintomas": "x", "diagnostico": "x"}
        for extra in ({"peso_kg": "-2"}, {"temperatura_c": "-10"}, {"temperatura_c": "80"}):
            r = self.client.post(f"/historiales/mascota/{self.m.pk}/nueva/", {**base, **extra})
            self.assertEqual(r.status_code, 200, extra)
        self.assertEqual(HistorialClinico.objects.count(), 0)

    def test_val05_historial_rechaza_fechas_incoherentes(self):
        self.entrar(self.vet)
        futura = (timezone.localtime() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
        base = {"tipo_atencion": "CONSULTA", "motivo": "x", "sintomas": "x", "diagnostico": "x"}
        r = self.client.post(f"/historiales/mascota/{self.m.pk}/nueva/", {**base, "fecha_atencion": futura})
        self.assertEqual(r.status_code, 200)
        ahora = timezone.localtime().strftime("%Y-%m-%dT%H:%M")
        ayer = (date.today() - timedelta(days=2)).isoformat()
        r = self.client.post(f"/historiales/mascota/{self.m.pk}/nueva/",
                             {**base, "fecha_atencion": ahora, "fecha_proximo_control": ayer})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(HistorialClinico.objects.count(), 0)

    def test_val06_inventario_rechaza_negativos(self):
        self.entrar(self.admin)
        base = {"nombre": "Gasas", "categoria": "MATERIAL", "unidad_medida": "caja", "activo": "on"}
        for extra in ({"stock_minimo": "-1"}, {"precio_unitario": "-5"}):
            r = self.client.post("/inventario/nuevo/", {**base, "stock_minimo": "1", **extra})
            self.assertEqual(r.status_code, 200, extra)
        self.assertEqual(Insumo.objects.filter(nombre="Gasas").count(), 0)

    def test_val07_movimiento_cantidad_negativa_o_cero(self):
        ins = Insumo.objects.create(nombre="Jeringas", stock_actual=10, stock_minimo=1)
        self.entrar(self.admin)
        for cant in ("-5", "0"):
            r = self.client.post("/inventario/movimientos/nuevo/",
                                 {"insumo": ins.pk, "tipo": "ENTRADA", "cantidad": cant, "motivo": "Compra"})
            self.assertEqual(r.status_code, 200, cant)
        ins.refresh_from_db()
        self.assertEqual(ins.stock_actual, 10)

    def test_val08_modelo_valida_aunque_no_pase_por_formulario(self):
        from django.core.exceptions import ValidationError
        for obj in (
            Insumo(nombre="X", stock_actual=-1, stock_minimo=0),
            Mascota(propietario=self.prop, nombre="Y", peso_kg=Decimal("-1")),
        ):
            with self.assertRaises(ValidationError):
                obj.full_clean()

    def test_val09_telefono_invalido(self):
        self.entrar(self.recep)
        r = self.client.post("/mascotas/propietarios/nuevo/", {"ci": "999", "nombre_completo": "Pepe",
                                                              "telefono": "abc", "correo": "", "direccion": ""})
        self.assertNotEqual(r.status_code, 302)
        self.assertEqual(Propietario.objects.filter(ci="999").count(), 0)

    def test_val10_cita_en_el_pasado(self):
        self.entrar(self.recep)
        ayer = (date.today() - timedelta(days=3)).isoformat()
        r = self.client.post("/citas/nueva/", {
            "propietario_nombre": "Ana", "propietario_telefono": "70012345", "mascota_nombre": "Rex",
            "especie": "PERRO", "fecha": ayer, "hora": "10:00", "motivo": "Control"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Cita.objects.count(), 0)

    def test_val11_diagnostico_ia_rechaza_valores_imposibles(self):
        from diagnostico.forms import DiagnosticoForm
        datos = {"mascota": self.m.pk, "edad_meses": 12, "temperatura_c": "38.5",
                 "leucocitos_mil_mm3": "10", "hidratacion_pct": "95"}
        self.assertTrue(DiagnosticoForm(datos).is_valid())
        for campo, valor in (("edad_meses", "-4"), ("temperatura_c", "-38"), ("leucocitos_mil_mm3", "-1"),
                             ("hidratacion_pct", "-5"), ("hidratacion_pct", "150"), ("temperatura_c", "90")):
            f = DiagnosticoForm({**datos, campo: valor})
            self.assertFalse(f.is_valid(), (campo, valor))
            self.assertIn(campo, f.errors)

    def test_val12_html_incluye_min_y_max(self):
        self.entrar(self.recep)
        r = self.client.get("/mascotas/nueva/")
        self.assertContains(r, 'min="0.01"')
        self.assertContains(r, 'max="200"')


class CambiosFinalesTests(BaseCorrecciones):
    def test_fx01_laboratorio_rechaza_valor_negativo(self):
        m = Mascota.objects.create(propietario=self.prop, nombre="Rex")
        h = HistorialClinico.objects.create(mascota=m, veterinario=self.vet, creado_por=self.vet,
                                            fecha_atencion=timezone.now(), motivo="x", sintomas="x", diagnostico="x")
        self.entrar(self.admin)
        r = self.client.get(f"/historiales/{h.pk}/laboratorio/nuevo/")
        self.assertContains(r, 'min="0"')
        r = self.client.post(f"/historiales/{h.pk}/laboratorio/nuevo/", {
            "tipo_examen": "ORINA", "nombre_variable": "Densidad urinaria", "valor": "-0.002", "unidad": "mg/dL"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(h.resultados_lab.count(), 0)

    def test_fx02_cita_lista_propietarios_registrados(self):
        Mascota.objects.create(propietario=self.prop, nombre="Rex")
        self.entrar(self.recep)
        r = self.client.get("/citas/nueva/")
        self.assertContains(r, "Buscar propietario registrado")
        self.assertContains(r, "Ana Rojas")
        self.assertContains(r, "Rex")

    def test_fx03_admin_elimina_usuario_y_conserva_historial(self):
        victima = crear_usuario("vet_borrar", Perfil.Rol.VETERINARIO)
        c = Cita.objects.create(propietario_nombre="A", mascota_nombre="B", fecha=date.today(), hora="10:00",
                                motivo="m", creado_por=victima)
        self.entrar(self.admin)
        self.assertEqual(self.client.get(f"/usuarios/{victima.pk}/eliminar/").status_code, 200)
        r = self.client.post(f"/usuarios/{victima.pk}/eliminar/")
        self.assertEqual(r.status_code, 302)
        self.assertFalse(User.objects.filter(pk=victima.pk).exists())
        c.refresh_from_db()
        self.assertIsNone(c.creado_por)
        self.assertTrue(Bitacora.objects.filter(accion="Eliminó usuario").exists())

    def test_fx04_no_se_puede_eliminar_a_si_mismo_ni_sin_ser_admin(self):
        self.entrar(self.admin)
        self.client.post(f"/usuarios/{self.admin.pk}/eliminar/")
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())
        otro = crear_usuario("otro", Perfil.Rol.VETERINARIO)
        self.entrar(self.recep)
        self.assertEqual(self.client.post(f"/usuarios/{otro.pk}/eliminar/").status_code, 403)
        self.assertTrue(User.objects.filter(pk=otro.pk).exists())


class SesionTests(BaseCorrecciones):
    def test_ses01_cerrar_sesion_va_a_la_pagina_principal_y_bloquea_el_panel(self):
        self.entrar(self.admin)
        r = self.client.post("/logout/")
        self.assertRedirects(r, "/login/", fetch_redirect_response=False)
        r = self.client.get("/panel/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])

    def test_ses03_login_envia_atras_a_la_pagina_principal(self):
        r = self.client.get("/login/")
        self.assertContains(r, "popstate")

    def test_ses02_paginas_con_sesion_no_se_guardan_en_cache(self):
        self.entrar(self.admin)
        r = self.client.get("/panel/")
        self.assertIn("no-store", r["Cache-Control"])
        self.assertIn("no-cache", r["Cache-Control"])


class CorreoYCsrfTests(BaseCorrecciones):
    def test_em01_usuario_no_admite_correo_duplicado(self):
        self.entrar(self.admin)
        r = self.client.post("/usuarios/nuevo/", {
            "username": "nuevo1", "first_name": "N", "last_name": "U", "email": "VET_C@ciac.com",
            "password1": "ClaveSegura2026", "password2": "ClaveSegura2026", "rol": "VET"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Ya existe un usuario con ese correo")
        self.assertFalse(User.objects.filter(username="nuevo1").exists())

    def test_em02_editar_usuario_con_su_propio_correo_funciona(self):
        self.entrar(self.admin)
        r = self.client.post(f"/usuarios/{self.vet.pk}/editar/", {
            "first_name": "V", "last_name": "C", "email": self.vet.email, "is_active": "on", "rol": "VET"})
        self.assertEqual(r.status_code, 302)

    def test_em03_propietario_correo_duplicado(self):
        Propietario.objects.create(ci="111", nombre_completo="Uno", telefono="70012345", correo="a@x.com")
        self.entrar(self.recep)
        r = self.client.post("/mascotas/propietario/nuevo/", {
            "ci": "222", "nombre_completo": "Dos", "telefono": "70012345", "correo": "A@X.com", "direccion": ""})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Ya hay un propietario registrado con ese correo")

    def test_em04_formularios_muestran_etiquetas(self):
        self.entrar(self.admin)
        r = self.client.get(f"/mascotas/propietario/{self.prop.pk}/editar/")
        for t in ("Cédula de identidad", "Nombre completo", "Teléfono", "Correo electrónico", "Dirección"):
            self.assertContains(r, t)
        i = Insumo.objects.create(nombre="X", stock_actual=1, stock_minimo=1)
        r = self.client.get(f"/inventario/{i.pk}/editar/")
        self.assertContains(r, "Nombre del insumo")
        self.assertContains(r, "Unidad de medida")

    def test_cs01_fallo_csrf_redirige_en_vez_de_mostrar_403(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        r = c.post("/login/", {"username": "x", "password": "y"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])


class EstadisticasReportesTests(BaseCorrecciones):
    def test_es01_reportes_incluyen_graficos_y_kpis(self):
        m = Mascota.objects.create(propietario=self.prop, nombre="Rex", especie="PERRO", raza="Mestizo")
        HistorialClinico.objects.create(mascota=m, veterinario=self.vet, creado_por=self.vet,
                                        fecha_atencion=timezone.now(), motivo="x", sintomas="x", diagnostico="Sano")
        Cita.objects.create(propietario_nombre="A", mascota_nombre="Rex", fecha=date.today(), hora="10:00", motivo="Vacuna")
        Insumo.objects.create(nombre="Gasas", categoria="MATERIAL", stock_actual=1, stock_minimo=5, precio_unitario=3)
        self.entrar(self.admin)
        for clave, titulo in (("pacientes", "Pacientes por especie"), ("citas", "Citas por estado"),
                              ("atenciones", "Atenciones por veterinario"), ("inventario", "Estado del stock")):
            r = self.client.get(f"/reportes/{clave}/")
            self.assertContains(r, "rp-card", msg_prefix=clave)
            self.assertContains(r, titulo)
            r = self.client.get(f"/reportes/{clave}/?formato=imprimir")
            self.assertContains(r, titulo)
            self.assertContains(r, "Estadísticas")

    def test_es02_reporte_sin_datos_no_falla(self):
        self.entrar(self.admin)
        for clave in ("pacientes", "citas", "atenciones", "inventario", "movimientos", "ia"):
            self.assertEqual(self.client.get(f"/reportes/{clave}/").status_code, 200, clave)
            self.assertEqual(self.client.get(f"/reportes/{clave}/?formato=imprimir").status_code, 200, clave)

    def test_es03_resumen_ia_tiene_graficos_y_exportar(self):
        self.entrar(self.admin)
        r = self.client.get("/diagnostico/reporte/")
        self.assertContains(r, "Exportar a Excel")
