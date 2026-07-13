"""
Models de respostas automáticas, boas-vindas e horário de atendimento.
"""

from django.contrib.auth.models import User
from django.db import models


class AutoResposta(models.Model):
    """Resposta automática baseada em palavra-chave."""

    STATUS_CHOICES = [
        ("ativa", "Ativa"),
        ("inativa", "Inativa"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="autorespostas")
    palavra_chave = models.CharField("Palavra-chave", max_length=100)
    resposta = models.TextField("Resposta")
    status = models.CharField("Status", max_length=10, choices=STATUS_CHOICES, default="ativa")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Resposta Automática"
        verbose_name_plural = "Respostas Automáticas"
        ordering = ["palavra_chave"]
        unique_together = ("user", "palavra_chave")

    def __str__(self):
        return f"{self.palavra_chave} ({self.user.username})"


class ConfiguracaoBoasVindas(models.Model):
    """Mensagem de boas-vindas enviada ao primeiro contato."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="config_boas_vindas"
    )
    ativo = models.BooleanField("Ativo", default=False)
    mensagem = models.TextField(
        "Mensagem",
        default="Olá! Seja bem-vindo.\nDigite:\n1 - Vendas\n2 - Suporte\n3 - Financeiro",
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração de Boas-Vindas"
        verbose_name_plural = "Configurações de Boas-Vindas"

    def __str__(self):
        return f"Boas-vindas de {self.user.username}"


class ConfiguracaoHorario(models.Model):
    """Horário de atendimento e mensagem fora do expediente."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="config_horario"
    )
    hora_inicial = models.TimeField("Hora Inicial", default="08:00")
    hora_final = models.TimeField("Hora Final", default="18:00")
    mensagem_fora_horario = models.TextField(
        "Mensagem Fora do Horário",
        default="Nosso atendimento funciona das 08:00 às 18:00.",
    )
    ativo = models.BooleanField("Ativo", default=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração de Horário"
        verbose_name_plural = "Configurações de Horário"

    def __str__(self):
        return f"Horário de {self.user.username}"
