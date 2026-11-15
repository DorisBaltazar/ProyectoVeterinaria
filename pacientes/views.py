#from django.shortcuts import render

# Create your views here.
# todo lo que el sistema hace, crear , editar
from django.contrib import messages
from django.db import models
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView

from usuarios.bitacora import registrar_bitacora
from usuarios.mixins import RolRequeridoMixin

from .forms import AlertaMedicaForm, MascotaForm, PesoForm, PropietarioForm
from .grafico_peso import datos_grafico
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mascota = self.object
        pesos = list(mascota.pesos.order_by("fecha", "id"))
        context["peso_actual"] = pesos[-1].peso_kg if pesos else mascota.peso_kg
        context["grafico_peso"] = datos_grafico(pesos)
        variacion = mascota.variacion_peso()
        if variacion:
            context["variacion_peso"], context["variacion_desde"] = variacion
        context["num_pesajes"] = len(pesos)
        return context


class MascotaCreateView(RolRequeridoMixin, CreateView):
    model = Mascota
    form_class = MascotaForm
    roles_permitidos = ROLES_GESTION
    template_name = "pacientes/mascota_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.object.peso_kg is not None:
            self.object.registrar_peso(self.object.peso_kg, usuario=self.request.user)
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
        if self.object.peso_kg is not None and (
            "peso_kg" in form.changed_data or not self.object.pesos.exists()
        ):
            self.object.registrar_peso(self.object.peso_kg, usuario=self.request.user)
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



class _MascotaDeLaUrlMixin:
    """Carga la mascota indicada en la URL para las vistas de peso y alerta."""

    def dispatch(self, request, *args, **kwargs):
        self.mascota = get_object_or_404(Mascota, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mascota"] = self.mascota
        return context


class PesoCreateView(_MascotaDeLaUrlMixin, RolRequeridoMixin, FormView):
    """'Pesar hoy': registra un nuevo pesaje y actualiza la curva de peso."""

    roles_permitidos = ROLES_LECTURA  # cualquier miembro del personal puede pesar
    form_class = PesoForm
    template_name = "pacientes/peso_form.html"

    def get_initial(self):
        from datetime import date
        return {"fecha": date.today()}

    def form_valid(self, form):
        self.mascota.registrar_peso(
            form.cleaned_data["peso_kg"], fecha=form.cleaned_data["fecha"], usuario=self.request.user,
        )
        registrar_bitacora(
            self.request.user, "Registró peso",
            f"{self.mascota.nombre}: {form.cleaned_data['peso_kg']} kg",
        )
        messages.success(self.request, "Peso registrado.")
        return redirect("pacientes:detalle", pk=self.mascota.pk)


class AlertaMedicaUpdateView(_MascotaDeLaUrlMixin, RolRequeridoMixin, FormView):
    """Añadir, editar o quitar la alerta médica de una mascota."""

    roles_permitidos = ROLES_LECTURA
    form_class = AlertaMedicaForm
    template_name = "pacientes/alerta_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.mascota
        return kwargs

    def form_valid(self, form):
        form.save()
        accion = "Actualizó alerta médica" if self.mascota.alerta_medica else "Quitó alerta médica"
        registrar_bitacora(self.request.user, accion, str(self.mascota))
        messages.success(self.request, "Alerta médica guardada." if self.mascota.alerta_medica else "Alerta médica eliminada.")
        return redirect("pacientes:detalle", pk=self.mascota.pk)
