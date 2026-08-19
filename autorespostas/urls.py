"""
URLs do app autorespostas.
"""

from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "autorespostas"

urlpatterns = [
    path("", views.list_view, name="list"),
    path("modelos/", views.modelos_view, name="modelos"),
    path("criar/", views.create_view, name="create"),
    path("assistente/", views.assistente_view, name="assistente"),
    path("assistente/gerar/", views.assistente_gerar_view, name="assistente_gerar"),
    path("assistente/salvar/", views.assistente_salvar_view, name="assistente_salvar"),
    path("<int:pk>/editar/", views.edit_view, name="edit"),
    path("<int:pk>/excluir/", views.delete_view, name="delete"),
    path("boas-vindas/", views.boas_vindas_view, name="boas_vindas"),
    path("boas-vindas/audio/", views.boas_vindas_audio_view, name="boas_vindas_audio"),
    path("horario/", views.horario_view, name="horario"),
    # Página removida — redireciona links antigos para a lista de respostas
    path(
        "comportamento/",
        RedirectView.as_view(pattern_name="autorespostas:list", permanent=False),
        name="comportamento",
    ),
]
