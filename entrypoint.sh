#!/bin/sh
set -e

echo "Esperando a la base de datos ..."
python - <<'PY'
import os, time, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.db import connection
for _ in range(30):
    try:
        connection.ensure_connection()
        break
    except Exception:
        time.sleep(2)
else:
    raise SystemExit("No se pudo conectar a la base de datos")
PY

python manage.py migrate --noinput

# Crea el administrador la primera vez (en Render gratis no hay consola).
# Se activa solo si defines DJANGO_SUPERUSER_USERNAME y DJANGO_SUPERUSER_PASSWORD.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
python - <<'PY'
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
u = os.environ["DJANGO_SUPERUSER_USERNAME"]
if not User.objects.filter(username=u).exists():
    User.objects.create_superuser(u, os.environ.get("DJANGO_SUPERUSER_EMAIL", ""), os.environ["DJANGO_SUPERUSER_PASSWORD"])
    print("Administrador creado:", u)
else:
    print("El administrador ya existe:", u)
PY
fi

exec "$@"
