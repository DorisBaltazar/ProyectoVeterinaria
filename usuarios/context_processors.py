def perfil(request):
    """
    Context processor que expone 'perfil' en TODAS las plantillas
    (no solo en las vistas de usuarios), para poder mostrar/ocultar
    botones según el rol (RBAC) desde cualquier template, p. ej.
    citas/cita_list.html.
    """
    if request.user.is_authenticated:
        return {"perfil": getattr(request.user, "perfil", None)}
    return {}
