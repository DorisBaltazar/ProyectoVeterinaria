from django import forms
from django.contrib.auth import get_user_model

from citas.models import Cita
from diagnostico.models import DiagnosticoIA
from inventario.models import Insumo, MovimientoInventario
from pacientes.models import Mascota

CLS = "bg-surface-container-highest border-none rounded-xl p-2.5 text-sm"


def _sel(choices, label):
    return forms.ChoiceField(choices=choices, required=False, label=label,
                             widget=forms.Select(attrs={"class": CLS}))


class FiltroReporteForm(forms.Form):
    """Filtros opcionales; solo se muestran los que corresponden al reporte."""
    desde = forms.DateField(required=False, label="Desde",
                            widget=forms.DateInput(attrs={"type": "date", "class": CLS}, format="%Y-%m-%d"))
    hasta = forms.DateField(required=False, label="Hasta",
                            widget=forms.DateInput(attrs={"type": "date", "class": CLS}, format="%Y-%m-%d"))
    especie = _sel([("", "Todas")] + list(Mascota.Especie.choices), "Especie")
    estado = forms.ChoiceField(required=False, label="Estado", widget=forms.Select(attrs={"class": CLS}))
    veterinario = forms.ChoiceField(required=False, label="Veterinario", widget=forms.Select(attrs={"class": CLS}))
    categoria = _sel([("", "Todas")] + list(Insumo.Categoria.choices), "Categoría")
    tipo = _sel([("", "Todos")] + list(MovimientoInventario.Tipo.choices), "Tipo")

    ESTADOS = {
        "estado_mascota": [("", "Todas"), ("activas", "Solo activas"), ("inactivas", "Solo inactivas")],
        "estado_cita": [("", "Todos")] + list(Cita.Estado.choices),
        "estado_stock": [("", "Todos"), ("bajo", "Solo con stock bajo")],
        "retro": [("", "Todas")] + list(DiagnosticoIA.Retroalimentacion.choices),
    }
    CAMPOS = {
        "fechas": ["desde", "hasta"], "especie": ["especie"], "veterinario": ["veterinario"],
        "categoria": ["categoria"], "tipo_mov": ["tipo"],
        "estado_mascota": ["estado"], "estado_cita": ["estado"], "estado_stock": ["estado"], "retro": ["estado"],
    }

    def __init__(self, *args, filtros=(), **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields["veterinario"].choices = [("", "Todos")] + [
            (u.pk, u.get_full_name() or u.username)
            for u in User.objects.filter(perfil__rol="VET").order_by("first_name", "username")]
        usados = []
        for f in filtros:
            usados += self.CAMPOS[f]
            if f in self.ESTADOS:
                self.fields["estado"].choices = self.ESTADOS[f]
        for nombre in list(self.fields):
            if nombre not in usados:
                del self.fields[nombre]

    def clean(self):
        c = super().clean()
        if c.get("desde") and c.get("hasta") and c["desde"] > c["hasta"]:
            self.add_error("hasta", "La fecha final no puede ser anterior a la fecha inicial.")
        return c
