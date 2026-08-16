from django.contrib import admin

# Register your models here.
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Perfil


class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False
    verbose_name_plural = "Perfil (rol clínico)"


class UsuarioAdmin(UserAdmin):
    inlines = (PerfilInline,)
    list_display = ("username", "first_name", "last_name", "email", "get_rol", "is_active")

    def get_rol(self, obj):
        return getattr(obj.perfil, "rol", "-")
    get_rol.short_description = "Rol"


admin.site.unregister(User)
admin.site.register(User, UsuarioAdmin)