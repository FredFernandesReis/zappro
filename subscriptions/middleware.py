"""
Middleware para verificar assinatura ativa antes de acessar funcionalidades.
"""

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse


class SubscriptionMiddleware:
    """
    Bloqueia acesso às funções do sistema quando a assinatura está
    vencida, suspensa ou cancelada.
    """

    # URLs liberadas mesmo com assinatura inativa
    EXEMPT_URLS = [
        "/accounts/",
        "/admin/",
        "/assinaturas/renovar/",
        "/assinaturas/planos/",
        "/ajuda/",
        "/static/",
        "/media/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_staff:
            path = request.path

            if not any(path.startswith(url) for url in self.EXEMPT_URLS):
                subscription = getattr(request.user, "subscription", None)

                if subscription and not subscription.esta_ativa:
                    if not request.session.get("subscription_warning_shown"):
                        if subscription.esta_vencida:
                            messages.warning(
                                request,
                                "Sua assinatura venceu. Renove para continuar usando o ZapPro.",
                            )
                        elif subscription.status == "suspenso":
                            from django.conf import settings
                            from django.utils.safestring import mark_safe

                            display = getattr(settings, "ADMIN_WHATSAPP_DISPLAY", "")
                            wa = getattr(settings, "ADMIN_WHATSAPP", "")
                            if wa:
                                url = f"https://wa.me/{wa}?text=Ol%C3%A1!%20Minha%20assinatura%20est%C3%A1%20suspensa."
                                messages.warning(
                                    request,
                                    mark_safe(
                                        f'Sua assinatura está suspensa. '
                                        f'<a href="{url}" target="_blank" rel="noopener">Fale com o suporte no WhatsApp</a>'
                                        f'{f" ({display})" if display else ""}.'
                                    ),
                                    extra_tags="html",
                                )
                            else:
                                messages.warning(
                                    request,
                                    "Sua assinatura está suspensa. Entre em contato com o suporte.",
                                )
                        elif subscription.status == "cancelado":
                            messages.error(
                                request,
                                "Sua assinatura foi cancelada. Renove para reativar o acesso.",
                            )
                        request.session["subscription_warning_shown"] = True

                    # Bloqueia funcionalidades, permite renovação, planos, ajuda e perfil
                    allowed = [
                        reverse("subscriptions:renew"),
                        reverse("subscriptions:plans"),
                        reverse("accounts:profile"),
                        reverse("dashboard:home"),
                        reverse("dashboard:ajuda"),
                    ]
                    if path not in allowed and not path.startswith("/accounts/perfil"):
                        return redirect("subscriptions:renew")

        response = self.get_response(request)
        return response
