"""
Admin de planos e assinaturas.
"""

from django.contrib import admin

from .models import Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "max_whatsapp", "max_respostas", "preco_mensal", "ativo")
    list_filter = ("ativo",)
    prepopulated_fields = {"slug": ("nome",)}


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "data_vencimento", "esta_ativa", "criado_em")
    list_filter = ("status", "plan")
    search_fields = ("user__username", "user__email")
    date_hierarchy = "data_vencimento"
    raw_id_fields = ("user",)
