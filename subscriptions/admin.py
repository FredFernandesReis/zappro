"""
Admin de planos e assinaturas.
"""

from django.contrib import admin

from .models import CaktoWebhookLog, Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "max_whatsapp", "max_respostas", "preco_mensal", "ativo")
    list_filter = ("ativo",)
    prepopulated_fields = {"slug": ("nome",)}


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "plan",
        "status",
        "data_vencimento",
        "esta_ativa",
        "cakto_order_id",
        "criado_em",
    )
    list_filter = ("status", "plan")
    search_fields = ("user__username", "user__email", "cakto_customer_email", "cakto_order_id")
    date_hierarchy = "data_vencimento"
    raw_id_fields = ("user",)


@admin.register(CaktoWebhookLog)
class CaktoWebhookLogAdmin(admin.ModelAdmin):
    list_display = ("event", "processado", "detalhe", "criado_em")
    list_filter = ("event", "processado")
    readonly_fields = ("event", "payload", "processado", "detalhe", "criado_em")
