"""
URLs do app dashboard.
"""

from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.landing_view, name="landing"),
    path("painel/", views.home_view, name="home"),
    path("ajuda/", views.ajuda_view, name="ajuda"),
]
