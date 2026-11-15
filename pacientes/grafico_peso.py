"""Datos para dibujar la curva de peso (SVG generado en el servidor, sin librerías externas)."""

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

ANCHO, ALTO = 600, 190
IZQ, DER, ARR, ABA = 44, 16, 14, 34  # márgenes del área de trazado


def fecha_corta(fecha):
    return f"{fecha.day} {MESES[fecha.month - 1]}"


def datos_grafico(pesos):
    """Recibe una lista de RegistroPeso ordenada por fecha y devuelve lo necesario
    para dibujar la curva, o None si hay menos de 2 mediciones."""
    if len(pesos) < 2:
        return None
    valores = [float(p.peso_kg) for p in pesos]
    minimo, maximo = min(valores), max(valores)
    margen = max((maximo - minimo) * 0.35, 0.5)
    bajo, alto = max(minimo - margen, 0), maximo + margen

    ordinales = [p.fecha.toordinal() for p in pesos]
    d0, d1 = ordinales[0], ordinales[-1]
    ancho_util = ANCHO - IZQ - DER
    alto_util = ALTO - ARR - ABA

    def x(o):
        return IZQ + (ancho_util * (o - d0) / (d1 - d0) if d1 != d0 else ancho_util / 2)

    def y(v):
        return ARR + alto_util * (1 - (v - bajo) / (alto - bajo))

    puntos = [{"x": round(x(o), 1), "y": round(y(v), 1), "peso": p.peso_kg, "fecha": p.fecha}
              for o, v, p in zip(ordinales, valores, pesos)]
    linea = " ".join(f"{pt['x']},{pt['y']}" for pt in puntos)
    area = f"{IZQ},{ALTO - ABA} {linea} {puntos[-1]['x']},{ALTO - ABA}"
    guias = []
    for v in (alto, (alto + bajo) / 2, bajo):
        guias.append({"y": round(y(v), 1), "etiqueta": f"{v:.1f}"})
    return {
        "ancho": ANCHO, "alto": ALTO, "izq": IZQ, "der": ANCHO - DER, "base": ALTO - ABA,
        "linea": linea, "area": area, "puntos": puntos, "guias": guias,
        "fecha_inicio": fecha_corta(pesos[0].fecha), "fecha_fin": fecha_corta(pesos[-1].fecha),
    }
