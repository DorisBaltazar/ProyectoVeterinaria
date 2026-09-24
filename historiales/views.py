from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from usuarios.bitacora import registrar_bitacora
from usuarios.mixins import RolRequeridoMixin
from pacientes.models import Mascota

from .forms import HistorialClinicoForm, ResultadoLaboratorioForm
from .models import HistorialClinico, ResultadoLaboratorio

ROLES_LECTURA = ["ADMIN", "VET", "RECEP"]
ROLES_CLINICOS = ["ADMIN", "VET"]  # solo personal médico registra/edita historiales
ROLES_ELIMINACION = ["ADMIN"]


class MascotaTimelineView(RolRequeridoMixin, DetailView):
    """RF-04: consultar el historial clínico completo de una mascota (línea de tiempo)."""

    model = Mascota
    roles_permitidos = ROLES_LECTURA
    template_name = "historiales/mascota_timeline.html"
    context_object_name = "mascota"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["historiales"] = self.object.historiales.select_related(
            "veterinario", "consulta_relacionada"
        ).prefetch_related("resultados_lab").order_by("-fecha_atencion")
        return context


class HistorialCreateView(RolRequeridoMixin, CreateView):
    """RF-03: registrar la consulta clínica completa (síntomas, diagnóstico, tratamiento, medicamentos)."""

    model = HistorialClinico
    form_class = HistorialClinicoForm
    roles_permitidos = ROLES_CLINICOS
    template_name = "historiales/historial_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.mascota = get_object_or_404(Mascota, pk=kwargs["mascota_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["mascota"] = self.mascota
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mascota"] = self.mascota
        return context

    def form_valid(self, form):
        form.instance.mascota = self.mascota
        form.instance.creado_por = self.request.user
        if not form.instance.veterinario_id:
            perfil = getattr(self.request.user, "perfil", None)
            if perfil and perfil.rol == "VET":
                form.instance.veterinario = self.request.user
        response = super().form_valid(form)
        registrar_bitacora(self.request.user, "Registró historial clínico", str(self.object))
        messages.success(self.request, "Historial clínico registrado correctamente.")
        return response


class HistorialDetailView(RolRequeridoMixin, DetailView):
    model = HistorialClinico
    roles_permitidos = ROLES_LECTURA
    template_name = "historiales/historial_detail.html"
    context_object_name = "historial"


class HistorialUpdateView(RolRequeridoMixin, UpdateView):
    model = HistorialClinico
    form_class = HistorialClinicoForm
    roles_permitidos = ROLES_CLINICOS
    template_name = "historiales/historial_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["mascota"] = self.object.mascota
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mascota"] = self.object.mascota
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        registrar_bitacora(self.request.user, "Editó historial clínico", str(self.object))
        messages.success(self.request, "Historial clínico actualizado.")
        return response


class HistorialDeleteView(RolRequeridoMixin, DeleteView):
    model = HistorialClinico
    roles_permitidos = ROLES_ELIMINACION
    template_name = "historiales/historial_confirm_delete.html"

    def get_success_url(self):
        return reverse("historiales:timeline", kwargs={"pk": self.object.mascota.pk})

    def form_valid(self, form):
        mascota_str = str(self.object.mascota)
        registrar_bitacora(self.request.user, "Eliminó historial clínico", mascota_str)
        messages.success(self.request, "Registro de historial eliminado.")
        return super().form_valid(form)


class RecetaDigitalView(RolRequeridoMixin, DetailView):
    """RF-04: generar la receta digital de una consulta."""

    model = HistorialClinico
    roles_permitidos = ROLES_LECTURA
    template_name = "historiales/receta_digital.html"
    context_object_name = "historial"


class ResultadoLaboratorioCreateView(RolRequeridoMixin, CreateView):
    """RF-05: registrar resultados de laboratorio como variables estructuradas."""

    model = ResultadoLaboratorio
    form_class = ResultadoLaboratorioForm
    roles_permitidos = ROLES_CLINICOS
    template_name = "historiales/resultado_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.historial = get_object_or_404(HistorialClinico, pk=kwargs["historial_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["historial"] = self.historial
        return context

    def form_valid(self, form):
        form.instance.historial = self.historial
        response = super().form_valid(form)
        registrar_bitacora(
            self.request.user, "Registró resultado de laboratorio",
            f"{form.instance.nombre_variable} - {self.historial.mascota}",
        )
        messages.success(self.request, "Resultado de laboratorio registrado.")
        return response

    def get_success_url(self):
        return reverse("historiales:detalle", kwargs={"pk": self.historial.pk})
