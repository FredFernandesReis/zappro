"""
Views de assinaturas e renovação.
"""

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from .forms import UserSubscriptionForm
from .models import Plan, Subscription


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
    })


def plans_view(request):
    """Exibe planos disponíveis (público). Assinatura via WhatsApp do admin."""
    planos = Plan.objects.filter(ativo=True)
    subscription = None
    if request.user.is_authenticated:
        subscription = getattr(request.user, "subscription", None)

    return render(request, "subscriptions/plans.html", {
        "planos": planos,
        "subscription": subscription,
    })

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
            "plan": Plan.objects.filter(slug="gratuito").first(),
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
