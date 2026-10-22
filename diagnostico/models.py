from django.conf import settings
from django.db import models

from pacientes.models import Mascota


class DiagnosticoIA(models.Model):
    """Registro de una inferencia del módulo de aprendizaje automático
    (RF-13 a RF-15 / HU-13 a HU-15): captura los síntomas y variables de
    laboratorio ingresados por el veterinario, la predicción del modelo
    Random Forest y, posteriormente, la retroalimentación del profesional
    (RF-16 / HU-16: confirmación o corrección del diagnóstico sugerido)."""

    class Retroalimentacion(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente de revisión"
        CONFIRMADO = "CONFIRMADO", "Confirmado por el veterinario"
        CORREGIDO = "CORREGIDO", "Corregido por el veterinario"

    # --- Contexto clínico ---
    mascota = models.ForeignKey(Mascota, on_delete=models.CASCADE, related_name="diagnosticos_ia")
    veterinario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                     related_name="diagnosticos_realizados")
    fecha = models.DateTimeField(auto_now_add=True)

    # --- Variables de laboratorio (vectorización numérica) ---
    edad_meses = models.PositiveIntegerField()
    temperatura_c = models.DecimalField(max_digits=4, decimal_places=1)
    leucocitos_mil_mm3 = models.DecimalField(max_digits=5, decimal_places=1)
    hidratacion_pct = models.DecimalField(max_digits=5, decimal_places=1)

    # --- Catálogo taxonómico de síntomas (selectores discretos / booleanos) ---
    fiebre = models.BooleanField(default=False)
    vomito = models.BooleanField(default=False)
    diarrea = models.BooleanField(default=False)
    diarrea_con_sangre = models.BooleanField(default=False)
    letargo = models.BooleanField(default=False)
    perdida_apetito = models.BooleanField(default=False)
    deshidratacion = models.BooleanField(default=False)
    tos = models.BooleanField(default=False)
    estornudos = models.BooleanField(default=False)
    secrecion_nasal = models.BooleanField(default=False)
    secrecion_ocular = models.BooleanField(default=False)
    dificultad_respiratoria = models.BooleanField(default=False)
    convulsiones = models.BooleanField(default=False)
    temblores = models.BooleanField(default=False)
    engrosamiento_almohadillas = models.BooleanField(default=False)
    picazon = models.BooleanField(default=False)
    lesiones_piel = models.BooleanField(default=False)

    # --- Resultado de la inferencia (RF-14 / RF-15) ---
    prediccion = models.CharField(max_length=80)
    confianza = models.DecimalField(max_digits=5, decimal_places=2,
                                     help_text="Probabilidad (%) de la clase predicha.")
    probabilidades = models.JSONField(
        help_text="Distribución completa de probabilidades por clase (para mostrar el top-3)."
    )

    # --- Retroalimentación del veterinario (RF-16 / HU-16) ---
    retroalimentacion = models.CharField(max_length=12, choices=Retroalimentacion.choices,
                                          default=Retroalimentacion.PENDIENTE)
    diagnostico_real = models.CharField(
        max_length=80, blank=True,
        help_text="Diagnóstico final emitido por el veterinario, si corrigió la sugerencia del modelo."
    )
    observaciones_feedback = models.TextField(blank=True)
    fecha_feedback = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Diagnóstico asistido por IA"
        verbose_name_plural = "Diagnósticos asistidos por IA"

    def __str__(self):
        return f"{self.mascota} - {self.prediccion} ({self.confianza}%) - {self.fecha:%Y-%m-%d}"

    @property
    def diagnostico_final(self):
        """Diagnóstico de referencia: el corregido por el veterinario si
        existe, o la predicción del modelo en caso contrario."""
        return self.diagnostico_real or self.prediccion
