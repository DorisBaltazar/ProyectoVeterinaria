from django import forms

from config.validadores import LimitesHtmlMixin
from django.utils import timezone
from datetime import timedelta

from .models import HistorialClinico, ResultadoLaboratorio

INPUT = "w-full bg-transparent border-none focus:ring-0 text-on-surface font-medium placeholder:text-slate-400"
SELECT = "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20"


class HistorialClinicoForm(LimitesHtmlMixin, forms.ModelForm):
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
            "fecha_proximo_control": forms.DateInput(format="%Y-%m-%d", attrs={"class": SELECT, "type": "date"}),
            "consulta_relacionada": forms.Select(attrs={"class": SELECT}),
            "veterinario": forms.Select(attrs={"class": SELECT}),
        }

    def __init__(self, *args, mascota=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get("fecha_atencion") and not self.instance.pk:
            self.initial["fecha_atencion"] = timezone.localtime().strftime("%Y-%m-%dT%H:%M")
        if mascota is not None:
            self.fields["consulta_relacionada"].queryset = HistorialClinico.objects.filter(
                mascota=mascota, tipo_atencion=HistorialClinico.TipoAtencion.CONSULTA
            )
        self.fields["consulta_relacionada"].required = False

    def clean(self):
        cleaned = super().clean()
        fa, prox = cleaned.get("fecha_atencion"), cleaned.get("fecha_proximo_control")
        if fa and fa > timezone.now() + timedelta(minutes=5):
            self.add_error("fecha_atencion", "La fecha de atención no puede estar en el futuro.")
        if fa and prox and prox < timezone.localtime(fa).date():
            self.add_error("fecha_proximo_control", "El próximo control no puede ser anterior a la atención.")
        return cleaned


class ResultadoLaboratorioForm(LimitesHtmlMixin, forms.ModelForm):
    class Meta:
        model = ResultadoLaboratorio
        fields = ["tipo_examen", "nombre_variable", "valor", "unidad", "valor_referencia", "observacion"]
        widgets = {
            "tipo_examen": forms.Select(attrs={"class": SELECT}),
            "nombre_variable": forms.TextInput(attrs={"class": INPUT, "placeholder": "Ej: Hematocrito", "list": "lista-variables", "autocomplete": "off"}),
            "valor": forms.NumberInput(attrs={"class": SELECT, "step": "0.001"}),
            "unidad": forms.TextInput(attrs={"class": INPUT, "placeholder": "Ej: %"}),
            "valor_referencia": forms.TextInput(attrs={"class": INPUT, "placeholder": "Ej: 37-55 %"}),
            "observacion": forms.TextInput(attrs={"class": INPUT, "placeholder": "Ej: Normal"}),
        }
