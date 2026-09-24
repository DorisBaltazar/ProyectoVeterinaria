# Create your views here.
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
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


class CitaCreateView(RolRequeridoMixin, CreateView):
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


class CitaUpdateView(RolRequeridoMixin, UpdateView):
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