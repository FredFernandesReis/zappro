"""
URLs do app reports.
"""

from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.user_reports_view, name="user"),
    path("admin/", views.admin_reports_view, name="admin"),
]
