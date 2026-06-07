"""
Models do app accounts - Perfil estendido do usuário.
"""

from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    """Perfil complementar vinculado ao User do Django."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )
    telefone = models.CharField("Telefone", max_length=20, blank=True)
    empresa = models.CharField("Empresa", max_length=150, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de Usuário"
        verbose_name_plural = "Perfis de Usuários"

    def __str__(self):
        return f"Perfil de {self.user.username}"
