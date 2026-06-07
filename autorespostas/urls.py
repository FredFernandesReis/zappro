"""
URLs do app autorespostas.
"""

from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "autorespostas"

urlpatterns = [
    path("", views.list_view, name="list"),
    path("criar/", views.create_view, name="create"),
    path("<int:pk>/editar/", views.edit_view, name="edit"),
    path("<int:pk>/excluir/", views.delete_view, name="delete"),
    path("boas-vindas/", views.boas_vindas_view, name="boas_vindas"),
    path("horario/", views.horario_view, name="horario"),
    # Página removida — redireciona links antigos para a lista de respostas
    path(
        "comportamento/",
        RedirectView.as_view(pattern_name="autorespostas:list", permanent=False),
        name="comportamento",
    ),
]
