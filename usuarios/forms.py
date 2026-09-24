from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

from .models import Perfil

INPUT = "w-full bg-transparent border-none focus:ring-0 text-on-surface font-medium placeholder:text-slate-400"
SELECT = "w-full bg-surface-container-highest border-none rounded-xl p-3 focus:ring-2 focus:ring-primary/20"


class LoginForm(AuthenticationForm):
    """AuthenticationForm con estilo Tailwind acorde al diseño de Clínica CIAC."""

    username = forms.CharField(widget=forms.TextInput(attrs={
        "class": INPUT, "placeholder": "Usuario o correo", "autofocus": True,
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": INPUT, "placeholder": "Contraseña",
    }))


class UsuarioCreateForm(forms.ModelForm):
    """RF-11: el administrador crea usuarios del sistema y les asigna un rol."""

    password1 = forms.CharField(
        label="Contraseña", widget=forms.PasswordInput(attrs={"class": SELECT})
    )
    password2 = forms.CharField(
        label="Confirmar contraseña", widget=forms.PasswordInput(attrs={"class": SELECT})
    )
    rol = forms.ChoiceField(choices=Perfil.Rol.choices, widget=forms.Select(attrs={"class": SELECT}))

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]
        widgets = {
            "username": forms.TextInput(attrs={"class": SELECT, "placeholder": "Usuario (para iniciar sesión)"}),
            "first_name": forms.TextInput(attrs={"class": SELECT, "placeholder": "Nombres"}),
            "last_name": forms.TextInput(attrs={"class": SELECT, "placeholder": "Apellidos"}),
            "email": forms.EmailInput(attrs={"class": SELECT, "placeholder": "Correo electrónico"}),
        }

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ya existe un usuario con ese nombre de usuario.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            user.perfil.rol = self.cleaned_data["rol"]
            user.perfil.save()
        return user


class UsuarioUpdateForm(forms.ModelForm):
    """Editar datos y rol de un usuario existente (sin tocar la contraseña)."""

    rol = forms.ChoiceField(choices=Perfil.Rol.choices, widget=forms.Select(attrs={"class": SELECT}))

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "is_active"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": SELECT, "placeholder": "Nombres"}),
            "last_name": forms.TextInput(attrs={"class": SELECT, "placeholder": "Apellidos"}),
            "email": forms.EmailInput(attrs={"class": SELECT, "placeholder": "Correo electrónico"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["rol"].initial = getattr(self.instance.perfil, "rol", None)

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.perfil.rol = self.cleaned_data["rol"]
            user.perfil.save()
        return user
