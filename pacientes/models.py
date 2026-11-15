from django.db import models

# Create your models here.
#poner los datos de los porpieraios y de las mascotas
from django.urls import reverse
from config import validadores as val


class Propietario(models.Model):
    """Dueño(a) de una o varias mascotas.

    RF-01: se valida CI única para evitar propietarios duplicados.
    """

    ci = models.CharField(
        "Cédula de Identidad", max_length=20, unique=True,
        help_text="Documento único por propietario, evita registros duplicados (RF-01).",
    )
    nombre_completo = models.CharField("Nombre completo", max_length=150)
    telefono = models.CharField("Teléfono", max_length=20, validators=[val.telefono_valido])
    correo = models.EmailField("Correo electrónico", blank=True)
    direccion = models.CharField("Dirección", max_length=255, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Propietario"
        verbose_name_plural = "Propietarios"
        ordering = ["nombre_completo"]

    def __str__(self):
        return f"{self.nombre_completo} (CI: {self.ci})"


class Mascota(models.Model):
    """Paciente (mascota) asociado a un propietario, con foto.

    RF-02: cada mascota recibe un código único autogenerado, usado para
    identificación y búsqueda rápida (además de nombre y CI del propietario).
    """

    class Especie(models.TextChoices):
        PERRO = "PERRO", "Perro"
        GATO = "GATO", "Gato"
        AVE = "AVE", "Ave"
        OTRO = "OTRO", "Otro"

    class Sexo(models.TextChoices):
        MACHO = "M", "Macho"
        HEMBRA = "H", "Hembra"

    codigo = models.CharField(
        "Código único", max_length=12, unique=True, blank=True, editable=False,
        help_text="Generado automáticamente al registrar la mascota (RF-02).",
    )
    propietario = models.ForeignKey(
        Propietario, on_delete=models.CASCADE, related_name="mascotas"
    )
    nombre = models.CharField("Nombre de la mascota", max_length=80)
    especie = models.CharField(max_length=10, choices=Especie.choices, default=Especie.PERRO)
    raza = models.CharField("Raza", max_length=100, blank=True)
    sexo = models.CharField(max_length=1, choices=Sexo.choices, default=Sexo.MACHO)
    fecha_nacimiento = models.DateField("Fecha de nacimiento", null=True, blank=True)
    fecha_nacimiento_estimada = models.BooleanField(
        "Fecha de nacimiento estimada", default=False,
        help_text="True cuando se ingresó la edad aproximada en lugar de la fecha exacta.",
    )
    peso_kg = models.DecimalField("Peso (kg)", max_digits=5, decimal_places=2, null=True, blank=True,
                                  validators=val.peso_validators())

    foto = models.ImageField(
        "Foto de la mascota",
        upload_to="mascotas/%Y/%m/",
        blank=True,
        null=True,
        help_text="Formatos permitidos: JPG, PNG. Máx. 5 MB.",
    )

    alerta_medica = models.TextField(
        "Alerta médica", blank=True,
        help_text="Aviso importante para el personal. Ej: alergias, agresividad, cuidados especiales.",
    )
    notas = models.TextField("Notas adicionales", blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Mascota"
        verbose_name_plural = "Mascotas"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre} ({self.get_especie_display()}) - {self.propietario.nombre_completo}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.codigo:
            self.codigo = f"M-{self.pk:05d}"
            super().save(update_fields=["codigo"])

    def get_absolute_url(self):
        return reverse("pacientes:detalle", kwargs={"pk": self.pk})

    @property
    def edad_aproximada(self):
        """Edad en años completos (None si no hay fecha de nacimiento ni edad)."""
        if not self.fecha_nacimiento:
            return None
        from datetime import date
        hoy = date.today()
        años = hoy.year - self.fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )
        return años

    @property
    def edad_en_meses(self):
        """Edad total en meses, calculada a partir de la fecha de nacimiento."""
        if not self.fecha_nacimiento:
            return None
        from datetime import date
        hoy = date.today()
        meses = (hoy.year - self.fecha_nacimiento.year) * 12 + (hoy.month - self.fecha_nacimiento.month)
        if hoy.day < self.fecha_nacimiento.day:
            meses -= 1
        return max(meses, 0)

    @property
    def edad_texto(self):
        """Edad legible: '3 años', '3 años y 2 meses', '5 meses' o None."""
        meses = self.edad_en_meses
        if meses is None:
            return None
        años, resto = divmod(meses, 12)
        partes = []
        if años:
            partes.append(f"{años} año{'s' if años != 1 else ''}")
        if resto or not años:
            partes.append(f"{resto} mes{'es' if resto != 1 else ''}")
        texto = " y ".join(partes)
        return f"≈ {texto}" if self.fecha_nacimiento_estimada else texto

    # ---- Control de peso -------------------------------------------------
    def registrar_peso(self, peso_kg, fecha=None, usuario=None):
        """Guarda una medición de peso (una por día) y actualiza el peso actual."""
        from datetime import date
        fecha = fecha or date.today()
        registro, _ = RegistroPeso.objects.update_or_create(
            mascota=self, fecha=fecha,
            defaults={"peso_kg": peso_kg, "registrado_por": usuario},
        )
        ultimo = self.pesos.order_by("-fecha", "-id").first()
        if ultimo and self.peso_kg != ultimo.peso_kg:
            self.peso_kg = ultimo.peso_kg
            self.save(update_fields=["peso_kg"])
        return registro

    @property
    def peso_actual(self):
        ultimo = self.pesos.order_by("-fecha", "-id").first()
        return ultimo.peso_kg if ultimo else self.peso_kg

    def variacion_peso(self):
        """(diferencia, fecha de la primera medición) o None si hay menos de 2 mediciones."""
        pesos = list(self.pesos.order_by("fecha", "id"))
        if len(pesos) < 2:
            return None
        return pesos[-1].peso_kg - pesos[0].peso_kg, pesos[0].fecha


class RegistroPeso(models.Model):
    """Historial de pesajes de una mascota, para ver su evolución."""

    mascota = models.ForeignKey(Mascota, on_delete=models.CASCADE, related_name="pesos")
    fecha = models.DateField("Fecha del pesaje")
    peso_kg = models.DecimalField("Peso (kg)", max_digits=5, decimal_places=2, validators=val.peso_validators())
    registrado_por = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "Registro de peso"
        verbose_name_plural = "Registros de peso"
        ordering = ["fecha", "id"]
        constraints = [
            models.UniqueConstraint(fields=["mascota", "fecha"], name="un_peso_por_mascota_y_dia"),
        ]

    def __str__(self):
        return f"{self.mascota.nombre}: {self.peso_kg} kg ({self.fecha})"
