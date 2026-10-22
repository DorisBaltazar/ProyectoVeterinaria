from collections import Counter

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from usuarios.bitacora import registrar_bitacora
from usuarios.mixins import RolRequeridoMixin
from usuarios.models import Perfil

from .forms import DiagnosticoForm, RetroalimentacionForm
from .ml.inferencia import predecir
from .models import DiagnosticoIA


class DiagnosticoCreateView(RolRequeridoMixin, CreateView):
    """RF-13/RF-14: captura de síntomas y variables clínicas, e inferencia
    con el modelo Random Forest. Restringido exclusivamente al rol
    Veterinario (sección II.C.1 del documento: las vistas de IA permanecen
    bloqueadas para personal no médico)."""
    model = DiagnosticoIA
    form_class = DiagnosticoForm
    template_name = "diagnostico/diagnostico_form.html"
    roles_permitidos = [Perfil.Rol.VETERINARIO]

    def form_valid(self, form):
        resultado = predecir(form.datos_para_inferencia())
        self.object = form.save(commit=False)
        self.object.veterinario = self.request.user
        self.object.prediccion = resultado["prediccion"]
        self.object.confianza = resultado["confianza"]
        self.object.probabilidades = resultado["probabilidades"]
        self.object.save()
        registrar_bitacora(
            self.request.user, "Generó diagnóstico asistido por IA",
            f"{self.object.mascota} → {self.object.prediccion} ({self.object.confianza}%)",
        )
        return redirect("diagnostico:detalle", pk=self.object.pk)


class DiagnosticoDetailView(RolRequeridoMixin, DetailView):
    """RF-15: muestra la predicción con su índice de confianza y el top-3
    de probabilidades como soporte diagnóstico."""
    model = DiagnosticoIA
    template_name = "diagnostico/diagnostico_detail.html"
    context_object_name = "diagnostico"
    roles_permitidos = [Perfil.Rol.VETERINARIO]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        top3 = sorted(self.object.probabilidades.items(), key=lambda kv: kv[1], reverse=True)[:3]
        ctx["top3"] = top3
        ctx["feedback_form"] = RetroalimentacionForm(instance=self.object)
        return ctx


class DiagnosticoFeedbackView(RolRequeridoMixin, UpdateView):
    """RF-16/HU-16: el veterinario confirma o corrige la sugerencia del
    modelo. Esta retroalimentación queda disponible para una futura
    reentrenamiento/evaluación del modelo."""
    model = DiagnosticoIA
    form_class = RetroalimentacionForm
    template_name = "diagnostico/diagnostico_detail.html"
    roles_permitidos = [Perfil.Rol.VETERINARIO]

    def form_valid(self, form):
        from django.utils import timezone
        self.object = form.save(commit=False)
        self.object.fecha_feedback = timezone.now()
        self.object.save()
        registrar_bitacora(
            self.request.user, "Registró retroalimentación de diagnóstico IA",
            f"{self.object.mascota} → {self.object.get_retroalimentacion_display()}",
        )
        messages.success(self.request, "Retroalimentación registrada.")
        return redirect("diagnostico:detalle", pk=self.object.pk)


class DiagnosticoListView(RolRequeridoMixin, ListView):
    model = DiagnosticoIA
    template_name = "diagnostico/diagnostico_list.html"
    context_object_name = "diagnosticos"
    paginate_by = 20
    roles_permitidos = [Perfil.Rol.VETERINARIO]

    def get_queryset(self):
        qs = DiagnosticoIA.objects.select_related("mascota", "veterinario").all()
        if not self.request.user.is_superuser:
            qs = qs.filter(veterinario=self.request.user)
        return qs


class ReporteDiagnosticosView(RolRequeridoMixin, TemplateView):
    """HU-16 (parcial): reporte gerencial básico — distribución de
    diagnósticos sugeridos y tasa de confirmación/corrección del modelo,
    como insumo para la evaluación continua del módulo de IA."""
    template_name = "diagnostico/reporte.html"
    roles_permitidos = [Perfil.Rol.ADMINISTRADOR, Perfil.Rol.VETERINARIO]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = DiagnosticoIA.objects.all()
        total = qs.count()
        conteo = Counter(qs.values_list("prediccion", flat=True))
        ctx["total"] = total
        ctx["por_diagnostico"] = conteo.most_common()
        ctx["confirmados"] = qs.filter(retroalimentacion=DiagnosticoIA.Retroalimentacion.CONFIRMADO).count()
        ctx["corregidos"] = qs.filter(retroalimentacion=DiagnosticoIA.Retroalimentacion.CORREGIDO).count()
        ctx["pendientes"] = qs.filter(retroalimentacion=DiagnosticoIA.Retroalimentacion.PENDIENTE).count()
        if total:
            evaluados = ctx["confirmados"] + ctx["corregidos"]
            ctx["precision_percibida"] = round((ctx["confirmados"] / evaluados) * 100, 1) if evaluados else None
        else:
            ctx["precision_percibida"] = None
        return ctx
