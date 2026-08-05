"""
Views de respostas automáticas, boas-vindas e horário.
"""

import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.utils.html import strip_tags

from .ai_service import ai_configured, generate_autorespostas
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


@login_required
@ensure_csrf_cookie
def assistente_view(request):
    """Página do assistente de IA para criar respostas."""
    return render(
        request,
        "autorespostas/assistente.html",
        {
            "ai_ok": ai_configured(),
            "total": AutoResposta.objects.filter(user=request.user).count(),
            "plan": _get_user_plan(request.user),
        },
    )


@login_required
@require_POST
def assistente_gerar_view(request):
    """API: gera sugestões de respostas com IA."""
    if not ai_configured():
        return JsonResponse(
            {
                "ok": False,
                "error": "IA não configurada. Peça ao administrador para definir GEMINI_API_KEY.",
            },
            status=503,
        )

    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        body = {}

    descricao = (body.get("descricao") or request.POST.get("descricao") or "").strip()
    try:
        sugestoes = generate_autorespostas(descricao)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    except RuntimeError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=502)
    except Exception:
        return JsonResponse(
            {"ok": False, "error": "Erro inesperado ao gerar sugestões."},
            status=500,
        )

    return JsonResponse({"ok": True, **sugestoes})


@login_required
@require_POST
def assistente_salvar_view(request):
    """API: salva respostas selecionadas (e opcionalmente boas-vindas)."""
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "JSON inválido."}, status=400)

    itens = body.get("respostas") or []
    if not isinstance(itens, list):
        itens = []

    boas_vindas_preview = str(body.get("boas_vindas") or "").strip()
    aplicar_bv_preview = bool(body.get("aplicar_boas_vindas")) and bool(boas_vindas_preview)
    if not itens and not aplicar_bv_preview:
        return JsonResponse(
            {"ok": False, "error": "Selecione ao menos uma resposta ou a boas-vindas."},
            status=400,
        )

    criadas = 0
    atualizadas = 0
    ignoradas = 0
    erros = []

    for item in itens:
        if not isinstance(item, dict):
            continue
        chave = str(item.get("palavra_chave") or "").strip()[:100]
        texto = str(item.get("resposta") or "").strip()[:2000]
        if not chave or not texto:
            continue

        existente = AutoResposta.objects.filter(
            user=request.user, palavra_chave__iexact=chave
        ).first()
        if existente:
            existente.resposta = texto
            existente.status = "ativa"
            existente.save(update_fields=["resposta", "status", "atualizado_em"])
            atualizadas += 1
            continue

        ok, limit_msg = _check_response_limit(request.user)
        if not ok:
            ignoradas += 1
            if limit_msg and strip_tags(str(limit_msg)) not in erros:
                erros.append(strip_tags(str(limit_msg)))
            continue

        AutoResposta.objects.create(
            user=request.user,
            palavra_chave=chave,
            resposta=texto,
            status="ativa",
        )
        criadas += 1

    boas_vindas = str(body.get("boas_vindas") or "").strip()[:2000]
    aplicar_bv = bool(body.get("aplicar_boas_vindas")) and bool(boas_vindas)
    bv_ok = False
    if aplicar_bv:
        plan = _get_user_plan(request.user)
        if plan and not plan.permite_boas_vindas:
            erros.append("Seu plano não inclui mensagem de boas-vindas.")
        else:
            config, _ = ConfiguracaoBoasVindas.objects.get_or_create(user=request.user)
            config.mensagem = boas_vindas
            config.ativo = True
            config.save()
            bv_ok = True

    if criadas == 0 and atualizadas == 0 and not bv_ok:
        return JsonResponse(
            {
                "ok": False,
                "error": erros[0] if erros else "Nenhuma resposta foi salva.",
                "ignoradas": ignoradas,
            },
            status=400,
        )

    return JsonResponse(
        {
            "ok": True,
            "criadas": criadas,
            "atualizadas": atualizadas,
            "ignoradas": ignoradas,
            "boas_vindas": bv_ok,
            "avisos": erros,
        }
    )
