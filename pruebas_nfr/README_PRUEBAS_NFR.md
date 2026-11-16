# Pruebas de sistema y de requerimientos no funcionales (RNF)

Todo se ejecuta sobre **tu copia local** (`http://127.0.0.1:8000`). No apuntes estas pruebas a un sitio ajeno.

| Prueba | Herramienta | RNF que verifica | Dónde |
|---|---|---|---|
| Unitarias, integración y RNF medibles en código | `manage.py test` | RNF-02, 03, 10, I1-05 | `usuarios/test_rnf.py` y demás `tests.py` |
| Análisis estático de calidad (sistema) | SonarQube | RNF-06 mantenibilidad | `sonar-project.properties` |
| Carga y rendimiento | Grafana k6 | RNF-03 (< 3 s), RNF-04 | `k6/carga.js` |
| Seguridad dinámica | OWASP ZAP | RNF-02 seguridad | sección 4 |

## 1. Pruebas automáticas y cobertura (PowerShell, en la raíz del proyecto)
```
pip install coverage
coverage run --source=. --omit="*/migrations/*,venv/*,manage.py" manage.py test
coverage report
coverage xml
```
Genera `coverage.xml` (lo usa SonarQube).

## 2. SonarQube
1. Instala **SonarQube Community** (descarga el zip de sonarsource.com, requiere Java 17, y ejecuta `bin\windows-x86-64\StartSonar.bat`) o con Docker: `docker run -d -p 9000:9000 sonarqube:community`.
2. Entra a `http://localhost:9000` (usuario `admin`, clave `admin`, te pedirá cambiarla). Crea un proyecto local con la clave `proyecto-veterinaria-ciac` y genera un **token**.
3. Instala **sonar-scanner** (CLI) y, en la raíz del proyecto:
```
copy pruebas_nfr\sonar-project.properties sonar-project.properties
sonar-scanner -Dsonar.host.url=http://localhost:9000 -Dsonar.token=TU_TOKEN
```
4. En el panel del proyecto toma captura de: **Quality Gate**, bugs, vulnerabilidades, *code smells*, duplicación y cobertura.

Alternativa rápida sin instalar servidor (resultados de análisis estático):
```
pip install bandit ruff
bandit -r config usuarios pacientes citas historiales inventario diagnostico reportes --exclude "*/tests.py,*/test_*.py"
ruff check . --exclude venv,migrations --select F,B,S --ignore S101
```

## 3. Carga con k6
Instala k6 (`winget install k6` o descarga de k6.io). Con el servidor corriendo (`python manage.py runserver`):
```
k6 run -e USUARIO=tu_usuario -e CLAVE=tu_clave -e PERFIL=humo   pruebas_nfr/k6/carga.js
k6 run -e USUARIO=tu_usuario -e CLAVE=tu_clave -e PERFIL=carga  pruebas_nfr/k6/carga.js
k6 run -e USUARIO=tu_usuario -e CLAVE=tu_clave -e PERFIL=estres pruebas_nfr/k6/carga.js
```
- `humo`: 1 usuario, comprueba que el flujo funciona. `carga`: hasta 20 usuarios simultáneos (la clínica atiende 3–6 pacientes por hora, así que es un escenario muy exigente). `estres`: hasta 80 usuarios, busca el punto de quiebre.
- Criterios (SLA): p95 < 3 s (RNF-03), promedio < 1 s, errores < 1 %. k6 marca ✓/✗ cada umbral.
- Usa un usuario ADMIN de prueba. Para resultados representativos ejecútalo con PostgreSQL y con algunos cientos de pacientes cargados.
- Copia los números a la tabla de `plantilla_informe_resultados.md`.

## 4. Seguridad con OWASP ZAP
1. Instala **ZAP** (zaproxy.org) y abre la sesión.
2. *Automated Scan* → URL `http://127.0.0.1:8000/` → *Attack*. (Es un análisis pasivo + activo sobre tu copia local.)
3. Para ver también las pantallas internas, haz primero *Manual Explore* iniciando sesión en el navegador de ZAP y navega por los módulos; luego ejecuta el ataque activo sobre el contexto.
4. *Report → Generate Report* (HTML) y guarda las alertas por nivel (Alto, Medio, Bajo).
5. En desarrollo (`DEBUG=True`) es normal ver alertas de cabeceras y cookies; documéntalas y anota qué se corrige en producción (`DEBUG=False`, HTTPS, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`).

## Alcance honesto de los resultados
Las pruebas se hicieron con datos de prueba y en un solo equipo; los números describen ese entorno, no una clínica en producción.
