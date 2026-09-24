def registrar_bitacora(usuario, accion, detalle=""):
    """Helper para dejar constancia en la bitácora (RF-12) desde cualquier vista.

    Se importa perezosamente el modelo para evitar problemas de import
    circular entre apps (usuarios <-> citas/pacientes).
    """
    from .models import Bitacora

    Bitacora.objects.create(usuario=usuario, accion=accion, detalle=detalle[:255])