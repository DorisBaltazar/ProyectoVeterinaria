
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
            name='Perfil',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rol', models.CharField(choices=[('ADMIN', 'Administrador'), ('VET', 'Veterinario'), ('RECEP', 'Recepcionista')], default='RECEP', max_length=10)),
                ('telefono', models.CharField(blank=True, max_length=20)),
                ('usuario', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='perfil', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Perfil de usuario',
                'verbose_name_plural': 'Perfiles de usuario',
            },
        ),
    ]
