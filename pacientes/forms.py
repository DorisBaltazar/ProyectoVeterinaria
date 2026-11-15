from django import forms

from config.validadores import LimitesHtmlMixin

from .models import Mascota, Propietario


class PropietarioForm(forms.ModelForm):
    class Meta:
        model = Propietario
        fields = ["ci", "nombre_completo", "telefono", "correo", "direccion"]
        widgets = {
            "ci": forms.TextInput(attrs={
                "class": "w-full bg-transparent border-none focus:ring-0 text-on-surface font-medium placeholder:text-slate-400",
                "placeholder": "Cédula de Identidad (CI)",
            }),
            "nombre_completo": forms.TextInput(attrs={
                "class": "w-full bg-transparent border-none focus:ring-0 text-on-surface font-medium placeholder:text-slate-400",
                "placeholder": "Nombre completo",
            }),
            "telefono": forms.TextInput(attrs={
                "class": "w-full bg-transparent border-none focus:ring-0 text-on-surface font-medium placeholder:text-slate-400",
                "placeholder": "Teléfono",
            }),
            "correo": forms.EmailInput(attrs={
                "class": "w-full bg-transparent border-none focus:ring-0 text-on-surface font-medium placeholder:text-slate-400",
                "placeholder": "Correo electrónico",
            }),
            "direccion": forms.TextInput(attrs={
                "class": "w-full bg-transparent border-none focus:ring-0 text-on-surface font-medium placeholder:text-slate-400",
                "placeholder": "Dirección",
            }),
        }

    def clean_ci(self):
        ci = self.cleaned_data["ci"].strip()
        qs = Propietario.objects.filter(ci=ci)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "Ya existe un propietario registrado con esta CI. Búscalo en vez de crear un duplicado."
            )
        return ci


class MascotaForm(LimitesHtmlMixin, forms.ModelForm):
    """Registro de mascota. La edad se puede dar de dos formas: con la fecha
    de nacimiento exacta o, si no se conoce, con la edad aproximada
    (años y meses); en ese caso se estima la fecha de nacimiento."""

    edad_anios = forms.IntegerField(
        label="Edad (años)", required=False, min_value=0, max_value=40,
        widget=forms.NumberInput(attrs={
            "class": "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20",
            "placeholder": "Años", "min": "0", "max": "40",
        }),
    )
    edad_meses = forms.IntegerField(
        label="Edad (meses)", required=False, min_value=0, max_value=11,
        widget=forms.NumberInput(attrs={
            "class": "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20",
            "placeholder": "Meses", "min": "0", "max": "11",
        }),
    )

    class Meta:
        model = Mascota
        fields = [
            "propietario", "nombre", "especie", "raza", "sexo",
            "fecha_nacimiento", "peso_kg", "foto", "alerta_medica", "notas",
        ]
        widgets = {
            "propietario": forms.Select(attrs={
                "class": "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20",
            }),
            "nombre": forms.TextInput(attrs={
                "class": "w-full bg-transparent border-none focus:ring-0 text-on-surface font-medium placeholder:text-slate-400",
                "placeholder": "Nombre de la mascota",
            }),
            "especie": forms.Select(attrs={
                "class": "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20",
            }),
            "raza": forms.TextInput(attrs={
                "class": "w-full bg-transparent border-none focus:ring-0 text-on-surface font-medium placeholder:text-slate-400",
                "placeholder": "Raza",
            }),
            "sexo": forms.Select(attrs={
                "class": "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20",
            }),
            # format ISO: un <input type="date"> solo muestra el valor si viene como AAAA-MM-DD
            "fecha_nacimiento": forms.DateInput(format="%Y-%m-%d", attrs={
                "class": "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20",
                "type": "date",
            }),
            "peso_kg": forms.NumberInput(attrs={
                "class": "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20",
                "step": "0.01", "placeholder": "Peso en kg",
            }),
            "foto": forms.FileInput(attrs={
                "class": "hidden",
                "accept": "image/png, image/jpeg",
            }),
            "alerta_medica": forms.Textarea(attrs={
                "class": "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20",
                "rows": 2, "placeholder": "Ej: Cuidado al cortar las uñas. Alérgico a la penicilina.",
            }),
            "notas": forms.Textarea(attrs={
                "class": "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20",
                "rows": 3,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Al editar, mostrar la edad actual en años y meses
        meses = self.instance.edad_en_meses if self.instance.pk else None
        if meses is not None:
            self.fields["edad_anios"].initial = meses // 12
            self.fields["edad_meses"].initial = meses % 12

    def clean(self):
        cleaned = super().clean()
        from datetime import date
        nac = cleaned.get("fecha_nacimiento")
        if nac and nac > date.today():
            self.add_error("fecha_nacimiento", "La fecha de nacimiento no puede estar en el futuro.")
        anios, meses = cleaned.get("edad_anios"), cleaned.get("edad_meses")
        if not cleaned.get("fecha_nacimiento") and (anios or meses):
            from datetime import date

            from dateutil.relativedelta import relativedelta

            cleaned["fecha_nacimiento"] = date.today() - relativedelta(years=anios or 0, months=meses or 0)
            self._edad_estimada = True
        else:
            self._edad_estimada = False
        return cleaned

    def save(self, commit=True):
        mascota = super().save(commit=False)
        if self._edad_estimada:
            mascota.fecha_nacimiento = self.cleaned_data["fecha_nacimiento"]
            mascota.fecha_nacimiento_estimada = True
        elif "fecha_nacimiento" in self.changed_data:
            # el usuario escribió una fecha exacta
            mascota.fecha_nacimiento_estimada = False
        elif "edad_anios" in self.changed_data or "edad_meses" in self.changed_data:
            from datetime import date

            from dateutil.relativedelta import relativedelta
            anios = self.cleaned_data.get("edad_anios") or 0
            meses = self.cleaned_data.get("edad_meses") or 0
            mascota.fecha_nacimiento = date.today() - relativedelta(years=anios, months=meses)
            mascota.fecha_nacimiento_estimada = True
        if commit:
            mascota.save()
            self.save_m2m()
        return mascota

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")
        if foto and hasattr(foto, "size") and foto.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La imagen no puede superar los 5 MB.")
        return foto


class PesoForm(LimitesHtmlMixin, forms.Form):
    """Registrar un pesaje ('Pesar hoy')."""

    peso_kg = forms.DecimalField(
        label="Peso (kg)", max_digits=5, decimal_places=2, min_value=0.01, max_value=200,
        widget=forms.NumberInput(attrs={
            "class": "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20",
            "step": "0.01", "placeholder": "Ej: 4.2", "autofocus": True,
        }),
    )
    fecha = forms.DateField(
        label="Fecha del pesaje",
        widget=forms.DateInput(format="%Y-%m-%d", attrs={
            "class": "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20",
            "type": "date",
        }),
    )

    def clean_fecha(self):
        from datetime import date
        fecha = self.cleaned_data["fecha"]
        if fecha > date.today():
            raise forms.ValidationError("La fecha del pesaje no puede estar en el futuro.")
        return fecha


class AlertaMedicaForm(forms.ModelForm):
    class Meta:
        model = Mascota
        fields = ["alerta_medica"]
        widgets = {
            "alerta_medica": forms.Textarea(attrs={
                "class": "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20",
                "rows": 4, "placeholder": "Ej: Es tranquilo, pero tener cuidado al cortar las uñas.",
            }),
        }
