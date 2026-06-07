"""
URLs do app whatsapp.
"""

from django.urls import path

from . import views

app_name = "whatsapp"

urlpatterns = [
    path("conexao/", views.connection_view, name="connection"),
    path("status/", views.status_api, name="status"),
    path("webhook/", views.webhook_view, name="webhook"),
]
