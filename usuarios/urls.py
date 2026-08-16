from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    path("login/", views.LoginUsuarioView.as_view(), name="login"),
    path("logout/", views.LogoutUsuarioView.as_view(), name="logout"),
    path("", views.DashboardView.as_view(), name="dashboard"),
]
