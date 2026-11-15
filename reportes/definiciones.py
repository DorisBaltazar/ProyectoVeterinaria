"""Catálogo de reportes exportables de la clínica.

Cada reporte devuelve un diccionario con columnas, filas y un resumen, de
modo que la misma información se puede ver en pantalla, imprimir/guardar
como PDF y exportar a CSV (abre directo en Excel)."""
from datetime import date, datetime, time

from django.contrib.auth import get_user_model
from django.db.models import Count, F, Sum
from django.utils import timezone

from citas.models import Cita
from diagnostico.models import DiagnosticoIA
from historiales.models import HistorialClinico
from inventario.models import Insumo, MovimientoInventario
from pacientes.models import Mascota

ADMIN, VET, RECEP = "ADMIN", "VET", "RECEP"

PALETA = ["#0e7c7b", "#2fa4a2", "#f2a900", "#e4572e", "#6c5ce7", "#4a6267", "#8fd3d1", "#b0b8b8"]


def _contar(valores, top=None):
    """[(etiqueta, cantidad)] ordenado de mayor a menor."""
    conteo = {}
    for v in valores:
        v = v if v not in (None, "") else "Sin dato"
        conteo[v] = conteo.get(v, 0) + 1
    orden = sorted(conteo.items(), key=lambda kv: (-kv[1], str(kv[0])))
    return orden[:top] if top else orden


def _por_mes(fechas, maximo=12):
    conteo = {}
    for f in fechas:
        if f:
            clave = f.strftime("%Y-%m")
            conteo[clave] = conteo.get(clave, 0) + 1
    claves = sorted(conteo)[-maximo:]
    return [(f"{k[5:]}/{k[:4]}", conteo[k]) for k in claves]


def grafico(titulo, datos, tipo="barras", unidad=""):
    """Datos listos para dibujar: barras horizontales o dona (conic-gradient)."""
    datos = [(str(e), v) for e, v in datos if v]
    if not datos:
        return None
    total = sum(float(v) for _, v in datos) or 1
    maximo = max(float(v) for _, v in datos) or 1
    items, acumulado, trozos = [], 0.0, []
    for i, (e, v) in enumerate(datos):
        color = PALETA[i % len(PALETA)] if tipo == "dona" else PALETA[0]
        pct = float(v) / total * 100
        items.append({"etiqueta": e, "valor": v, "color": color, "pct_total": round(pct, 1),
                      "ancho": round(float(v) / maximo * 100, 1)})
        trozos.append(f"{color} {acumulado:.2f}% {acumulado + pct:.2f}%")
        acumulado += pct
    return {"titulo": titulo, "tipo": tipo, "items": items, "unidad": unidad,
            "gradiente": "conic-gradient(" + ", ".join(trozos) + ")", "total": round(total, 2) if unidad else int(total)}


def _dt(d, fin=False):
    """Convierte una fecha en datetime con zona horaria (inicio o fin del día)."""
    return timezone.make_aware(datetime.combine(d, time.max if fin else time.min))


def _fmt(d):
    return d.strftime("%d/%m/%Y") if d else ""


def _fmt_dt(d):
    return timezone.localtime(d).strftime("%d/%m/%Y %H:%M") if d else ""


def _nombre(u):
    return (u.get_full_name() or u.username) if u else ""


def _rango(f):
    return f.get("desde"), f.get("hasta")


# ------------------------------------------------------------------ pacientes
def rep_pacientes(f):
    qs = Mascota.objects.select_related("propietario").annotate(n_consultas=Count("historiales"))
    if f.get("especie"):
        qs = qs.filter(especie=f["especie"])
    if f.get("estado") == "activas":
        qs = qs.filter(activo=True)
    elif f.get("estado") == "inactivas":
        qs = qs.filter(activo=False)
    filas = []
    for m in qs.order_by("nombre"):
        ultima = m.historiales.order_by("-fecha_atencion").first()
        filas.append([
            m.codigo, m.nombre, m.get_especie_display(), m.raza, m.get_sexo_display(),
            m.edad_texto or "", m.peso_actual if m.peso_actual is not None else "",
            m.propietario.nombre_completo, m.propietario.ci, m.propietario.telefono,
            m.alerta_medica, m.n_consultas, _fmt_dt(ultima.fecha_atencion) if ultima else "",
            "Sí" if m.activo else "No",
        ])
    total = len(filas)
    con_alerta = sum(1 for r in filas if r[10])
    def _rango_edad(txt):
        return txt
    edades = []
    for m in qs:
        meses = m.edad_en_meses
        edades.append("Sin dato" if meses is None else "Menos de 1 año" if meses < 12 else
                      "1 a 3 años" if meses < 48 else "4 a 7 años" if meses < 96 else "8 años o más")
    graficos = [
        grafico("Pacientes por especie", _contar(r[2] for r in filas), "dona"),
        grafico("Pacientes por sexo", _contar(r[4] for r in filas), "dona"),
        grafico("Pacientes por rango de edad", _contar(edades)),
        grafico("Razas más frecuentes", _contar((r[3] for r in filas), top=6)),
        grafico("Registros nuevos por mes", _por_mes(m.fecha_registro for m in qs)),
    ]
    por_especie = {}
    for r in filas:
        por_especie[r[2]] = por_especie.get(r[2], 0) + 1
    return {
        "columnas": ["Código", "Mascota", "Especie", "Raza", "Sexo", "Edad", "Peso (kg)", "Propietario",
                     "CI", "Teléfono", "Alerta médica", "Nº consultas", "Última atención", "Activa"],
        "filas": filas, "graficos": [g for g in graficos if g],
        "resumen": [("Total de pacientes", total), ("Con alerta médica", con_alerta)]
                   + [(f"Especie: {k}", v) for k, v in por_especie.items()],
    }


# ---------------------------------------------------------------------- citas
def rep_citas(f):
    qs = Cita.objects.select_related("veterinario")
    desde, hasta = _rango(f)
    if desde:
        qs = qs.filter(fecha__gte=desde)
    if hasta:
        qs = qs.filter(fecha__lte=hasta)
    if f.get("estado"):
        qs = qs.filter(estado=f["estado"])
    qs = qs.order_by("fecha", "hora")
    filas = [[_fmt(c.fecha), c.hora.strftime("%H:%M"), c.propietario_nombre, c.propietario_telefono,
              c.mascota_nombre, c.get_especie_display(), c.motivo, _nombre(c.veterinario),
              c.get_estado_display()] for c in qs]
    por_estado = {}
    for r in filas:
        por_estado[r[8]] = por_estado.get(r[8], 0) + 1
    atendidas = por_estado.get("Atendida", 0)
    canceladas = por_estado.get("Cancelada", 0)
    graficos = [
        grafico("Citas por estado", _contar(r[8] for r in filas), "dona"),
        grafico("Citas por mes", _por_mes(c.fecha for c in qs)),
        grafico("Citas por veterinario", _contar((r[7] or "Sin asignar") for r in filas)),
        grafico("Motivos más frecuentes", _contar((r[6] for r in filas), top=6)),
    ]
    return {"graficos": [g for g in graficos if g],
        "columnas": ["Fecha", "Hora", "Propietario", "Teléfono", "Mascota", "Especie", "Motivo",
                     "Veterinario", "Estado"],
        "filas": filas,
        "resumen": [("Total de citas", len(filas))] + [(f"Estado: {k}", v) for k, v in por_estado.items()]
                   + ([("% canceladas", f"{canceladas / len(filas) * 100:.1f}%")] if filas else []),
    }


# ----------------------------------------------------------------- atenciones
def rep_atenciones(f):
    qs = HistorialClinico.objects.select_related("mascota__propietario", "veterinario")
    desde, hasta = _rango(f)
    if desde:
        qs = qs.filter(fecha_atencion__gte=_dt(desde))
    if hasta:
        qs = qs.filter(fecha_atencion__lte=_dt(hasta, fin=True))
    if f.get("veterinario"):
        qs = qs.filter(veterinario_id=f["veterinario"])
    filas = [[_fmt_dt(h.fecha_atencion), h.mascota.codigo, h.mascota.nombre,
              h.mascota.propietario.nombre_completo, h.get_tipo_atencion_display(), h.motivo,
              h.diagnostico, h.tratamiento, h.peso_kg if h.peso_kg is not None else "",
              _nombre(h.veterinario)] for h in qs.order_by("-fecha_atencion")]
    por_vet = {}
    for r in filas:
        por_vet[r[9] or "Sin asignar"] = por_vet.get(r[9] or "Sin asignar", 0) + 1
    graficos = [
        grafico("Atenciones por veterinario", _contar((r[9] or "Sin asignar") for r in filas), "dona"),
        grafico("Consulta vs. control", _contar(r[4] for r in filas), "dona"),
        grafico("Atenciones por mes", _por_mes(h.fecha_atencion for h in qs)),
        grafico("Diagnósticos más frecuentes", _contar((r[6].strip().capitalize()[:40] for r in filas), top=6)),
    ]
    return {"graficos": [g for g in graficos if g],
        "columnas": ["Fecha y hora", "Código", "Mascota", "Propietario", "Tipo", "Motivo", "Diagnóstico",
                     "Tratamiento", "Peso (kg)", "Veterinario"],
        "filas": filas,
        "resumen": [("Total de atenciones", len(filas))] + [(f"Atendidas por {k}", v) for k, v in por_vet.items()],
    }


# ----------------------------------------------------------------- inventario
def rep_inventario(f):
    qs = Insumo.objects.filter(activo=True)
    if f.get("categoria"):
        qs = qs.filter(categoria=f["categoria"])
    if f.get("estado") == "bajo":
        qs = qs.filter(stock_actual__lte=F("stock_minimo"))
    filas, valor = [], 0
    bajos = 0
    for i in qs.order_by("nombre"):
        precio = i.precio_unitario
        subtotal = (precio * i.stock_actual) if precio is not None else None
        valor += subtotal or 0
        bajos += 1 if i.stock_bajo else 0
        filas.append([i.nombre, i.get_categoria_display(), i.unidad_medida, i.stock_actual, i.stock_minimo,
                      "Stock bajo" if i.stock_bajo else "Normal",
                      precio if precio is not None else "", subtotal if subtotal is not None else ""])
    graficos = [
        grafico("Insumos por categoría", _contar(r[1] for r in filas), "dona"),
        grafico("Estado del stock", _contar(r[5] for r in filas), "dona"),
        grafico("Valor en stock por categoría (Bs)",
                [(k, round(sum(float(r[7] or 0) for r in filas if r[1] == k), 2)) for k, _ in _contar(r[1] for r in filas)],
                unidad="Bs"),
        grafico("Insumos con menos stock respecto al mínimo",
                [(r[0], round(float(r[3]) / float(r[4]) * 100) if float(r[4]) else 0)
                 for r in sorted(filas, key=lambda r: (float(r[3]) / float(r[4])) if float(r[4]) else 9e9)[:6] if float(r[4])],
                unidad="% del mínimo"),
    ]
    return {"graficos": [g for g in graficos if g],
        "columnas": ["Insumo", "Categoría", "Unidad", "Stock actual", "Stock mínimo", "Estado",
                     "Precio unit. (Bs)", "Valor en stock (Bs)"],
        "filas": filas,
        "resumen": [("Total de insumos", len(filas)), ("Con stock bajo", bajos),
                    ("Valor del inventario (Bs)", f"{valor:.2f}")],
    }


def rep_movimientos(f):
    qs = MovimientoInventario.objects.select_related("insumo", "usuario")
    desde, hasta = _rango(f)
    if desde:
        qs = qs.filter(fecha__gte=_dt(desde))
    if hasta:
        qs = qs.filter(fecha__lte=_dt(hasta, fin=True))
    if f.get("tipo"):
        qs = qs.filter(tipo=f["tipo"])
    filas = [[_fmt_dt(m.fecha), m.insumo.nombre, m.get_tipo_display(), m.cantidad, m.insumo.unidad_medida,
              m.motivo, _nombre(m.usuario)] for m in qs.order_by("-fecha")]
    ent = qs.filter(tipo="ENTRADA").aggregate(t=Sum("cantidad"))["t"] or 0
    sal = qs.filter(tipo="SALIDA").aggregate(t=Sum("cantidad"))["t"] or 0
    graficos = [
        grafico("Entradas vs. salidas (nº de movimientos)", _contar(r[2] for r in filas), "dona"),
        grafico("Movimientos por mes", _por_mes(m.fecha for m in qs)),
        grafico("Insumos con más salidas", _contar((r[1] for r in filas if r[2] == "Salida"), top=6)),
        grafico("Motivos más frecuentes", _contar((r[5] for r in filas), top=6)),
    ]
    return {"graficos": [g for g in graficos if g],
        "columnas": ["Fecha y hora", "Insumo", "Tipo", "Cantidad", "Unidad", "Motivo", "Registrado por"],
        "filas": filas,
        "resumen": [("Total de movimientos", len(filas)), ("Unidades que entraron", ent),
                    ("Unidades que salieron", sal)],
    }


# ------------------------------------------------------------------------- IA
def rep_ia(f):
    qs = DiagnosticoIA.objects.select_related("mascota", "veterinario")
    desde, hasta = _rango(f)
    if desde:
        qs = qs.filter(fecha__gte=_dt(desde))
    if hasta:
        qs = qs.filter(fecha__lte=_dt(hasta, fin=True))
    if f.get("estado"):
        qs = qs.filter(retroalimentacion=f["estado"])
    filas = [[_fmt_dt(d.fecha), d.mascota.codigo, d.mascota.nombre, _nombre(d.veterinario), d.prediccion,
              f"{d.confianza}%", d.get_retroalimentacion_display(), d.diagnostico_real or ""]
             for d in qs.order_by("-fecha")]
    conf = sum(1 for d in qs if d.retroalimentacion == "CONFIRMADO")
    corr = sum(1 for d in qs if d.retroalimentacion == "CORREGIDO")
    confs = [float(d.confianza) for d in qs]
    graficos = [
        grafico("Diagnósticos sugeridos", _contar((r[4] for r in filas), top=8)),
        grafico("Retroalimentación del veterinario", _contar(r[6] for r in filas), "dona"),
        grafico("Diagnósticos por mes", _por_mes(d.fecha for d in qs)),
    ]
    return {"graficos": [g for g in graficos if g],
        "columnas": ["Fecha y hora", "Código", "Mascota", "Veterinario", "Diagnóstico sugerido", "Confianza",
                     "Retroalimentación", "Diagnóstico real"],
        "filas": filas,
        "resumen": [("Total de diagnósticos IA", len(filas)), ("Confirmados", conf), ("Corregidos", corr),
                    ("Confianza promedio", f"{sum(confs) / len(confs):.1f}%" if confs else "—"),
                    ("Precisión percibida", f"{conf / (conf + corr) * 100:.1f}%" if (conf + corr) else "—")],
    }


ESTADOS_CITA = [("", "Todos")] + list(Cita.Estado.choices)
ESPECIES = [("", "Todas")] + list(Mascota.Especie.choices)

# clave -> definición. 'filtros' lista los campos del formulario de filtros.
REPORTES = {
    "pacientes": {
        "titulo": "Listado de pacientes", "icono": "pets", "roles": [ADMIN, VET, RECEP],
        "descripcion": "Mascotas registradas con su propietario, edad, peso actual, alerta médica y última atención.",
        "filtros": ["especie", "estado_mascota"], "func": rep_pacientes,
    },
    "citas": {
        "titulo": "Agenda de citas", "icono": "calendar_month", "roles": [ADMIN, VET, RECEP],
        "descripcion": "Citas del período con su estado: pendientes, confirmadas, atendidas y canceladas.",
        "filtros": ["fechas", "estado_cita"], "func": rep_citas,
    },
    "atenciones": {
        "titulo": "Atenciones clínicas", "icono": "description", "roles": [ADMIN, VET],
        "descripcion": "Consultas y controles realizados, con diagnóstico, tratamiento y veterinario.",
        "filtros": ["fechas", "veterinario"], "func": rep_atenciones,
    },
    "inventario": {
        "titulo": "Estado del inventario", "icono": "inventory_2", "roles": [ADMIN, RECEP],
        "descripcion": "Stock actual, insumos bajo el mínimo y valor del inventario.",
        "filtros": ["categoria", "estado_stock"], "func": rep_inventario,
    },
    "movimientos": {
        "titulo": "Movimientos de inventario", "icono": "swap_vert", "roles": [ADMIN, RECEP],
        "descripcion": "Entradas y salidas de insumos en un período.",
        "filtros": ["fechas", "tipo_mov"], "func": rep_movimientos,
    },
    "ia": {
        "titulo": "Diagnósticos con IA", "icono": "neurology", "roles": [ADMIN, VET],
        "descripcion": "Diagnósticos sugeridos por el modelo y la retroalimentación del veterinario.",
        "filtros": ["fechas", "retro"], "func": rep_ia,
    },
}
