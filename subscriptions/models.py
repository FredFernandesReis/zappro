"""
Models de planos e assinaturas.
Integração Cakto para pagamento automático.
"""

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Plan(models.Model):
    """Planos disponíveis no sistema."""

    SLUG_CHOICES = [
        ("gratuito", "Gratuito"),
        ("basico", "Básico"),
        ("premium", "Premium"),
    ]

    nome = models.CharField("Nome", max_length=50)
    slug = models.SlugField("Slug", max_length=20, unique=True, choices=SLUG_CHOICES)
    descricao = models.TextField("Descrição", blank=True)
    max_whatsapp = models.PositiveIntegerField("Máx. WhatsApp", default=1)
    max_respostas = models.PositiveIntegerField(
        "Máx. Respostas Automáticas", default=10, help_text="0 = ilimitado"
    )
    permite_horario = models.BooleanField("Permite Horário de Atendimento", default=False)
    permite_boas_vindas = models.BooleanField("Permite Mensagem de Boas-Vindas", default=True)
    preco_mensal = models.DecimalField("Preço Mensal (R$)", max_digits=8, decimal_places=2, default=0)
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Plano"
        verbose_name_plural = "Planos"
        ordering = ["ordem"]

    def __str__(self):
        return self.nome

    @property
    def respostas_ilimitadas(self):
        return self.max_respostas == 0


class Subscription(models.Model):
    """Assinatura vinculada a cada usuário."""

    STATUS_CHOICES = [
        ("ativo", "Ativo"),
        ("suspenso", "Suspenso"),
        ("cancelado", "Cancelado"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="assinaturas")
    status = models.CharField("Situação", max_length=20, choices=STATUS_CHOICES, default="ativo")
    data_vencimento = models.DateField("Data de Vencimento")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    cakto_customer_email = models.EmailField("E-mail Cakto", blank=True)
    cakto_order_id = models.CharField("Último pedido Cakto", max_length=100, blank=True)
    cakto_subscription_id = models.CharField("Assinatura Cakto", max_length=100, blank=True)
    cakto_last_event = models.CharField("Último evento Cakto", max_length=80, blank=True)

    class Meta:
        verbose_name = "Assinatura"
        verbose_name_plural = "Assinaturas"

    def __str__(self):
        return f"{self.user.username} - {self.plan.nome}"

    @property
    def esta_ativa(self):
        if self.status != "ativo":
            return False
        return self.data_vencimento >= timezone.now().date()

    @property
    def esta_vencida(self):
        return self.data_vencimento < timezone.now().date()

    @property
    def dias_restantes(self):
        delta = self.data_vencimento - timezone.now().date()
        return max(delta.days, 0)


class CaktoWebhookLog(models.Model):
    """Log de eventos recebidos da Cakto (auditoria / debug)."""

    event = models.CharField(max_length=80)
    payload = models.JSONField(default=dict)
    processado = models.BooleanField(default=False)
    detalhe = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Log Webhook Cakto"
        verbose_name_plural = "Logs Webhook Cakto"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.event} ({self.criado_em:%d/%m %H:%M})"
