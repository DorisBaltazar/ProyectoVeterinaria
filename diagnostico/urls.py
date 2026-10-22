from django.urls import path

from . import views

app_name = "diagnostico"

urlpatterns = [
    path("", views.DiagnosticoListView.as_view(), name="lista"),
    path("nuevo/", views.DiagnosticoCreateView.as_view(), name="crear"),
    path("<int:pk>/", views.DiagnosticoDetailView.as_view(), name="detalle"),
    path("<int:pk>/retroalimentacion/", views.DiagnosticoFeedbackView.as_view(), name="feedback"),
    path("reporte/", views.ReporteDiagnosticosView.as_view(), name="reporte"),
]