"""
Models de conexão WhatsApp e mensagens.
Preparado para futura integração com WhatsApp API Oficial.
"""

from django.contrib.auth.models import User
from django.db import models


class WhatsAppConnection(models.Model):
    """Status da conexão WhatsApp de cada usuário."""

    STATUS_CHOICES = [
        ("conectado", "Conectado"),
        ("desconectado", "Desconectado"),
        ("aguardando_qr", "Aguardando QR Code"),
        ("conectando", "Conectando"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="whatsapp_connection"
    )
    status = models.CharField(
        "Status", max_length=20, choices=STATUS_CHOICES, default="desconectado"
    )
    numero_telefone = models.CharField("Número", max_length=20, blank=True)
    nome_perfil = models.CharField("Nome do Perfil", max_length=100, blank=True)
    qr_code = models.TextField("QR Code (base64)", blank=True)
    conectado_em = models.DateTimeField("Conectado em", null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    # Futura integração WhatsApp API Oficial
    # official_api_token = models.CharField(max_length=255, blank=True)
    # official_phone_id = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Conexão WhatsApp"
        verbose_name_plural = "Conexões WhatsApp"

    def __str__(self):
        return f"WhatsApp de {self.user.username} - {self.get_status_display()}"

    @property
    def session_path(self):
        """Caminho da sessão Baileys para este usuário."""
        return f"usuario_{self.user.id}"


class Mensagem(models.Model):
    """Registro de mensagens enviadas e recebidas."""

    DIRECAO_CHOICES = [
        ("recebida", "Recebida"),
        ("enviada", "Enviada"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mensagens")
    direcao = models.CharField("Direção", max_length=10, choices=DIRECAO_CHOICES)
    conteudo = models.TextField("Conteúdo")
    telefone_origem = models.CharField("Telefone Origem", max_length=20, blank=True)
    telefone_destino = models.CharField("Telefone Destino", max_length=20, blank=True)
    contato_nome = models.CharField("Nome do Contato", max_length=100, blank=True)
    tipo_resposta = models.CharField(
        "Tipo de Resposta",
        max_length=30,
        blank=True,
        help_text="palavra_chave, boas_vindas, fora_horario, manual",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mensagem"
        verbose_name_plural = "Mensagens"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.get_direcao_display()} - {self.user.username} - {self.criado_em}"


class ContatoAtendido(models.Model):
    """Controle de contatos que já receberam boas-vindas."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="contatos_atendidos")
    telefone = models.CharField(max_length=20)
    primeira_mensagem_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Contato Atendido"
        verbose_name_plural = "Contatos Atendidos"
        unique_together = ("user", "telefone")

    def __str__(self):
        return f"{self.telefone} ({self.user.username})"
