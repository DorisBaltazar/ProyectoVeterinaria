#from django.shortcuts import render

# Create your views here.
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class LoginUsuarioView(LoginView):
    template_name = "usuarios/login.html"
    redirect_authenticated_user = True


class LogoutUsuarioView(LogoutView):
    next_page = "usuarios:login"


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Pantalla de inicio tras el login. Muestra accesos distintos
    según el rol (RBAC), ocultando el módulo de IA/diagnóstico
    para el rol Recepcionista, conforme al Alcance del proyecto (3.4).
    """

    template_name = "usuarios/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        perfil = getattr(self.request.user, "perfil", None)
        context["perfil"] = perfil
        return context