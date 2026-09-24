#from django.shortcuts import render

# Create your views here.
# todo lo que el sistema hace, crear , editar
from django.contrib import messages
from django.db import models
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from usuarios.bitacora import registrar_bitacora
from usuarios.mixins import RolRequeridoMixin

from .forms import MascotaForm, PropietarioForm
from .models import Mascota, Propietario

ROLES_LECTURA = ["ADMIN", "VET", "RECEP"]
ROLES_GESTION = ["ADMIN", "RECEP"]
ROLES_ELIMINACION = ["ADMIN"]


class PropietarioListView(RolRequeridoMixin, ListView):
    """RF-02: buscar propietarios por nombre o CI."""

    model = Propietario
    roles_permitidos = ROLES_LECTURA
    template_name = "pacientes/propietario_list.html"
    context_object_name = "propietarios"
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(
                models.Q(nombre_completo__icontains=q) | models.Q(ci__icontains=q)
            )
        return queryset


class PropietarioCreateView(RolRequeridoMixin, CreateView):
    model = Propietario
    form_class = PropietarioForm
    roles_permitidos = ROLES_GESTION
    template_name = "pacientes/propietario_form.html"
    success_url = reverse_lazy("pacientes:crear")

    def form_valid(self, form):
        response = super().form_valid(form)
        registrar_bitacora(self.request.user, "Registró propietario", str(self.object))
        messages.success(self.request, "Propietario registrado. Ahora registra su mascota.")
        return response


class PropietarioUpdateView(RolRequeridoMixin, UpdateView):
    """RF-02: editar propietarios existentes."""

    model = Propietario
    form_class = PropietarioForm
    roles_permitidos = ROLES_GESTION
    template_name = "pacientes/propietario_form.html"
    success_url = reverse_lazy("pacientes:propietarios")

    def form_valid(self, form):
        response = super().form_valid(form)
        registrar_bitacora(self.request.user, "Editó propietario", str(self.object))
        messages.success(self.request, "Datos del propietario actualizados.")
        return response


class MascotaListView(RolRequeridoMixin, ListView):
    model = Mascota
    roles_permitidos = ROLES_LECTURA
    template_name = "pacientes/mascota_list.html"
    context_object_name = "mascotas"
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset().select_related("propietario").filter(activo=True)
        q = self.request.GET.get("q")
        especie = self.request.GET.get("especie")
        if q:
            queryset = queryset.filter(
                models.Q(nombre__icontains=q)
                | models.Q(codigo__icontains=q)
                | models.Q(propietario__nombre_completo__icontains=q)
                | models.Q(propietario__ci__icontains=q)
            )
        if especie:
            queryset = queryset.filter(especie=especie)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["especies"] = Mascota.Especie.choices
        return context


class MascotaDetailView(RolRequeridoMixin, DetailView):
    model = Mascota
    roles_permitidos = ROLES_LECTURA
    template_name = "pacientes/mascota_detail.html"
    context_object_name = "mascota"


class MascotaCreateView(RolRequeridoMixin, CreateView):
    model = Mascota
    form_class = MascotaForm
    roles_permitidos = ROLES_GESTION
    template_name = "pacientes/mascota_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        registrar_bitacora(self.request.user, "Registró mascota", str(self.object))
        messages.success(self.request, "Mascota registrada correctamente.")
        return response


class MascotaUpdateView(RolRequeridoMixin, UpdateView):
    model = Mascota
    form_class = MascotaForm
    roles_permitidos = ROLES_GESTION
    template_name = "pacientes/mascota_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        registrar_bitacora(self.request.user, "Editó mascota", str(self.object))
        messages.success(self.request, "Datos de la mascota actualizados.")
        return response


class MascotaDeleteView(RolRequeridoMixin, DeleteView):
    model = Mascota
    roles_permitidos = ROLES_ELIMINACION
    template_name = "pacientes/mascota_confirm_delete.html"
    success_url = reverse_lazy("pacientes:lista")

    def form_valid(self, form):
        registrar_bitacora(self.request.user, "Eliminó mascota", str(self.object))
        messages.success(self.request, "Mascota eliminada.")
        return super().form_valid(form)
