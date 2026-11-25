# ProyectoVeterinaria
# Sistema Web Clínico Veterinario

Sistema web de gestión para una clínica veterinaria, con un módulo de aprendizaje automático que **sugiere** diagnósticos al veterinario. Proyecto de grado: *Sistema Web Clínico Veterinario con Módulo de Aprendizaje Automático para Apoyo al Diagnóstico*.

## Qué hace

| Módulo (app Django) | Funcionalidad |
| --- | --- |
| `usuarios` | Inicio de sesión (con usuario o correo), 3 roles, bitácora de acciones |
| `pacientes` | Propietarios y mascotas, CI única, gráfico de peso |
| `citas` | Programar, asignar veterinario y cambiar el estado de las citas |
| `historiales` | Consultas, resultados de laboratorio, receta digital y línea de tiempo |
| `inventario` | Entradas y salidas de insumos, descuento automático y alerta de stock bajo |
| `diagnostico` | Sugerencia de diagnóstico con Random Forest y retroalimentación del veterinario |
| `reportes` | Reportes de atenciones e inventario, con impresión y exportación |

## Roles

| Rol | Acceso |
| --- | --- |
| Recepcionista | Propietarios, mascotas y citas |
| Veterinario | Consultas, historiales, laboratorio y diagnóstico con IA |
| Administrador | Usuarios, inventario, bitácora y reportes |

El diagnóstico con IA es exclusivo del rol Veterinario (y del superusuario técnico de Django). El control de acceso se hace en el servidor, con `RolRequeridoMixin` y `@rol_requerido`.

## Tecnologías

- **Backend:** Python, Django 6.0.7 (patrón MVT, vistas basadas en clases)
- **Base de datos:** PostgreSQL
- **Frontend:** plantillas de Django, HTML5, Tailwind CSS
- **IA:** scikit-learn (Random Forest), Pandas, joblib
- **Producción:** gunicorn, WhiteNoise, Docker
- **Calidad:** pruebas con `manage.py test`, SonarQube, k6

## Arquitectura

Monolito modular en capas: un solo proceso Django con 7 apps, PostgreSQL como base de datos y el modelo de IA cargado una sola vez en memoria.

```
Navegador -> Views/Forms (rol) -> Servicio de inferencia -> Pandas -> Random Forest
                 |                                                          |
                 +--------------- ORM / Models -> PostgreSQL <--------------+
                 |
              Templates -> Navegador
```

## Estructura del proyecto

```
config/          configuración de Django (settings, urls, wsgi)
usuarios/        autenticación, roles, bitácora
pacientes/       propietarios y mascotas
citas/           agenda de citas
historiales/     historial clínico y laboratorio
inventario/      insumos y movimientos
diagnostico/     módulo de IA (ml/ contiene el modelo y la inferencia)
reportes/        reportes y estadísticas
templates/       plantillas HTML
static/          archivos estáticos
pruebas_nfr/     pruebas de carga (k6) y de requerimientos no funcionales
```

## Instalación local

Requisitos: Python 3.13 o superior y PostgreSQL.

```bash
git clone https://github.com/DorisBaltazar/ProyectoVeterinaria.git
cd ProyectoVeterinaria

python -m venv venv
# Windows (PowerShell): venv\Scripts\Activate.ps1
# Linux o Mac:          source venv/bin/activate

pip install -r requirements.txt
```

Crea un archivo `.env` en la raíz con tus datos (no se sube a Git):

```
DEBUG=True
SECRET_KEY=pon-aqui-una-clave-larga-y-secreta
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=ciac_db
DB_USER=postgres
DB_PASSWORD=tu_clave
DB_HOST=localhost
DB_PORT=5432
```

Crea la base de datos `ciac_db` en PostgreSQL y luego:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abre `http://127.0.0.1:8000`. Desde el módulo **Usuarios** (como administrador) crea los usuarios con rol Veterinario y Recepcionista.

## Ejecutar con Docker

Requisitos: Docker Desktop.

1. Crea el archivo `.env` (ejemplo para Docker):

```
DEBUG=False
SECRET_KEY=pon-aqui-una-clave-larga-y-secreta
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
DB_NAME=ciac_db
DB_USER=postgres
DB_PASSWORD=tu_clave
```

2. Construye y levanta los contenedores (aplicación y PostgreSQL):

```bash
docker compose up --build -d
```

3. Crea el usuario administrador:

```bash
docker compose exec web python manage.py createsuperuser
```

4. Abre `http://localhost:8000`.

Las migraciones se aplican solas al arrancar. Comandos útiles:

```bash
docker compose logs -f web     # ver mensajes
docker compose down            # apagar (conserva los datos)
docker compose down -v         # apagar y borrar la base de datos
```

## Pruebas

```bash
python manage.py test
```

El proyecto incluye pruebas unitarias, de integración y de aceptación. Para medir cobertura:

```bash
pip install coverage
coverage run --source=. --omit="*/migrations/*,venv/*,manage.py" manage.py test
coverage report
```

Las pruebas de carga (k6) y de requerimientos no funcionales están en `pruebas_nfr/`. Ejecútalas solo contra tu copia local.

## Módulo de IA: alcance y límites

- Modelo: Random Forest (300 árboles) que recibe 22 datos clínicos y devuelve la probabilidad de 6 enfermedades.
- El modelo entrenado está en `diagnostico/ml/` y se carga una sola vez en memoria.
- **El sistema solo sugiere:** el diagnóstico final lo decide el veterinario.
- **Los datos de entrenamiento son 900 casos de demostración, con perfiles clínicos definidos por la autora; no son pacientes reales.** Las métricas (F1 macro de 0,87 a 0,90) muestran viabilidad técnica, no exactitud clínica. Con datos reales de la clínica, el modelo debe reentrenarse.

## Variables de entorno

| Variable | Para qué sirve |
| --- | --- |
| `SECRET_KEY` | Clave interna de Django |
| `DEBUG` | `True` solo en desarrollo |
| `ALLOWED_HOSTS` | Direcciones desde las que se puede abrir el sistema |
| `CSRF_TRUSTED_ORIGINS` | Orígenes confiables para formularios (necesario con HTTPS o Docker) |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Conexión a PostgreSQL |

## Autora

Doris Neyza Baltazar Torrez. Tutor: Ing. Víctor Hugo Sarzuri.
