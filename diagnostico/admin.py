from django.contrib import admin

from .models import DiagnosticoIA


@admin.register(DiagnosticoIA)
class DiagnosticoIAAdmin(admin.ModelAdmin):
    list_display = ("mascota", "prediccion", "confianza", "retroalimentacion", "veterinario", "fecha")
    list_filter = ("retroalimentacion", "prediccion")
    search_fields = ("mascota__nombre", "mascota__codigo", "prediccion")
    readonly_fields = ("fecha", "prediccion", "confianza", "probabilidades")
