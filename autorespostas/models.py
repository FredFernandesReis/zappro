"""
Models de respostas automáticas, boas-vindas e horário de atendimento.
"""

from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db import models


def _audio_boas_vindas_path(instance, filename):
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "ogg").lower()[:8]
    return f"boas_vindas/{instance.user_id}/welcome.{ext}"


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
    """Mensagens de boas-vindas (até 3) enviadas ao primeiro contato, com rotação."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="config_boas_vindas"
    )
    ativo = models.BooleanField("Ativo", default=False)
    mensagem = models.TextField(
        "Mensagem 1",
        default="Olá! Seja bem-vindo.\nDigite:\n1 - Vendas\n2 - Suporte\n3 - Financeiro",
    )
    mensagem_2 = models.TextField("Mensagem 2", blank=True, default="")
    mensagem_3 = models.TextField("Mensagem 3", blank=True, default="")
    audio = models.FileField(
        "Áudio de boas-vindas",
        upload_to=_audio_boas_vindas_path,
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["ogg", "opus", "mp3", "m4a", "aac", "wav", "webm"]
            )
        ],
        help_text="Opcional. Até 2 MB. Enviado como áudio no WhatsApp.",
    )
    ultima_variacao = models.PositiveSmallIntegerField(
        "Última variação enviada", default=0
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração de Boas-Vindas"
        verbose_name_plural = "Configurações de Boas-Vindas"

    def __str__(self):
        return f"Boas-vindas de {self.user.username}"

    def mensagens_ativas(self):
        """Lista as mensagens preenchidas (1 a 3)."""
        msgs = []
        for texto in (self.mensagem, self.mensagem_2, self.mensagem_3):
            limpo = (texto or "").strip()
            if limpo:
                msgs.append(limpo)
        return msgs

    def tem_conteudo(self):
        return bool(self.mensagens_ativas() or self.audio)

    def escolher_mensagem(self):
        """
        Escolhe a próxima variação em rodízio (1→2→3→1...).
        Assim não manda sempre o mesmo texto.
        """
        msgs = self.mensagens_ativas()
        if not msgs:
            return None
        idx = self.ultima_variacao % len(msgs)
        escolhida = msgs[idx]
        self.ultima_variacao = (idx + 1) % len(msgs)
        self.save(update_fields=["ultima_variacao", "atualizado_em"])
        return escolhida


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
