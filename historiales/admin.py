from django.contrib import admin

from .models import HistorialClinico, ResultadoLaboratorio


class ResultadoLaboratorioInline(admin.TabularInline):
    model = ResultadoLaboratorio
    extra = 0


@admin.register(HistorialClinico)
class HistorialClinicoAdmin(admin.ModelAdmin):
    list_display = ("mascota", "tipo_atencion", "fecha_atencion", "veterinario", "diagnostico")
    list_filter = ("tipo_atencion", "fecha_atencion")
    search_fields = ("mascota__nombre", "diagnostico", "sintomas")
    inlines = [ResultadoLaboratorioInline]

