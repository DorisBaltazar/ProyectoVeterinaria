"""
Servicio de inferencia síncrona en memoria (sección II.C.3 del documento:
"Flujo de inferencia asistida"). El artefacto .joblib se carga una sola vez
en memoria del proceso del servidor (patrón singleton a nivel de módulo),
evitando el costo de deserializar el modelo en cada solicitud y manteniendo
tiempos de latencia mínimos acordes a una inferencia síncrona in-process.
"""
import os
import threading

import joblib
import pandas as pd

_MODELO_PATH = os.path.join(os.path.dirname(__file__), "modelo_diagnostico_ciac.joblib")

_lock = threading.Lock()
_artefacto = None


def _cargar_artefacto():
    global _artefacto
    if _artefacto is None:
        with _lock:
            if _artefacto is None:  # doble verificación (thread-safe)
                _artefacto = joblib.load(_MODELO_PATH)
    return _artefacto


def predecir(datos: dict) -> dict:
    """Ejecuta la inferencia sobre un diccionario de entrada con las claves
    de especie, variables numéricas y síntomas (ver DiagnosticoForm).

    Devuelve: {"prediccion": str, "confianza": float, "probabilidades": {clase: prob, ...}}
    """
    artefacto = _cargar_artefacto()
    pipeline = artefacto["pipeline"]
    le = artefacto["label_encoder"]
    columnas = artefacto["columnas_categoricas"] + artefacto["columnas_numericas"] + artefacto["columnas_sintomas"]

    fila = {col: datos[col] for col in columnas}
    X = pd.DataFrame([fila])

    proba = pipeline.predict_proba(X)[0]
    clases = le.classes_
    distribucion = {clase: round(float(p) * 100, 2) for clase, p in zip(clases, proba)}
    distribucion = dict(sorted(distribucion.items(), key=lambda kv: kv[1], reverse=True))

    clase_predicha = max(distribucion, key=distribucion.get)
    confianza = distribucion[clase_predicha]

    return {
        "prediccion": clase_predicha,
        "confianza": confianza,
        "probabilidades": distribucion,
    }
