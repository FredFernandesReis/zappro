"""
URLs do app subscriptions.
"""

from django.urls import path

from . import views

app_name = "subscriptions"

urlpatterns = [
    path("renovar/", views.renew_view, name="renew"),
    path("planos/", views.plans_view, name="plans"),
    path("admin/usuarios/", views.admin_users_view, name="admin_users"),
    path("admin/usuarios/<int:user_id>/editar/", views.admin_edit_subscription_view, name="admin_edit_subscription"),
]
