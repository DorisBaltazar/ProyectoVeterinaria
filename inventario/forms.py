from django import forms

from .models import Insumo, MovimientoInventario

INPUT = "w-full bg-transparent border-none focus:ring-0 text-on-surface font-medium placeholder:text-slate-400"
SELECT = "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20"


class InsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = ["nombre", "categoria", "unidad_medida", "stock_minimo", "precio_unitario", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": INPUT, "placeholder": "Nombre del insumo"}),
            "categoria": forms.Select(attrs={"class": SELECT}),
            "unidad_medida": forms.TextInput(attrs={"class": INPUT, "placeholder": "Ej: unidad, ml, caja"}),
            "stock_minimo": forms.NumberInput(attrs={"class": SELECT, "step": "0.01"}),
            "precio_unitario": forms.NumberInput(attrs={"class": SELECT, "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            del self.fields["activo"]


class MovimientoInventarioForm(forms.ModelForm):
    class Meta:
        model = MovimientoInventario
        fields = ["insumo", "tipo", "cantidad", "motivo"]
        widgets = {
            "insumo": forms.Select(attrs={"class": SELECT}),
            "tipo": forms.Select(attrs={"class": SELECT}),
            "cantidad": forms.NumberInput(attrs={"class": SELECT, "step": "0.01", "min": "0.01"}),
            "motivo": forms.TextInput(attrs={"class": INPUT, "placeholder": "Ej: Compra a proveedor, Uso en consulta"}),
        }

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")
        cantidad = cleaned.get("cantidad")
        insumo = cleaned.get("insumo")
        if tipo == MovimientoInventario.Tipo.SALIDA and insumo and cantidad:
            if cantidad > insumo.stock_actual:
                raise forms.ValidationError(
                    f"Stock insuficiente: solo hay {insumo.stock_actual} {insumo.unidad_medida} de {insumo.nombre}."
                )
        return cleaned