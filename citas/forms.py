from django import forms

from .models import Cita


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
            "propietario_nombre": forms.TextInput(attrs={"class": "form-control"}),
            "propietario_telefono": forms.TextInput(attrs={"class": "form-control"}),
            "mascota_nombre": forms.TextInput(attrs={"class": "form-control"}),
            "especie": forms.Select(attrs={"class": "form-select"}),
            "fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "hora": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "motivo": forms.TextInput(attrs={"class": "form-control"}),
            "veterinario": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
