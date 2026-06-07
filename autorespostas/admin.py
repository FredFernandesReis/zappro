"""
Admin de respostas automáticas.
"""

from django.contrib import admin

from .models import AutoResposta, ConfiguracaoBoasVindas, ConfiguracaoHorario


@admin.register(AutoResposta)
class AutoRespostaAdmin(admin.ModelAdmin):
    list_display = ("palavra_chave", "user", "status", "criado_em")
    list_filter = ("status",)
    search_fields = ("palavra_chave", "user__username")


@admin.register(ConfiguracaoBoasVindas)
class ConfiguracaoBoasVindasAdmin(admin.ModelAdmin):
    list_display = ("user", "ativo", "atualizado_em")


@admin.register(ConfiguracaoHorario)
class ConfiguracaoHorarioAdmin(admin.ModelAdmin):
    list_display = ("user", "ativo", "hora_inicial", "hora_final")
