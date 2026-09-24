from django.contrib import admin

from .models import Insumo, MovimientoInventario


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "stock_actual", "stock_minimo", "unidad_medida", "activo")
    list_filter = ("categoria", "activo")
    search_fields = ("nombre",)


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ("insumo", "tipo", "cantidad", "motivo", "usuario", "fecha")
    list_filter = ("tipo", "fecha")

