"""Validadores reutilizables: rechazan valores negativos o fuera de rango
clínicamente posible, tanto en formularios como en el panel admin."""
import re
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator

PESO_MAX_KG = Decimal("200")


def positivo(minimo="0.01"):
    return MinValueValidator(Decimal(minimo), message="El valor debe ser mayor que cero.")


def no_negativo():
    return MinValueValidator(Decimal("0"), message="El valor no puede ser negativo.")


def peso_validators():
    return [positivo("0.01"), MaxValueValidator(PESO_MAX_KG, message="El peso máximo permitido es 200 kg.")]


def temperatura_validators():
    return [MinValueValidator(Decimal("30"), message="La temperatura debe estar entre 30 y 45 °C."),
            MaxValueValidator(Decimal("45"), message="La temperatura debe estar entre 30 y 45 °C.")]


def telefono_valido(valor):
    if valor and (not re.fullmatch(r"[0-9+\-\s()]+", valor) or len(re.sub(r"\D", "", valor)) < 7):
        raise ValidationError("Ingresa un teléfono válido (solo números, mínimo 7 dígitos).")


class LimitesHtmlMixin:
    """Copia los validadores de mínimo/máximo de cada campo numérico a los
    atributos min/max del <input>, para que el navegador también avise."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        modelo = getattr(getattr(self, "_meta", None), "model", None)
        for nombre, campo in self.fields.items():
            if not isinstance(campo.widget, forms.NumberInput):
                continue
            validadores = list(campo.validators)
            if modelo is not None:
                try:
                    validadores += modelo._meta.get_field(nombre).validators
                except Exception:
                    pass
            for v in validadores:
                if isinstance(v, MinValueValidator):
                    campo.widget.attrs.setdefault("min", str(v.limit_value))
                elif isinstance(v, MaxValueValidator):
                    campo.widget.attrs.setdefault("max", str(v.limit_value))
