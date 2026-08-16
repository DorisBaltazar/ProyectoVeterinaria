from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class RolRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin para Class-Based Views que restringe el acceso según el rol
    del usuario autenticado. Se define 'roles_permitidos' en la vista
    hija, por ejemplo:

        class CitaDeleteView(RolRequeridoMixin, DeleteView):
            roles_permitidos = ["ADMIN"]
            ...
    """

    roles_permitidos = []
    # raise_exception=False (heredado de AccessMixin) ya da el comportamiento
    # correcto: usuario anónimo -> redirige a login; usuario autenticado sin
    # el rol correcto -> 403 Forbidden.

    def test_func(self):
        usuario = self.request.user
        if usuario.is_superuser:
            return True
        perfil = getattr(usuario, "perfil", None)
        if perfil is None:
            return False
        return perfil.rol in self.roles_permitidos
