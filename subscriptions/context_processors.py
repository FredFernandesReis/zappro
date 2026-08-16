"""
Context processor para disponibilizar dados da assinatura nos templates.
"""

from django.conf import settings

from whatsapp.models import WhatsAppConnection


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
        "subscription_expiring_soon": False,
        "dias_restantes": None,
        "whatsapp_connection": None,
        "whatsapp_disconnected": False,
    }
    if request.user.is_authenticated:
        subscription = getattr(request.user, "subscription", None)
        context["user_subscription"] = subscription
        if subscription:
            context["subscription_active"] = subscription.esta_ativa
            context["user_plan"] = subscription.plan
            if subscription.esta_ativa:
                dias = subscription.dias_restantes
                context["dias_restantes"] = dias
                context["subscription_expiring_soon"] = dias <= 5
        connection = WhatsAppConnection.objects.filter(user=request.user).first()
        context["whatsapp_connection"] = connection
        context["whatsapp_disconnected"] = bool(
            connection
            and connection.status == "desconectado"
            and (connection.conectado_em or connection.numero_telefone)
        )
    return context
