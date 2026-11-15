import csv

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views import View

from pacientes.models import Mascota
from usuarios.bitacora import registrar_bitacora

from .definiciones import REPORTES, _fmt, _fmt_dt, _nombre
from .forms import FiltroReporteForm


def _rol(user):
    perfil = getattr(user, "perfil", None)
    return perfil.rol if perfil else None


def _permitido(user, roles):
    return user.is_superuser or _rol(user) in roles


def _csv(nombre, columnas, filas, resumen=()):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{nombre}_{timezone.localdate():%Y%m%d}.csv"'
    resp.write("﻿")  # BOM: Excel reconoce los acentos
    w = csv.writer(resp, delimiter=";")
    for etiqueta, valor in resumen:
        w.writerow([etiqueta, valor])
    if resumen:
        w.writerow([])
    w.writerow(columnas)
    for fila in filas:
        w.writerow(["" if v is None else v for v in fila])
    return resp


class IndiceReportesView(LoginRequiredMixin, View):
    def get(self, request):
        visibles = [(k, d) for k, d in REPORTES.items() if _permitido(request.user, d["roles"])]
        if not visibles:
            raise PermissionDenied
        return render(request, "reportes/index.html", {"reportes": visibles,
                                                       "ver_ia": _permitido(request.user, ["ADMIN", "VET"])})


class ReporteView(LoginRequiredMixin, View):
    def get(self, request, clave):
        defn = REPORTES.get(clave)
        if defn is None:
            raise Http404
        if not _permitido(request.user, defn["roles"]):
            raise PermissionDenied
        formato = request.GET.get("formato", "")
        form = FiltroReporteForm(request.GET or None, filtros=defn["filtros"])
        valido = form.is_valid() if request.GET else True
        datos = form.cleaned_data if (request.GET and valido) else {}
        resultado = defn["func"](datos) if valido else None
        if formato == "csv" and resultado:
            registrar_bitacora(request.user, "Exportó reporte", f"{defn['titulo']} (CSV)")
            return _csv(clave, resultado["columnas"], resultado["filas"], resultado["resumen"])
        if formato == "imprimir" and resultado:
            registrar_bitacora(request.user, "Imprimió reporte", defn["titulo"])
            return render(request, "reportes/imprimible.html", {
                "titulo": defn["titulo"], "resultado": resultado, "generado": timezone.localtime(),
                "usuario": _nombre(request.user), "filtros": _filtros_texto(form, datos)})
        return render(request, "reportes/reporte.html", {
            "clave": clave, "defn": defn, "form": form, "resultado": resultado,
            "querystring": request.GET.urlencode()})


def _filtros_texto(form, datos):
    partes = []
    for nombre, valor in datos.items():
        if valor in (None, ""):
            continue
        campo = form.fields[nombre]
        if hasattr(valor, "strftime"):
            valor = _fmt(valor)
        elif getattr(campo, "choices", None):
            valor = dict((str(k), v) for k, v in campo.choices).get(str(valor), valor)
        partes.append(f"{campo.label}: {valor}")
    return " · ".join(partes)


class FichaMascotaView(LoginRequiredMixin, View):
    """Ficha clínica completa de un paciente (imprimible o CSV)."""
    roles = ["ADMIN", "VET", "RECEP"]

    def get(self, request, pk):
        if not _permitido(request.user, self.roles):
            raise PermissionDenied
        m = get_object_or_404(Mascota.objects.select_related("propietario"), pk=pk)
        historiales = list(m.historiales.select_related("veterinario").prefetch_related("resultados_lab")
                           .order_by("-fecha_atencion"))
        pesos = list(m.pesos.order_by("-fecha")) if hasattr(m, "pesos") else []
        if request.GET.get("formato") == "csv":
            registrar_bitacora(request.user, "Exportó ficha de paciente", f"{m.codigo} (CSV)")
            filas = [[_fmt_dt(h.fecha_atencion), h.get_tipo_atencion_display(), h.motivo, h.sintomas,
                      h.diagnostico, h.tratamiento, h.medicamentos,
                      h.peso_kg if h.peso_kg is not None else "", h.temperatura_c if h.temperatura_c is not None else "",
                      _nombre(h.veterinario)] for h in historiales]
            resumen = [("Código", m.codigo), ("Mascota", m.nombre), ("Especie", m.get_especie_display()),
                       ("Raza", m.raza), ("Edad", m.edad_texto or ""),
                       ("Peso actual (kg)", m.peso_actual if m.peso_actual is not None else ""),
                       ("Propietario", m.propietario.nombre_completo), ("Teléfono", m.propietario.telefono),
                       ("Alerta médica", m.alerta_medica)]
            return _csv(f"ficha_{m.codigo}", ["Fecha y hora", "Tipo", "Motivo", "Síntomas", "Diagnóstico",
                                              "Tratamiento", "Medicamentos", "Peso (kg)", "Temp. (°C)",
                                              "Veterinario"], filas, resumen)
        registrar_bitacora(request.user, "Imprimió ficha de paciente", m.codigo)
        return render(request, "reportes/ficha_mascota.html", {
            "m": m, "historiales": historiales, "pesos": pesos,
            "generado": timezone.localtime(), "usuario": _nombre(request.user)})
