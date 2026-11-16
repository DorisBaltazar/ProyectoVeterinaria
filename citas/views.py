# Create your views here.
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from usuarios.bitacora import registrar_bitacora
from usuarios.mixins import RolRequeridoMixin

from .forms import CitaForm
from .models import Cita

ROLES_LECTURA = ["ADMIN", "VET", "RECEP"]
ROLES_GESTION = ["ADMIN", "RECEP"]  # crear / asignar turnos
ROLES_ACTUALIZACION = ["ADMIN", "RECEP", "VET"]  # p. ej. VET marca "Atendida"
ROLES_ELIMINACION = ["ADMIN"]


class CitaListView(RolRequeridoMixin, ListView):
    model = Cita
    roles_permitidos = ROLES_LECTURA
    template_name = "citas/cita_list.html"
    context_object_name = "citas"
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        estado = self.request.GET.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado)
        # Un veterinario solo ve, por defecto, sus propias citas asignadas
        perfil = getattr(self.request.user, "perfil", None)
        if perfil and perfil.rol == "VET" and self.request.GET.get("todas") != "1":
            queryset = queryset.filter(veterinario=self.request.user)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["estados"] = Cita.Estado.choices
        return context


class CitaDetailView(RolRequeridoMixin, DetailView):
    model = Cita
    roles_permitidos = ROLES_LECTURA
    template_name = "citas/cita_detail.html"
    context_object_name = "cita"


def _propietarios_registrados():
    """Propietarios con sus mascotas, para el selector del formulario de citas."""
    from pacientes.models import Propietario
    return [
        {"id": p.pk, "etiqueta": f"{p.nombre_completo} — CI {p.ci}", "nombre": p.nombre_completo,
         "telefono": p.telefono,
         "mascotas": [{"nombre": m.nombre, "especie": m.especie if m.especie in ("PERRO", "GATO") else "OTRO"}
                      for m in p.mascotas.filter(activo=True)]}
        for p in Propietario.objects.prefetch_related("mascotas").order_by("nombre_completo")
    ]


class PropietariosCitaMixin:
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["propietarios_registrados"] = _propietarios_registrados()
        return ctx


class CitaCreateView(PropietariosCitaMixin, RolRequeridoMixin, CreateView):
    model = Cita
    form_class = CitaForm
    roles_permitidos = ROLES_GESTION
    template_name = "citas/cita_form.html"

    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        response = super().form_valid(form)
        registrar_bitacora(self.request.user, "Registró cita", str(self.object))
        messages.success(self.request, "Cita registrada correctamente.")
        return response


class CitaUpdateView(PropietariosCitaMixin, RolRequeridoMixin, UpdateView):
    model = Cita
    form_class = CitaForm
    roles_permitidos = ROLES_ACTUALIZACION
    template_name = "citas/cita_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        registrar_bitacora(self.request.user, "Actualizó cita", str(self.object))
        messages.success(self.request, "Cita actualizada correctamente.")
        return response


class CitaDeleteView(RolRequeridoMixin, DeleteView):
    model = Cita
    roles_permitidos = ROLES_ELIMINACION
    template_name = "citas/cita_confirm_delete.html"
    success_url = reverse_lazy("citas:lista")

    def form_valid(self, form):
        registrar_bitacora(self.request.user, "Eliminó cita", str(self.object))
        messages.success(self.request, "Cita eliminada.")
        return super().form_valid(form)


class CitaCambiarEstadoView(RolRequeridoMixin, View):
    """Cambio rápido de estado desde el listado o el detalle (sin abrir el formulario)."""

    roles_permitidos = ROLES_ACTUALIZACION
    http_method_names = ["post"]

    def post(self, request, pk):
        cita = get_object_or_404(Cita, pk=pk)
        nuevo = request.POST.get("estado")
        if nuevo not in Cita.Estado.values:
            messages.error(request, "Estado no válido.")
        elif nuevo == Cita.Estado.PENDIENTE and cita.estado != nuevo:
            # Volver a Pendiente implica reprogramar: se abre el formulario para elegir fecha y hora
            messages.info(request, "Elige la nueva fecha y hora para dejar la cita como pendiente.")
            return redirect("citas:editar", pk=cita.pk)
        elif nuevo != cita.estado:
            anterior = cita.get_estado_display()
            cita.estado = nuevo
            cita.save(update_fields=["estado", "fecha_actualizacion"])
            registrar_bitacora(request.user, "Cambió estado de cita", f"{cita} (antes: {anterior})")
            messages.success(request, f"Estado actualizado a {cita.get_estado_display()}.")
        siguiente = request.POST.get("next", "")
        if siguiente.startswith("/") and not siguiente.startswith("//"):
            return redirect(siguiente)
        return redirect("citas:lista")
