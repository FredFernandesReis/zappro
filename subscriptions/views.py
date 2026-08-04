"""
Views de assinaturas, renovação e webhook Cakto.
"""

import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .cakto_service import (
    activate_subscription_from_payment,
    build_checkout_url,
    extract_customer_email,
    extract_order_id,
    extract_subscription_id,
    resolve_user_from_payload,
    suspend_subscription_from_cancel,
)
from .forms import UserSubscriptionForm
from .models import CaktoWebhookLog, Plan, Subscription

logger = logging.getLogger(__name__)


@login_required
def renew_view(request):
    """Página de aviso de renovação quando assinatura está inativa."""
    subscription = getattr(request.user, "subscription", None)

    if subscription and subscription.esta_ativa:
        return redirect("dashboard:home")

    planos = Plan.objects.filter(ativo=True)

    return render(request, "subscriptions/renew.html", {
        "subscription": subscription,
        "planos": planos,
        "checkout_url": build_checkout_url(request.user),
    })


def plans_view(request):
    """Exibe planos disponíveis (público). Pagamento via Cakto."""
    planos = Plan.objects.filter(ativo=True)
    subscription = None
    if request.user.is_authenticated:
        subscription = getattr(request.user, "subscription", None)

    return render(request, "subscriptions/plans.html", {
        "planos": planos,
        "subscription": subscription,
        "cakto_enabled": bool(getattr(settings, "CAKTO_CHECKOUT_URL", "")),
    })


@login_required
def checkout_view(request):
    """
    Página de pagamento.
    Tenta embutir o checkout Cakto em iframe; se a Cakto bloquear,
    o cliente usa o botão para abrir em nova aba.
    """
    checkout_url = build_checkout_url(request.user)
    if not checkout_url:
        messages.error(request, "Checkout Cakto não configurado.")
        return redirect("subscriptions:plans")

    if not request.user.email:
        messages.warning(
            request,
            "Cadastre um e-mail no perfil igual ao e-mail usado no pagamento, "
            "para ativarmos sua assinatura automaticamente.",
        )

    return render(request, "subscriptions/checkout.html", {
        "checkout_url": checkout_url,
        "embed_iframe": getattr(settings, "CAKTO_EMBED_IFRAME", True),
        "subscription": getattr(request.user, "subscription", None),
    })


@login_required
def checkout_success_view(request):
    """Tela pós-pagamento (ativação real vem do webhook)."""
    messages.success(
        request,
        "Recebemos seu pagamento! Se a assinatura ainda não liberou, aguarde alguns segundos "
        "e atualize a página (a Cakto confirma via webhook).",
    )
    return redirect("dashboard:home")


@csrf_exempt
@require_POST
def cakto_webhook_view(request):
    """
    Webhook da Cakto.
    Configure no painel: Integrações > Webhooks
    URL: https://SEU_DOMINIO/assinaturas/cakto/webhook/
    Secret: o mesmo de CAKTO_WEBHOOK_SECRET
    Eventos: purchase_approved, subscription_renewed, subscription_canceled, refund, chargeback
    """
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

    secret = str(payload.get("secret") or request.headers.get("X-Webhook-Secret") or "")
    expected = getattr(settings, "CAKTO_WEBHOOK_SECRET", "")
    if not expected or secret != expected:
        logger.warning("Webhook Cakto com secret inválido")
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=401)

    event = str(payload.get("event") or "")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload

    log = CaktoWebhookLog.objects.create(event=event or "unknown", payload=payload)

    try:
        user = resolve_user_from_payload(data)
        email = extract_customer_email(data)
        order_id = extract_order_id(data)
        sub_id = extract_subscription_id(data)

        activate_events = {
            "purchase_approved",
            "subscription_renewed",
            "compra_aprovada",
            "assinatura_renovada",
        }
        cancel_events = {
            "subscription_canceled",
            "refund",
            "chargeback",
            "assinatura_cancelada",
            "reembolso",
        }

        if event in activate_events:
            if not user:
                log.detalhe = f"Usuário não encontrado (email={email})"
                log.save(update_fields=["detalhe"])
                # 200 para a Cakto não reenviar em loop; admin pode reconciliar
                return JsonResponse({"ok": True, "matched": False})

            sub = activate_subscription_from_payment(
                user,
                order_id=order_id,
                subscription_id=sub_id,
                event=event,
                email=email,
            )
            log.processado = True
            log.detalhe = f"Ativado user={user.id} até {sub.data_vencimento}"
            log.save(update_fields=["processado", "detalhe"])
            return JsonResponse({"ok": True, "matched": True, "user_id": user.id})

        if event in cancel_events:
            if user:
                suspend_subscription_from_cancel(user, event=event)
                log.processado = True
                log.detalhe = f"Cancelado/suspenso user={user.id}"
                log.save(update_fields=["processado", "detalhe"])
            else:
                log.detalhe = f"Cancelamento sem usuário (email={email})"
                log.save(update_fields=["detalhe"])
            return JsonResponse({"ok": True})

        log.detalhe = "Evento ignorado"
        log.save(update_fields=["detalhe"])
        return JsonResponse({"ok": True, "ignored": True})
    except Exception as exc:
        logger.exception("Erro webhook Cakto")
        log.detalhe = str(exc)
        log.save(update_fields=["detalhe"])
        return JsonResponse({"ok": False, "error": "Erro interno"}, status=500)


@staff_member_required
def admin_users_view(request):
    """Painel admin: listagem de usuários e assinaturas."""
    users = User.objects.select_related("subscription", "subscription__plan").order_by("-date_joined")

    return render(request, "subscriptions/admin_users.html", {
        "users": users,
    })


@staff_member_required
def admin_edit_subscription_view(request, user_id):
    """Painel admin: editar assinatura de um usuário."""
    user = get_object_or_404(User, pk=user_id)
    from datetime import date

    subscription, created = Subscription.objects.get_or_create(
        user=user,
        defaults={
            "plan": Plan.objects.filter(slug="basico", ativo=True).first()
            or Plan.objects.filter(ativo=True).first(),
            "status": "ativo",
            "data_vencimento": date(2099, 12, 31),
        },
    )

    if request.method == "POST":
        form = UserSubscriptionForm(request.POST, instance=subscription)
        if form.is_valid():
            form.save()
            messages.success(request, f"Assinatura de {user.username} atualizada!")
            return redirect("subscriptions:admin_users")
    else:
        form = UserSubscriptionForm(instance=subscription)

    return render(request, "subscriptions/admin_edit_subscription.html", {
        "form": form,
        "edit_user": user,
        "subscription": subscription,
    })
