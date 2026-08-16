from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Perfil


@receiver(post_save, sender=User)
def crear_o_actualizar_perfil(sender, instance, created, **kwargs):
    """Crea automáticamente un Perfil (rol Recepcionista por defecto)
    cada vez que se crea un nuevo usuario, para que el sistema nunca
    tenga un User sin rol asignado."""
    if created:
        Perfil.objects.create(usuario=instance)
    else:
        Perfil.objects.get_or_create(usuario=instance)
