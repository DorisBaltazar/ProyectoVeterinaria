from django.urls import path

from . import views

app_name = "citas"

urlpatterns = [
    path("", views.CitaListView.as_view(), name="lista"),
    path("nueva/", views.CitaCreateView.as_view(), name="crear"),
    path("<int:pk>/", views.CitaDetailView.as_view(), name="detalle"),
    path("<int:pk>/editar/", views.CitaUpdateView.as_view(), name="editar"),
    path("<int:pk>/eliminar/", views.CitaDeleteView.as_view(), name="eliminar"),
]