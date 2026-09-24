from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.InsumoListView.as_view(), name="lista"),
    path("nuevo/", views.InsumoCreateView.as_view(), name="crear"),
    path("<int:pk>/editar/", views.InsumoUpdateView.as_view(), name="editar"),
    path("movimientos/", views.MovimientoListView.as_view(), name="movimientos"),
    path("movimientos/nuevo/", views.MovimientoCreateView.as_view(), name="movimiento_crear"),
]
