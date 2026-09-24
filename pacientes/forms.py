from django import forms

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


class MascotaForm(forms.ModelForm):
    class Meta:
        model = Mascota
        fields = [
            "propietario", "nombre", "especie", "raza", "sexo",
            "fecha_nacimiento", "peso_kg", "foto", "notas",
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
            "fecha_nacimiento": forms.DateInput(attrs={
                "class": "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20",
                "type": "date",
            }),
            "peso_kg": forms.NumberInput(attrs={
                "class": "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20",
                "step": "0.01", "placeholder": "Peso en kg",
            }),
            "notas": forms.Textarea(attrs={
                "class": "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20",
                "rows": 3,
            }),
        }

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")
        if foto and hasattr(foto, "size") and foto.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La imagen no puede superar los 5 MB.")
        return foto