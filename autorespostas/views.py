"""
Views de respostas automáticas, boas-vindas e horário.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.safestring import mark_safe

from .forms import AutoRespostaForm, BoasVindasForm, HorarioForm
from .models import AutoResposta, ConfiguracaoBoasVindas, ConfiguracaoHorario
from subscriptions.plan_utils import get_active_plan, can_create_autoresposta


def _upgrade_message(texto_base):
    """Mensagem de upgrade com link direto para o WhatsApp do administrador."""
    display = getattr(settings, "ADMIN_WHATSAPP_DISPLAY", "")
    wa = getattr(settings, "ADMIN_WHATSAPP", "")
    if not wa:
        return f"{texto_base} {f'Chame o administrador: {display}' if display else ''}".strip()

    url = f"https://wa.me/{wa}?text=Ol%C3%A1!%20Quero%20assinar%20um%20plano%20no%20ZapPro."
    label = display or "WhatsApp"
    return mark_safe(
        f'{texto_base} '
        f'<a href="{url}" target="_blank" rel="noopener">Chamar no WhatsApp ({label})</a> para assinar.'
    )


def _get_user_plan(user):
    """Retorna o plano ativo do usuário ou None."""
    return get_active_plan(user)


def _check_response_limit(user):
    """Verifica limite de respostas do plano."""
    ok, limit_or_none = can_create_autoresposta(user)
    if ok:
        return True, None

    if isinstance(limit_or_none, int):
        msg = _upgrade_message(
            f"Seu plano permite no máximo {limit_or_none} respostas automáticas."
        )
        return False, msg

    return False, limit_or_none or "Limite de respostas atingido."


@login_required
def list_view(request):
    """Lista todas as respostas automáticas do usuário."""
    respostas = AutoResposta.objects.filter(user=request.user)
    plan = _get_user_plan(request.user)

    return render(request, "autorespostas/list.html", {
        "respostas": respostas,
        "plan": plan,
        "total": respostas.count(),
    })


@login_required
def create_view(request):
    """Cria nova resposta automática."""
    can_create, error_msg = _check_response_limit(request.user)
    if not can_create:
        messages.error(request, error_msg, extra_tags="html")
        return redirect("autorespostas:list")

    if request.method == "POST":
        form = AutoRespostaForm(request.POST)
        if form.is_valid():
            resposta = form.save(commit=False)
            resposta.user = request.user
            resposta.save()
            messages.success(request, "Resposta automática criada com sucesso!")
            return redirect("autorespostas:list")
    else:
        form = AutoRespostaForm()

    return render(request, "autorespostas/form.html", {
        "form": form,
        "title": "Nova Resposta Automática",
    })


@login_required
def edit_view(request, pk):
    """Edita resposta automática existente."""
    resposta = get_object_or_404(AutoResposta, pk=pk, user=request.user)

    if request.method == "POST":
        form = AutoRespostaForm(request.POST, instance=resposta)
        if form.is_valid():
            form.save()
            messages.success(request, "Resposta automática atualizada!")
            return redirect("autorespostas:list")
    else:
        form = AutoRespostaForm(instance=resposta)

    return render(request, "autorespostas/form.html", {
        "form": form,
        "title": "Editar Resposta Automática",
        "resposta": resposta,
    })


@login_required
def delete_view(request, pk):
    """Exclui resposta automática."""
    resposta = get_object_or_404(AutoResposta, pk=pk, user=request.user)

    if request.method == "POST":
        resposta.delete()
        messages.success(request, "Resposta automática excluída!")
        return redirect("autorespostas:list")

    return render(request, "autorespostas/delete.html", {"resposta": resposta})


@login_required
def boas_vindas_view(request):
    """Configuração da mensagem de boas-vindas."""
    config, _ = ConfiguracaoBoasVindas.objects.get_or_create(user=request.user)
    plan = _get_user_plan(request.user)

    if plan and not plan.permite_boas_vindas:
        messages.warning(
            request,
            _upgrade_message("Seu plano não inclui mensagem de boas-vindas."),
            extra_tags="html",
        )
        return redirect("subscriptions:plans")

    if request.method == "POST":
        form = BoasVindasForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuração de boas-vindas salva!")
            return redirect("autorespostas:boas_vindas")
    else:
        form = BoasVindasForm(instance=config)

    return render(request, "autorespostas/boas_vindas.html", {"form": form})


@login_required
def horario_view(request):
    """Configuração de horário de atendimento."""
    config, _ = ConfiguracaoHorario.objects.get_or_create(user=request.user)
    plan = _get_user_plan(request.user)

    if plan and not plan.permite_horario:
        messages.warning(
            request,
            _upgrade_message("Horário de atendimento disponível a partir do plano Básico."),
            extra_tags="html",
        )
        return redirect("subscriptions:plans")

    if request.method == "POST":
        form = HorarioForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Horário de atendimento configurado!")
            return redirect("autorespostas:horario")
    else:
        form = HorarioForm(instance=config)

    return render(request, "autorespostas/horario.html", {"form": form})
