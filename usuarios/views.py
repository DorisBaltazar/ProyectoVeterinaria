from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from .bitacora import registrar_bitacora
from .forms import LoginForm, UsuarioCreateForm, UsuarioUpdateForm
from .mixins import RolRequeridoMixin
from .models import Bitacora


class LoginUsuarioView(LoginView):
    template_name = "usuarios/login.html"
    redirect_authenticated_user = True
    authentication_form = LoginForm

    def form_valid(self, form):
        response = super().form_valid(form)
        registrar_bitacora(self.request.user, "Inició sesión")
        return response


class LogoutUsuarioView(LogoutView):
    next_page = "usuarios:login"


class DashboardView(RolRequeridoMixin, TemplateView):
    """
    Pantalla de inicio tras el login. Muestra accesos distintos según el
    rol (RBAC) y un recordatorio de las citas del día (RF-07 / HU-06).
    """

    template_name = "usuarios/dashboard.html"
    roles_permitidos = ["ADMIN", "VET", "RECEP"]

    def get_context_data(self, **kwargs):
        from datetime import date

        from citas.models import Cita

        context = super().get_context_data(**kwargs)
        perfil = getattr(self.request.user, "perfil", None)
        context["perfil"] = perfil

        citas_hoy = Cita.objects.filter(fecha=date.today()).exclude(estado="CANCELADA")
        if perfil and perfil.rol == "VET":
            citas_hoy = citas_hoy.filter(veterinario=self.request.user)
        citas_hoy = citas_hoy.order_by("hora")

        context["citas_hoy"] = citas_hoy
        context["total_citas_hoy"] = citas_hoy.count()
        context["proxima_cita"] = citas_hoy.filter(estado__in=["PENDIENTE", "CONFIRMADA"]).first()
        return context


# --- RF-11 / HU-03: gestión de usuarios y roles (solo Administrador) ---

class UsuarioListView(RolRequeridoMixin, ListView):
    model = User
    roles_permitidos = ["ADMIN"]
    template_name = "usuarios/usuario_list.html"
    context_object_name = "usuarios_lista"
    paginate_by = 20

    def get_queryset(self):
        return User.objects.select_related("perfil").order_by("username")


class UsuarioCreateView(RolRequeridoMixin, CreateView):
    model = User
    form_class = UsuarioCreateForm
    roles_permitidos = ["ADMIN"]
    template_name = "usuarios/usuario_form.html"
    success_url = reverse_lazy("usuarios:usuarios_lista")

    def form_valid(self, form):
        response = super().form_valid(form)
        registrar_bitacora(
            self.request.user, "Creó usuario",
            f"{self.object.username} (rol: {self.object.perfil.get_rol_display()})",
        )
        messages.success(self.request, "Usuario creado correctamente.")
        return response


class UsuarioUpdateView(RolRequeridoMixin, UpdateView):
    model = User
    form_class = UsuarioUpdateForm
    roles_permitidos = ["ADMIN"]
    template_name = "usuarios/usuario_form.html"
    success_url = reverse_lazy("usuarios:usuarios_lista")

    def form_valid(self, form):
        response = super().form_valid(form)
        registrar_bitacora(
            self.request.user, "Editó usuario",
            f"{self.object.username} (rol: {self.object.perfil.get_rol_display()})",
        )
        messages.success(self.request, "Usuario actualizado correctamente.")
        return response


# --- RF-12 / HU-04: bitácora de acciones (solo Administrador) ---

class BitacoraListView(RolRequeridoMixin, ListView):
    model = Bitacora
    roles_permitidos = ["ADMIN"]
    template_name = "usuarios/bitacora_list.html"
    context_object_name = "registros"
    paginate_by = 30
