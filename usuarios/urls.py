from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    path("login/", views.LoginUsuarioView.as_view(), name="login"),
    path("logout/", views.LogoutUsuarioView.as_view(), name="logout"),
    path("", views.DashboardView.as_view(), name="dashboard"),
    # RF-11 / HU-03: gestión de usuarios y roles
    path("usuarios/", views.UsuarioListView.as_view(), name="usuarios_lista"),
    path("usuarios/nuevo/", views.UsuarioCreateView.as_view(), name="usuario_crear"),
    path("usuarios/<int:pk>/editar/", views.UsuarioUpdateView.as_view(), name="usuario_editar"),
    # RF-12 / HU-04: bitácora de acciones
    path("bitacora/", views.BitacoraListView.as_view(), name="bitacora"),

]
