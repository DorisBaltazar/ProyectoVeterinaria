"""Tipos de examen de laboratorio y variables que se ingresan en cada uno.

Solo se sugiere el nombre y la unidad de cada variable; el rango de referencia
lo escribe el personal según el laboratorio que emitió el resultado.
"""

CATALOGO = {
    "HEMOGRAMA": {
        "etiqueta": "Hemograma (sangre)",
        "variables": [
            ("Hematocrito", "%"),
            ("Hemoglobina", "g/dL"),
            ("Eritrocitos", "x10^6/µL"),
            ("Leucocitos", "x10^3/µL"),
            ("Plaquetas", "x10^3/µL"),
            ("Neutrófilos", "%"),
            ("Linfocitos", "%"),
        ],
    },
    "QUIMICA": {
        "etiqueta": "Química sanguínea",
        "variables": [
            ("Glucosa", "mg/dL"),
            ("Urea (BUN)", "mg/dL"),
            ("Creatinina", "mg/dL"),
            ("ALT (TGP)", "U/L"),
            ("Fosfatasa alcalina", "U/L"),
            ("Proteínas totales", "g/dL"),
            ("Albúmina", "g/dL"),
        ],
    },
    "ORINA": {
        "etiqueta": "Examen de orina",
        "variables": [
            ("Densidad urinaria", ""),
            ("pH urinario", ""),
        ],
    },
    "COPROPARASITARIO": {
        "etiqueta": "Coproparasitario (heces)",
        "variables": [
            ("Huevos por gramo (HPG)", "HPG"),
        ],
    },
    "EXAMEN_FISICO": {
        "etiqueta": "Examen físico / signos vitales",
        "variables": [
            ("Temperatura", "°C"),
            ("Hidratación", "%"),
            ("Frecuencia cardíaca", "lpm"),
            ("Frecuencia respiratoria", "rpm"),
        ],
    },
    "OTRO": {"etiqueta": "Otro examen", "variables": []},
}

TIPOS_CHOICES = [(k, v["etiqueta"]) for k, v in CATALOGO.items()]


def catalogo_para_js():
    """{tipo: [{nombre, unidad}, ...]} para autocompletar en el formulario."""
    return {
        k: [{"nombre": n, "unidad": u} for n, u in v["variables"]]
        for k, v in CATALOGO.items()
    }
