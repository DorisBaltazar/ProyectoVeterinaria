from django.contrib.auth.models import User
from django.test import TestCase

from usuarios.models import Perfil

from .models import Insumo, MovimientoInventario


class InsumoModelTests(TestCase):
    """RF-10: consultar stock disponible y alertas de nivel mínimo."""

    def test_stock_bajo_true_cuando_actual_es_menor_o_igual_al_minimo(self):
        insumo = Insumo.objects.create(nombre="Vacuna Antirrábica", stock_actual=2, stock_minimo=5)
        self.assertTrue(insumo.stock_bajo)

    def test_stock_bajo_false_cuando_hay_suficiente_stock(self):
        insumo = Insumo.objects.create(nombre="Gasas", stock_actual=100, stock_minimo=10)
        self.assertFalse(insumo.stock_bajo)


class MovimientoInventarioModelTests(TestCase):
    """RF-09: entradas/salidas con descuento automático de stock."""

    def setUp(self):
        self.insumo = Insumo.objects.create(nombre="Amoxicilina", stock_actual=10, stock_minimo=5)
        self.usuario = User.objects.create_user("admin_inv", password="clave12345")

    def test_entrada_incrementa_el_stock(self):
        MovimientoInventario.objects.create(
            insumo=self.insumo, tipo="ENTRADA", cantidad=20, motivo="Compra a proveedor", usuario=self.usuario
        )
        self.insumo.refresh_from_db()
        self.assertEqual(self.insumo.stock_actual, 30)

    def test_salida_descuenta_el_stock_automaticamente(self):
        MovimientoInventario.objects.create(
            insumo=self.insumo, tipo="SALIDA", cantidad=4, motivo="Uso en consulta", usuario=self.usuario
        )
        self.insumo.refresh_from_db()
        self.assertEqual(self.insumo.stock_actual, 6)

    def test_salida_mayor_al_stock_es_rechazada_por_el_formulario(self):
        from .forms import MovimientoInventarioForm
        form = MovimientoInventarioForm(data={
            "insumo": self.insumo.pk, "tipo": "SALIDA", "cantidad": 999, "motivo": "Uso en consulta",
        })
        self.assertFalse(form.is_valid())


class InventarioViewsPorRolTests(TestCase):
    """Solo ADMIN gestiona insumos; ADMIN y VET registran salidas por consumo clínico."""

    def setUp(self):
        self.admin = User.objects.create_user("admin_v", password="clave12345")
        self.admin.perfil.rol = Perfil.Rol.ADMINISTRADOR
        self.admin.perfil.save()

        self.recep = User.objects.create_user("recep_v", password="clave12345")
        self.recep.perfil.rol = Perfil.Rol.RECEPCIONISTA
        self.recep.perfil.save()

        self.insumo = Insumo.objects.create(nombre="Suero", stock_actual=10, stock_minimo=2)

    def test_recepcionista_no_puede_ver_inventario(self):
        self.client.login(username="recep_v", password="clave12345")
        response = self.client.get("/inventario/")
        self.assertEqual(response.status_code, 403)

    def test_administrador_puede_crear_insumo(self):
        self.client.login(username="admin_v", password="clave12345")
        response = self.client.post("/inventario/nuevo/", {
            "nombre": "Jeringas", "categoria": "MATERIAL", "unidad_medida": "unidad", "stock_minimo": 20,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Insumo.objects.filter(nombre="Jeringas").exists())
