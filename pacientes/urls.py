# todo las rutas se definen aqui
from django.urls import path

from . import views

app_name = "pacientes"

urlpatterns = [
    path("", views.MascotaListView.as_view(), name="lista"),
    path("nueva/", views.MascotaCreateView.as_view(), name="crear"),
    path("<int:pk>/", views.MascotaDetailView.as_view(), name="detalle"),
    path("<int:pk>/editar/", views.MascotaUpdateView.as_view(), name="editar"),
    path("<int:pk>/eliminar/", views.MascotaDeleteView.as_view(), name="eliminar"),
    # RF-02: propietarios (buscar y editar)
    path("propietarios/", views.PropietarioListView.as_view(), name="propietarios"),
    path("propietario/nuevo/", views.PropietarioCreateView.as_view(), name="propietario_crear"),
    path("propietario/<int:pk>/editar/", views.PropietarioUpdateView.as_view(), name="propietario_editar"),
]
