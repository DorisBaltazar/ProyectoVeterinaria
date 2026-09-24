from django.conf import settings
from django.db import models, transaction
from django.core.exceptions import ValidationError


class Insumo(models.Model):
    """Medicamento, material o producto controlado en el inventario de la clínica."""

    class Categoria(models.TextChoices):
        MEDICAMENTO = "MEDICAMENTO", "Medicamento"
        MATERIAL = "MATERIAL", "Material médico"
        ALIMENTO = "ALIMENTO", "Alimento"
        OTRO = "OTRO", "Otro"

    nombre = models.CharField(max_length=150)
    categoria = models.CharField(max_length=15, choices=Categoria.choices, default=Categoria.MEDICAMENTO)
    unidad_medida = models.CharField(
        max_length=20, default="unidad", help_text="Ej: unidad, ml, caja, tableta."
    )
    stock_actual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_minimo = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Bajo este nivel, el insumo aparece en las alertas de reabastecimiento.",
    )
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Insumo"
        verbose_name_plural = "Insumos"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.stock_actual} {self.unidad_medida})"

    @property
    def stock_bajo(self):
        return self.stock_actual <= self.stock_minimo


class MovimientoInventario(models.Model):
    """Entrada o salida de un insumo (RF-09), con descuento automático de stock.

    Cuando el movimiento está asociado a una consulta (historial_relacionado),
    representa el insumo usado durante esa atención, evitando el doble
    registro manual del stock.
    """

    class Tipo(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SALIDA = "SALIDA", "Salida"

    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name="movimientos")
    tipo = models.CharField(max_length=8, choices=Tipo.choices)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    motivo = models.CharField(
        max_length=150, help_text="Ej: Compra, Uso en consulta, Ajuste de inventario, Vencimiento."
    )
    historial_relacionado = models.ForeignKey(
        "historiales.HistorialClinico", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="insumos_usados",
    )
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimiento de inventario"
        verbose_name_plural = "Movimientos de inventario"
        ordering = ["-fecha"]

    def __str__(self):
        signo = "+" if self.tipo == self.Tipo.ENTRADA else "-"
        return f"{self.insumo.nombre} {signo}{self.cantidad} ({self.motivo})"

    def clean(self):
        if self.tipo == self.Tipo.SALIDA and self.cantidad > self.insumo.stock_actual:
            raise ValidationError(
                f"Stock insuficiente: hay {self.insumo.stock_actual} {self.insumo.unidad_medida} "
                f"disponibles de {self.insumo.nombre}."
            )

    def save(self, *args, **kwargs):
        """Aplica el movimiento al stock del insumo de forma atómica (RF-09)."""
        is_new = self._state.adding
        with transaction.atomic():
            super().save(*args, **kwargs)
            if is_new:
                delta = self.cantidad if self.tipo == self.Tipo.ENTRADA else -self.cantidad
                Insumo.objects.filter(pk=self.insumo_id).update(
                    stock_actual=models.F("stock_actual") + delta
                )

