from django.contrib import admin

# Register your models here.
from .models import Mascota, Propietario


@admin.register(Propietario)
class PropietarioAdmin(admin.ModelAdmin):
    list_display = ("nombre_completo", "telefono", "correo")
    search_fields = ("nombre_completo", "telefono", "correo")


@admin.register(Mascota)
class MascotaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "especie", "raza", "propietario", "activo")
    list_filter = ("especie", "sexo", "activo")
    search_fields = ("nombre", "propietario__nombre_completo")
