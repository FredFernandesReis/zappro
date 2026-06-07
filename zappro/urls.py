"""
URLs principais do ZapPro.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("dashboard.urls")),
    path("accounts/", include("accounts.urls")),
    path("whatsapp/", include("whatsapp.urls")),
    path("assinaturas/", include("subscriptions.urls")),
    path("respostas/", include("autorespostas.urls")),
    path("relatorios/", include("reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
