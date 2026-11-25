#!/bin/sh
set -e

echo "Esperando a la base de datos en $DB_HOST:$DB_PORT ..."
python - <<'PY'
import os, time, psycopg
for _ in range(30):
    try:
        psycopg.connect(
            dbname=os.environ["DB_NAME"], user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"], host=os.environ["DB_HOST"],
            port=os.environ.get("DB_PORT", "5432"), connect_timeout=3,
        ).close()
        break
    except Exception:
        time.sleep(2)
else:
    raise SystemExit("No se pudo conectar a la base de datos")
PY

python manage.py migrate --noinput
exec "$@"
