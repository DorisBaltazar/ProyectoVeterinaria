from django.contrib.auth.models import User
from django.db import models

# Create your models here.
class Perfil(models.Model):
    """
    Extiende el modelo de usuario nativo de Django (auth.User) para
    asociar un ROL clínico. La app 'usuarios' NO reemplaza el sistema
    de autenticación de Django: lo complementa, tal como se definió
    en el punto 3.4 (Gestión de Usuarios y Seguridad) del perfil de
    proyecto -> "arquitectura nativa de gestión de usuarios de Django".
    """

    class Rol(models.TextChoices):
        ADMINISTRADOR = "ADMIN", "Administrador"
        VETERINARIO = "VET", "Veterinario"
        RECEPCIONISTA = "RECEP", "Recepcionista"

    usuario = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="perfil"
    )
    rol = models.CharField(
        max_length=10, choices=Rol.choices, default=Rol.RECEPCIONISTA
    )
    telefono = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuario"

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} ({self.get_rol_display()})"

    @property
    def es_administrador(self):
        return self.rol == self.Rol.ADMINISTRADOR

    @property
    def es_veterinario(self):
        return self.rol == self.Rol.VETERINARIO

    @property
    def es_recepcionista(self):
        return self.rol == self.Rol.RECEPCIONISTA
