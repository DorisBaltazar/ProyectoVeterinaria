from django.db import models

# Create your models here.
#poner los datos de los porpieraios y de las mascotas
from django.urls import reverse


class Propietario(models.Model):
    """Dueño(a) de una o varias mascotas.

    RF-01: se valida CI única para evitar propietarios duplicados.
    """

    ci = models.CharField(
        "Cédula de Identidad", max_length=20, unique=True,
        help_text="Documento único por propietario, evita registros duplicados (RF-01).",
    )
    nombre_completo = models.CharField("Nombre completo", max_length=150)
    telefono = models.CharField("Teléfono", max_length=20)
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
    peso_kg = models.DecimalField("Peso (kg)", max_digits=5, decimal_places=2, null=True, blank=True)

    foto = models.ImageField(
        "Foto de la mascota",
        upload_to="mascotas/%Y/%m/",
        blank=True,
        null=True,
        help_text="Formatos permitidos: JPG, PNG. Máx. 5 MB.",
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
        if not self.fecha_nacimiento:
            return None
        from datetime import date
        hoy = date.today()
        años = hoy.year - self.fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )
        return años