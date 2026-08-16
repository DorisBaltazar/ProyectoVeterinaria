from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def rol_requerido(*roles_permitidos):
    """
    Decorador para restringir el acceso a una vista según el rol del
    usuario (Administrador, Veterinario, Recepcionista).

    Uso:
        @rol_requerido("ADMIN", "VET")
        def mi_vista(request):
            ...

    Cumple con lo definido en el Alcance (3.4): las funciones del
    Módulo de Aprendizaje Automático y el diagnóstico quedan
    completamente bloqueadas para el rol Recepcionista.
    """

    def decorador(vista):
        @wraps(vista)
        @login_required
        def _envoltura(request, *args, **kwargs):
            perfil = getattr(request.user, "perfil", None)
            if request.user.is_superuser:
                return vista(request, *args, **kwargs)
            if perfil is None or perfil.rol not in roles_permitidos:
                raise PermissionDenied(
                    "No tienes permisos para acceder a esta sección."
                )
            return vista(request, *args, **kwargs)

        return _envoltura

    return decorador