from django.contrib.auth.models import User
from django.db import models


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


class Bitacora(models.Model):
    """RF-12: registro de auditoría básico — quién hizo qué y cuándo.

    Se usa tanto para trazabilidad general del sistema como para dejar
    constancia de accesos/uso del Módulo de Aprendizaje Automático,
    restringido por rol según el Alcance (3.4) del proyecto.
    """

    usuario = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="acciones_bitacora"
    )
    accion = models.CharField("Acción", max_length=150)
    detalle = models.CharField("Detalle", max_length=255, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro de bitácora"
        verbose_name_plural = "Bitácora de acciones"
        ordering = ["-fecha_hora"]

    def __str__(self):
        return f"[{self.fecha_hora:%d/%m/%Y %H:%M}] {self.usuario} - {self.accion}"
