"""
Middleware para verificar assinatura ativa antes de acessar funcionalidades.
"""

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse


class SubscriptionMiddleware:
    """
    Bloqueia acesso quando não há assinatura ativa (pagamento Cakto).
    """

    EXEMPT_URLS = [
        "/accounts/",
        "/admin/",
        "/assinaturas/renovar/",
        "/assinaturas/planos/",
        "/assinaturas/checkout/",
        "/assinaturas/cakto/",
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
                assinatura_ok = bool(subscription and subscription.esta_ativa)

                if not assinatura_ok:
                    if not request.session.get("subscription_warning_shown"):
                        if not subscription:
                            messages.warning(
                                request,
                                "Assine o plano Mensal (R$ 29,90) para usar o ZapPro.",
                            )
                        elif subscription.esta_vencida:
                            messages.warning(
                                request,
                                "Sua assinatura venceu. Renove pelo pagamento Cakto para continuar.",
                            )
                        elif subscription.status == "suspenso":
                            messages.warning(
                                request,
                                "Sua assinatura está pendente. Conclua o pagamento de R$ 29,90 para liberar o acesso.",
                            )
                        elif subscription.status == "cancelado":
                            messages.error(
                                request,
                                "Sua assinatura foi cancelada. Assine novamente para reativar.",
                            )
                        request.session["subscription_warning_shown"] = True

                    allowed = [
                        reverse("subscriptions:renew"),
                        reverse("subscriptions:plans"),
                        reverse("subscriptions:checkout"),
                        reverse("subscriptions:checkout_success"),
                        reverse("accounts:profile"),
                        reverse("dashboard:ajuda"),
                    ]
                    # Home sem plano ativo vai para checkout
                    if path == reverse("dashboard:home"):
                        return redirect("subscriptions:checkout")
                    if path not in allowed and not path.startswith("/accounts/perfil"):
                        return redirect("subscriptions:checkout")

        response = self.get_response(request)
        return response
