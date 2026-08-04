"""
Integração Cakto: checkout + ativação automática via webhook.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Plan, Subscription

logger = logging.getLogger(__name__)


def build_checkout_url(user: User | None = None) -> str:
    """Monta URL do checkout Cakto, com e-mail/ref do usuário quando possível."""
    base = (getattr(settings, "CAKTO_CHECKOUT_URL", "") or "").rstrip("/")
    if not base:
        return ""

    params = {}
    if user and user.is_authenticated:
        if user.email:
            params["email"] = user.email
        name = (user.get_full_name() or user.username or "").strip()
        if name:
            params["name"] = name
        params["ref"] = f"zappro_u{user.id}"

    if not params:
        return base
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}{urlencode(params)}"


def _dig(data: dict, *paths: tuple[str, ...], default=None):
    for path in paths:
        cur: Any = data
        ok = True
        for key in path:
            if not isinstance(cur, dict) or key not in cur:
                ok = False
                break
            cur = cur[key]
        if ok and cur not in (None, ""):
            return cur
    return default


def extract_customer_email(data: dict) -> str:
    email = _dig(
        data,
        ("customer", "email"),
        ("buyer", "email"),
        ("client", "email"),
        ("email",),
        ("customerEmail",),
        ("customer_email",),
        ("user", "email"),
        ("data", "customer", "email"),
        ("data", "email"),
        default="",
    )
    if email:
        return str(email).strip().lower()

    # Varredura rasa por qualquer campo "email"
    stack = [data]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                if str(k).lower() in ("email", "customer_email", "customeremail") and v:
                    return str(v).strip().lower()
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(cur, list):
            stack.extend(cur)
    return ""


def extract_ref_user_id(data: dict) -> int | None:
    """Tenta achar user id em ref/metadata do payload."""
    candidates = [
        _dig(data, ("ref",), ("metadata", "ref"), ("custom", "ref"), ("affiliate",), default=""),
        _dig(data, ("utm_content",), default=""),
        _dig(data, ("customer", "ref"), default=""),
    ]
    for raw in candidates:
        text = str(raw or "")
        if "zappro_u" in text:
            try:
                return int(text.split("zappro_u", 1)[1].split("&")[0].strip())
            except (TypeError, ValueError):
                continue
    return None


def extract_order_id(data: dict) -> str:
    value = _dig(data, ("id",), ("orderId",), ("order_id",), ("payment", "id"), default="")
    return str(value or "")


def extract_subscription_id(data: dict) -> str:
    value = _dig(
        data,
        ("subscription", "id"),
        ("subscriptionId",),
        ("subscription_id",),
        default="",
    )
    return str(value or "")


def resolve_user_from_payload(data: dict) -> User | None:
    user_id = extract_ref_user_id(data)
    if user_id:
        user = User.objects.filter(pk=user_id).first()
        if user:
            return user

    email = extract_customer_email(data)
    if email:
        user = User.objects.filter(email__iexact=email).first()
        if user:
            return user

        # fallback: username igual ao e-mail
        user = User.objects.filter(username__iexact=email).first()
        if user:
            return user
    return None


def get_paid_plan() -> Plan | None:
    return Plan.objects.filter(slug="basico", ativo=True).first() or Plan.objects.filter(ativo=True).first()


def activate_subscription_from_payment(
    user: User,
    *,
    order_id: str = "",
    subscription_id: str = "",
    event: str = "",
    email: str = "",
    days: int | None = None,
) -> Subscription:
    """Ativa/renova assinatura Mensal após pagamento aprovado."""
    plan = get_paid_plan()
    if not plan:
        raise RuntimeError("Nenhum plano pago configurado")

    days = int(days if days is not None else getattr(settings, "CAKTO_PLAN_DAYS", 30))
    today = timezone.localdate()

    sub, _ = Subscription.objects.get_or_create(
        user=user,
        defaults={
            "plan": plan,
            "status": "ativo",
            "data_vencimento": today + timedelta(days=days),
        },
    )

    if sub.status == "ativo" and sub.data_vencimento >= today:
        base = sub.data_vencimento
    else:
        base = today

    sub.plan = plan
    sub.status = "ativo"
    sub.data_vencimento = base + timedelta(days=days)
    if email:
        sub.cakto_customer_email = email
    elif user.email:
        sub.cakto_customer_email = user.email
    if order_id:
        sub.cakto_order_id = str(order_id)[:100]
    if subscription_id:
        sub.cakto_subscription_id = str(subscription_id)[:100]
    if event:
        sub.cakto_last_event = event[:80]
    sub.save()

    logger.info(
        "Assinatura ativada via Cakto user=%s até %s event=%s",
        user.id,
        sub.data_vencimento,
        event,
    )
    return sub


def suspend_subscription_from_cancel(
    user: User,
    *,
    event: str = "",
) -> Subscription | None:
    sub = getattr(user, "subscription", None)
    if not sub:
        return None
    sub.status = "cancelado"
    if event:
        sub.cakto_last_event = event[:80]
    sub.save(update_fields=["status", "cakto_last_event", "atualizado_em"])
    return sub
