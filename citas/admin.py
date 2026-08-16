from django.contrib import admin

# Register your models here.
from .models import Cita


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ("mascota_nombre", "propietario_nombre", "fecha", "hora", "estado", "veterinario")
    list_filter = ("estado", "especie", "fecha")
    search_fields = ("mascota_nombre", "propietario_nombre")
