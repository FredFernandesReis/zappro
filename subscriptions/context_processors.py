"""
Context processor para disponibilizar dados da assinatura nos templates.
"""

from django.conf import settings


def subscription_context(request):
    """Injeta informações da assinatura e contato do admin nos templates."""
    context = {
        "admin_whatsapp": getattr(settings, "ADMIN_WHATSAPP", ""),
        "admin_whatsapp_display": getattr(settings, "ADMIN_WHATSAPP_DISPLAY", ""),
        "admin_whatsapp_url": (
            f"https://wa.me/{settings.ADMIN_WHATSAPP}"
            if getattr(settings, "ADMIN_WHATSAPP", "")
            else ""
        ),
    }
    if request.user.is_authenticated:
        subscription = getattr(request.user, "subscription", None)
        context["user_subscription"] = subscription
        if subscription:
            context["subscription_active"] = subscription.esta_ativa
            context["user_plan"] = subscription.plan
    return context
