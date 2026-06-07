"""
Admin de conexões WhatsApp e mensagens.
"""

from django.contrib import admin

from .models import ContatoAtendido, Mensagem, WhatsAppConnection


@admin.register(WhatsAppConnection)
class WhatsAppConnectionAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "numero_telefone", "conectado_em", "atualizado_em")
    list_filter = ("status",)
    search_fields = ("user__username", "numero_telefone")


@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ("user", "direcao", "conteudo", "telefone_origem", "tipo_resposta", "criado_em")
    list_filter = ("direcao", "tipo_resposta")
    search_fields = ("conteudo", "user__username")
    date_hierarchy = "criado_em"


@admin.register(ContatoAtendido)
class ContatoAtendidoAdmin(admin.ModelAdmin):
    list_display = ("user", "telefone", "primeira_mensagem_em")
    search_fields = ("telefone", "user__username")
