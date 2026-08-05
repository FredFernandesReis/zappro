"""
URLs do app subscriptions.
"""

from django.urls import path

from . import views

app_name = "subscriptions"

urlpatterns = [
    path("renovar/", views.renew_view, name="renew"),
    path("minha/", views.minha_assinatura_view, name="minha"),
    path("planos/", views.plans_view, name="plans"),
    path("checkout/", views.checkout_view, name="checkout"),
    path("checkout/sucesso/", views.checkout_success_view, name="checkout_success"),
    path("cakto/webhook/", views.cakto_webhook_view, name="cakto_webhook"),
    path("admin/usuarios/", views.admin_users_view, name="admin_users"),
    path("admin/usuarios/<int:user_id>/editar/", views.admin_edit_subscription_view, name="admin_edit_subscription"),
]
