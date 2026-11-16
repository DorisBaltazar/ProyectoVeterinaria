# Informe de resultados de pruebas no funcionales — Clínica CIAC

Entorno: equipo ____ (CPU/RAM) · Django 6.0.7 · PostgreSQL ____ · fecha ____
Escenario k6: usuarios concurrentes ____ · duración ____ · solicitudes/seg promedio ____

| Métrica clave | Valor obtenido | Objetivo (SLA) | Estado | Diagnóstico / observación |
|---|---|---|---|---|
| Tiempo de respuesta (promedio) | | < 1000 ms | | |
| Percentil 95 (p95) | | < 3000 ms (RNF-03) | | |
| Tasa de errores HTTP | | < 1 % | | |
| Cumplimiento de checks | | > 99 % | | |
| Alertas ZAP nivel Alto | | 0 | | |
| Alertas ZAP nivel Medio | | documentadas | | |
| SonarQube: Quality Gate | | Passed | | |
| SonarQube: cobertura | | ≥ 80 % | | |
| SonarQube: bugs / vulnerabilidades | | 0 / 0 | | |

Hallazgos y correcciones aplicadas: ____
