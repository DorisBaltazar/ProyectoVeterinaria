from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class UsuarioOCorreoBackend(ModelBackend):
    """Permite iniciar sesión con el nombre de usuario (sin distinguir
    mayúsculas) o con el correo electrónico, como indica el formulario de acceso."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None
        identificador = username.strip()
        candidatos = User.objects.filter(username__iexact=identificador)
        if not candidatos.exists() and "@" in identificador:
            candidatos = User.objects.filter(email__iexact=identificador)
        if candidatos.count() != 1:
            # sin coincidencia o correo repetido: no se adivina (y se mantiene el tiempo de respuesta)
            User().set_password(password)
            return None
        user = candidatos.get()
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
