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
    por_especie = {}
    for r in filas:
        por_especie[r[2]] = por_especie.get(r[2], 0) + 1
    return {
        "columnas": ["Código", "Mascota", "Especie", "Raza", "Sexo", "Edad", "Peso (kg)", "Propietario",
                     "CI", "Teléfono", "Alerta médica", "Nº consultas", "Última atención", "Activa"],
        "filas": filas,
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
    return {
        "columnas": ["Fecha", "Hora", "Propietario", "Teléfono", "Mascota", "Especie", "Motivo",
                     "Veterinario", "Estado"],
        "filas": filas,
        "resumen": [("Total de citas", len(filas))] + [(f"Estado: {k}", v) for k, v in por_estado.items()],
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
    return {
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
    return {
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
    return {
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
    return {
        "columnas": ["Fecha y hora", "Código", "Mascota", "Veterinario", "Diagnóstico sugerido", "Confianza",
                     "Retroalimentación", "Diagnóstico real"],
        "filas": filas,
        "resumen": [("Total de diagnósticos IA", len(filas)), ("Confirmados", conf), ("Corregidos", corr)],
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
