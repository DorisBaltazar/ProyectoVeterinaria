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
            "fecha": forms.DateInput(attrs={"class": SELECT, "type": "date"}),
            "hora": forms.TimeInput(attrs={"class": SELECT, "type": "time"}),
            "motivo": forms.TextInput(attrs={"class": INPUT, "placeholder": "Motivo de consulta"}),
            "veterinario": forms.Select(attrs={"class": SELECT}),
            "estado": forms.Select(attrs={"class": SELECT}),
            "observaciones": forms.Textarea(attrs={"class": SELECT, "rows": 3}),
        }
