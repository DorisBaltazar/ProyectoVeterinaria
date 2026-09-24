from django.urls import path

from . import views

app_name = "historiales"

urlpatterns = [
    path("mascota/<int:pk>/", views.MascotaTimelineView.as_view(), name="timeline"),
    path("mascota/<int:mascota_id>/nueva/", views.HistorialCreateView.as_view(), name="crear"),
    path("<int:pk>/", views.HistorialDetailView.as_view(), name="detalle"),
    path("<int:pk>/editar/", views.HistorialUpdateView.as_view(), name="editar"),
    path("<int:pk>/eliminar/", views.HistorialDeleteView.as_view(), name="eliminar"),
    path("<int:pk>/receta/", views.RecetaDigitalView.as_view(), name="receta"),
    path("<int:historial_id>/laboratorio/nuevo/", views.ResultadoLaboratorioCreateView.as_view(), name="lab_crear"),
]
