import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Cita',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('propietario_nombre', models.CharField(max_length=120, verbose_name='Nombre del propietario')),
                ('propietario_telefono', models.CharField(blank=True, max_length=20, verbose_name='Teléfono')),
                ('mascota_nombre', models.CharField(max_length=80, verbose_name='Nombre de la mascota')),
                ('especie', models.CharField(choices=[('PERRO', 'Perro'), ('GATO', 'Gato'), ('OTRO', 'Otro')], default='PERRO', max_length=10)),
                ('fecha', models.DateField(verbose_name='Fecha de la cita')),
                ('hora', models.TimeField(verbose_name='Hora de la cita')),
                ('motivo', models.CharField(max_length=255, verbose_name='Motivo de consulta')),
                ('estado', models.CharField(choices=[('PENDIENTE', 'Pendiente'), ('CONFIRMADA', 'Confirmada'), ('ATENDIDA', 'Atendida'), ('CANCELADA', 'Cancelada')], default='PENDIENTE', max_length=12)),
                ('observaciones', models.TextField(blank=True)),
                ('fecha_registro', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                ('creado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='citas_creadas', to=settings.AUTH_USER_MODEL)),
                ('veterinario', models.ForeignKey(blank=True, limit_choices_to={'perfil__rol': 'VET'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='citas_asignadas', to=settings.AUTH_USER_MODEL, verbose_name='Veterinario asignado')),
            ],
            options={
                'verbose_name': 'Cita',
                'verbose_name_plural': 'Citas',
                'ordering': ['fecha', 'hora'],
            },
        ),
    ]
