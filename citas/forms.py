from django import forms

from .models import Cita

INPUT = "w-full bg-transparent border-none focus:ring-0 text-on-surface font-medium placeholder:text-slate-400"
SELECT = "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20"

class CitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        fields = [
            "propietario_nombre",
            "propietario_telefono",
            "mascota_nombre",
            "especie",
            "fecha",
            "hora",
            "motivo",
            "veterinario",
            "estado",
            "observaciones",
        ]
        widgets = {
            "propietario_nombre": forms.TextInput(attrs={"class": INPUT, "placeholder": "Nombre del propietario"}),
            "propietario_telefono": forms.TextInput(attrs={"class": INPUT, "placeholder": "Teléfono"}),
            "mascota_nombre": forms.TextInput(attrs={"class": INPUT, "placeholder": "Nombre de la mascota"}),
            "especie": forms.Select(attrs={"class": SELECT}),
            "fecha": forms.DateInput(format="%Y-%m-%d", attrs={"class": SELECT, "type": "date"}),
            "hora": forms.TimeInput(format="%H:%M", attrs={"class": SELECT, "type": "time"}),
            "motivo": forms.TextInput(attrs={"class": INPUT, "placeholder": "Motivo de consulta"}),
            "veterinario": forms.Select(attrs={"class": SELECT}),
            "estado": forms.Select(attrs={"class": SELECT}),
            "observaciones": forms.Textarea(attrs={"class": SELECT, "rows": 3}),
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Una cita nueva siempre nace "Pendiente": el estado solo se cambia
        # una vez creado el registro.
        if not self.instance.pk:
            del self.fields["estado"]

    def clean(self):
        cleaned = super().clean()
        # Fecha y hora solo se pueden cambiar mientras la cita está Pendiente
        # (reprogramar); en otros estados se conservan los valores registrados.
        if self.instance.pk and cleaned.get("estado") != Cita.Estado.PENDIENTE:
            cleaned["fecha"] = self.instance.fecha
            cleaned["hora"] = self.instance.hora
            self.errors.pop("fecha", None)
            self.errors.pop("hora", None)
        else:
            from datetime import date
            fecha = cleaned.get("fecha")
            if fecha and fecha < date.today() and (not self.instance.pk or fecha != self.instance.fecha):
                self.add_error("fecha", "La fecha de la cita no puede estar en el pasado.")
        return cleaned
