from django.conf import settings
from django.db import models
from django.urls import reverse

# Create your models here.

class Cita(models.Model):
    """
    Registro de citas y atención clínica (HU-05, HU-06).
    Centraliza la asignación de turnos y organiza el flujo de
    pacientes, reemplazando las anotaciones verbales/dispersas
    descritas en la Situación Problemática (3.2.1).

    NOTA: en esta primera iteración el propietario y la mascota se
    capturan como texto libre para agilizar la entrega; en la
    Iteración 2 se reemplazará por FK a los modelos de la app
    'pacientes' (registro de propietarios/mascotas) sin romper esta
    estructura, dado el diseño en capas (MVT) del sistema.
    """

    class Especie(models.TextChoices):
        PERRO = "PERRO", "Perro"
        GATO = "GATO", "Gato"
        OTRO = "OTRO", "Otro"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        ATENDIDA = "ATENDIDA", "Atendida"
        CANCELADA = "CANCELADA", "Cancelada"

    propietario_nombre = models.CharField("Nombre del propietario", max_length=120)
    propietario_telefono = models.CharField("Teléfono", max_length=20, blank=True)
    mascota_nombre = models.CharField("Nombre de la mascota", max_length=80)
    especie = models.CharField(max_length=10, choices=Especie.choices, default=Especie.PERRO)

    fecha = models.DateField("Fecha de la cita")
    hora = models.TimeField("Hora de la cita")
    motivo = models.CharField("Motivo de consulta", max_length=255)

    veterinario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"perfil__rol": "VET"},
        related_name="citas_asignadas",
        verbose_name="Veterinario asignado",
    )
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    observaciones = models.TextField(blank=True)

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="citas_creadas",
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ["fecha", "hora"]

    def __str__(self):
        return f"{self.mascota_nombre} - {self.fecha} {self.hora} ({self.get_estado_display()})"

    def get_absolute_url(self):
        return reverse("citas:detalle", kwargs={"pk": self.pk})
