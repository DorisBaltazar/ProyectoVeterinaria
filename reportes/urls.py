from django.urls import path

from . import views

app_name = "reportes"

urlpatterns = [
    path("", views.IndiceReportesView.as_view(), name="index"),
    path("ficha/<int:pk>/", views.FichaMascotaView.as_view(), name="ficha"),
    path("<slug:clave>/", views.ReporteView.as_view(), name="reporte"),
]
