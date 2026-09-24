from django.conf import settings
from django.db import models
from django.urls import reverse


class HistorialClinico(models.Model):
    """Consulta clínica o control posterior de una mascota (RF-03/04/08 - Iteración 2).

    Un mismo modelo cubre tanto la consulta inicial como los controles
    posteriores (tipo_atencion), lo que permite reconstruir la línea de
    tiempo de evolución de una mascota consultando un único listado
    ordenado por fecha.
    """

    class TipoAtencion(models.TextChoices):
        CONSULTA = "CONSULTA", "Consulta"
        CONTROL = "CONTROL", "Control posterior"

    mascota = models.ForeignKey(
        "pacientes.Mascota", on_delete=models.CASCADE, related_name="historiales"
    )
    cita = models.ForeignKey(
        "citas.Cita", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="historial", help_text="Cita de origen, si la consulta viene de una cita agendada.",
    )
    veterinario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={"perfil__rol": "VET"}, related_name="historiales_atendidos",
    )
    tipo_atencion = models.CharField(max_length=10, choices=TipoAtencion.choices, default=TipoAtencion.CONSULTA)
    fecha_atencion = models.DateTimeField("Fecha y hora de atención")

    motivo = models.CharField("Motivo de consulta", max_length=255)
    sintomas = models.TextField("Síntomas observados")
    diagnostico = models.TextField("Diagnóstico")
    tratamiento = models.TextField("Tratamiento indicado", blank=True)
    medicamentos = models.TextField(
        "Medicamentos recetados", blank=True,
        help_text="Detalle de medicamento, dosis e indicaciones (usado para la receta digital).",
    )

    peso_kg = models.DecimalField("Peso registrado (kg)", max_digits=5, decimal_places=2, null=True, blank=True)
    temperatura_c = models.DecimalField("Temperatura (°C)", max_digits=4, decimal_places=1, null=True, blank=True)
    observaciones = models.TextField(blank=True)

    fecha_proximo_control = models.DateField("Fecha sugerida de próximo control", null=True, blank=True)

    consulta_relacionada = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="controles", help_text="Consulta original de la que este registro es un control posterior.",
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="historiales_creados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historial clínico"
        verbose_name_plural = "Historiales clínicos"
        ordering = ["-fecha_atencion"]

    def __str__(self):
        return f"{self.mascota.nombre} - {self.get_tipo_atencion_display()} ({self.fecha_atencion:%d/%m/%Y})"

    def get_absolute_url(self):
        return reverse("historiales:detalle", kwargs={"pk": self.pk})


class ResultadoLaboratorio(models.Model):
    """Resultado cuantitativo de laboratorio (RF-05 / futura entrada del modelo ML)."""

    historial = models.ForeignKey(
        HistorialClinico, on_delete=models.CASCADE, related_name="resultados_lab"
    )
    nombre_variable = models.CharField(
        "Variable / examen", max_length=100,
        help_text="Ej: Hematocrito, Glóbulos blancos, Glucosa.",
    )
    valor = models.DecimalField(max_digits=10, decimal_places=3)
    unidad = models.CharField(max_length=20, blank=True, help_text="Ej: %, mg/dL, x10^3/µL")
    valor_referencia = models.CharField(
        "Rango de referencia", max_length=50, blank=True,
        help_text="Ej: 37-55 %. Referencial, no clínicamente validado.",
    )
    observacion = models.CharField(max_length=20, blank=True, help_text="Ej: Normal, Alto, Bajo")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Resultado de laboratorio"
        verbose_name_plural = "Resultados de laboratorio"
        ordering = ["nombre_variable"]

    def __str__(self):
        return f"{self.nombre_variable}: {self.valor} {self.unidad}"


