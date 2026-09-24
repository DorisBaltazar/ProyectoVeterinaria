from django import forms
from django.utils import timezone

from .models import HistorialClinico, ResultadoLaboratorio

INPUT = "w-full bg-transparent border-none focus:ring-0 text-on-surface font-medium placeholder:text-slate-400"
SELECT = "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20"


class HistorialClinicoForm(forms.ModelForm):
    class Meta:
        model = HistorialClinico
        fields = [
            "tipo_atencion", "fecha_atencion", "motivo", "sintomas", "diagnostico",
            "tratamiento", "medicamentos", "peso_kg", "temperatura_c",
            "observaciones", "fecha_proximo_control", "consulta_relacionada", "veterinario",
        ]
        widgets = {
            "tipo_atencion": forms.Select(attrs={"class": SELECT}),
            "fecha_atencion": forms.DateTimeInput(attrs={"class": SELECT, "type": "datetime-local"}),
            "motivo": forms.TextInput(attrs={"class": INPUT, "placeholder": "Motivo de consulta"}),
            "sintomas": forms.Textarea(attrs={"class": SELECT, "rows": 3}),
            "diagnostico": forms.Textarea(attrs={"class": SELECT, "rows": 3}),
            "tratamiento": forms.Textarea(attrs={"class": SELECT, "rows": 3}),
            "medicamentos": forms.Textarea(attrs={"class": SELECT, "rows": 3, "placeholder": "Medicamento, dosis e indicaciones..."}),
            "peso_kg": forms.NumberInput(attrs={"class": SELECT, "step": "0.01"}),
            "temperatura_c": forms.NumberInput(attrs={"class": SELECT, "step": "0.1"}),
            "observaciones": forms.Textarea(attrs={"class": SELECT, "rows": 2}),
            "fecha_proximo_control": forms.DateInput(attrs={"class": SELECT, "type": "date"}),
            "consulta_relacionada": forms.Select(attrs={"class": SELECT}),
            "veterinario": forms.Select(attrs={"class": SELECT}),
        }

    def __init__(self, *args, mascota=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get("fecha_atencion") and not self.instance.pk:
            self.initial["fecha_atencion"] = timezone.now().strftime("%Y-%m-%dT%H:%M")
        if mascota is not None:
            self.fields["consulta_relacionada"].queryset = HistorialClinico.objects.filter(
                mascota=mascota, tipo_atencion=HistorialClinico.TipoAtencion.CONSULTA
            )
        self.fields["consulta_relacionada"].required = False


class ResultadoLaboratorioForm(forms.ModelForm):
    class Meta:
        model = ResultadoLaboratorio
        fields = ["nombre_variable", "valor", "unidad", "valor_referencia", "observacion"]
        widgets = {
            "nombre_variable": forms.TextInput(attrs={"class": INPUT, "placeholder": "Ej: Hematocrito"}),
            "valor": forms.NumberInput(attrs={"class": SELECT, "step": "0.001"}),
            "unidad": forms.TextInput(attrs={"class": INPUT, "placeholder": "Ej: %"}),
            "valor_referencia": forms.TextInput(attrs={"class": INPUT, "placeholder": "Ej: 37-55 %"}),
            "observacion": forms.TextInput(attrs={"class": INPUT, "placeholder": "Ej: Normal"}),
        }
