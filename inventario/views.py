from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from usuarios.bitacora import registrar_bitacora
from usuarios.mixins import RolRequeridoMixin

from .forms import InsumoForm, MovimientoInventarioForm
from .models import Insumo, MovimientoInventario

ROLES_LECTURA = ["ADMIN", "VET"]
ROLES_GESTION = ["ADMIN"]  # alta/edición de insumos y entradas
ROLES_SALIDA = ["ADMIN", "VET"]  # uso de insumos en consulta


class InsumoListView(RolRequeridoMixin, ListView):
    """RF-10: consultar stock disponible y alertas de nivel mínimo."""

    model = Insumo
    roles_permitidos = ROLES_LECTURA
    template_name = "inventario/insumo_list.html"
    context_object_name = "insumos"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().filter(activo=True)
        q = self.request.GET.get("q")
        solo_bajo_stock = self.request.GET.get("alerta")
        if q:
            queryset = queryset.filter(nombre__icontains=q)
        if solo_bajo_stock:
            queryset = [i for i in queryset if i.stock_bajo]
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        todos = Insumo.objects.filter(activo=True)
        context["total_alertas"] = sum(1 for i in todos if i.stock_bajo)
        return context


class InsumoCreateView(RolRequeridoMixin, CreateView):
    model = Insumo
    form_class = InsumoForm
    roles_permitidos = ROLES_GESTION
    template_name = "inventario/insumo_form.html"
    success_url = reverse_lazy("inventario:lista")

    def form_valid(self, form):
        response = super().form_valid(form)
        registrar_bitacora(self.request.user, "Registró insumo", str(self.object))
        messages.success(self.request, "Insumo registrado. Ahora puedes registrar su stock inicial como una entrada.")
        return response


class InsumoUpdateView(RolRequeridoMixin, UpdateView):
    model = Insumo
    form_class = InsumoForm
    roles_permitidos = ROLES_GESTION
    template_name = "inventario/insumo_form.html"
    success_url = reverse_lazy("inventario:lista")

    def form_valid(self, form):
        response = super().form_valid(form)
        registrar_bitacora(self.request.user, "Editó insumo", str(self.object))
        messages.success(self.request, "Insumo actualizado.")
        return response


class MovimientoListView(RolRequeridoMixin, ListView):
    model = MovimientoInventario
    roles_permitidos = ROLES_LECTURA
    template_name = "inventario/movimiento_list.html"
    context_object_name = "movimientos"
    paginate_by = 25

    def get_queryset(self):
        return super().get_queryset().select_related("insumo", "usuario")


class MovimientoCreateView(RolRequeridoMixin, CreateView):
    """RF-09: registrar entradas/salidas con descuento automático de stock."""

    model = MovimientoInventario
    form_class = MovimientoInventarioForm
    roles_permitidos = ROLES_SALIDA
    template_name = "inventario/movimiento_form.html"
    success_url = reverse_lazy("inventario:movimientos")

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        response = super().form_valid(form)
        registrar_bitacora(
            self.request.user, f"Registró movimiento de inventario ({self.object.get_tipo_display()})",
            str(self.object),
        )
        messages.success(self.request, "Movimiento registrado. El stock se actualizó automáticamente.")
        return response
