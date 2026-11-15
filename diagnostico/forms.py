from django import forms

from config.validadores import LimitesHtmlMixin

from pacientes.models import Mascota

from .models import DiagnosticoIA

INPUT_CLASS = "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20"
CHECK_CLASS = "w-5 h-5 rounded border-outline text-primary focus:ring-primary/30"

SINTOMAS_LABELS = {
    "fiebre": "Fiebre",
    "vomito": "Vómito",
    "diarrea": "Diarrea",
    "diarrea_con_sangre": "Diarrea con sangre",
    "letargo": "Letargo / decaimiento",
    "perdida_apetito": "Pérdida de apetito",
    "deshidratacion": "Deshidratación visible",
    "tos": "Tos",
    "estornudos": "Estornudos",
    "secrecion_nasal": "Secreción nasal",
    "secrecion_ocular": "Secreción ocular",
    "dificultad_respiratoria": "Dificultad respiratoria",
    "convulsiones": "Convulsiones",
    "temblores": "Temblores",
    "engrosamiento_almohadillas": "Engrosamiento de almohadillas",
    "picazon": "Picazón intensa",
    "lesiones_piel": "Lesiones en la piel",
}


class DiagnosticoForm(LimitesHtmlMixin, forms.ModelForm):
    mascota = forms.ModelChoiceField(
        queryset=Mascota.objects.filter(activo=True).select_related("propietario"),
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
        label="Mascota",
    )

    class Meta:
        model = DiagnosticoIA
        fields = (
            ["mascota", "edad_meses", "temperatura_c", "leucocitos_mil_mm3", "hidratacion_pct"]
            + list(SINTOMAS_LABELS.keys())
        )
        widgets = {
            "edad_meses": forms.NumberInput(attrs={"class": INPUT_CLASS, "placeholder": "Edad en meses"}),
            "temperatura_c": forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.1", "placeholder": "°C"}),
            "leucocitos_mil_mm3": forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.1",
                                                            "placeholder": "Leucocitos (miles/mm³)"}),
            "hidratacion_pct": forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.1",
                                                         "placeholder": "% hidratación estimada"}),
            **{s: forms.CheckboxInput(attrs={"class": CHECK_CLASS}) for s in SINTOMAS_LABELS},
        }
        labels = {**{"edad_meses": "Edad (meses)", "temperatura_c": "Temperatura (°C)",
                     "leucocitos_mil_mm3": "Leucocitos (miles/mm³)", "hidratacion_pct": "Hidratación (%)"},
                  **SINTOMAS_LABELS}

    def datos_para_inferencia(self):
        """Arma el diccionario de entrada que espera el servicio de
        inferencia (incluye la especie de la mascota seleccionada)."""
        cd = self.cleaned_data
        datos = {
            "especie": "Perro" if cd["mascota"].especie == "PERRO" else (
                "Gato" if cd["mascota"].especie == "GATO" else "Perro"),
            "edad_meses": cd["edad_meses"],
            "temperatura_c": float(cd["temperatura_c"]),
            "leucocitos_mil_mm3": float(cd["leucocitos_mil_mm3"]),
            "hidratacion_pct": float(cd["hidratacion_pct"]),
        }
        for s in SINTOMAS_LABELS:
            datos[s] = int(bool(cd.get(s)))
        return datos


class RetroalimentacionForm(forms.ModelForm):
    class Meta:
        model = DiagnosticoIA
        fields = ["retroalimentacion", "diagnostico_real", "observaciones_feedback"]
        widgets = {
            "retroalimentacion": forms.Select(attrs={"class": INPUT_CLASS}),
            "diagnostico_real": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Diagnóstico real (solo si corriges la sugerencia del modelo)",
            }),
            "observaciones_feedback": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3}),
        }
        labels = {
            "retroalimentacion": "Retroalimentación",
            "diagnostico_real": "Diagnóstico real (si corresponde)",
            "observaciones_feedback": "Observaciones",
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("retroalimentacion") == DiagnosticoIA.Retroalimentacion.CORREGIDO and not cleaned.get(
                "diagnostico_real"):
            self.add_error("diagnostico_real", "Indica el diagnóstico real al corregir la sugerencia del modelo.")
        return cleaned
