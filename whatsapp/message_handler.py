"""
Lógica de processamento de mensagens recebidas e envio de autorespostas.
"""

import logging

from django.conf import settings
from django.utils import timezone

from autorespostas.models import AutoResposta, ConfiguracaoBoasVindas, ConfiguracaoHorario
from subscriptions.plan_utils import get_active_plan, plan_allows_boas_vindas, plan_allows_horario

from .models import ContatoAtendido, Mensagem, WhatsAppConnection
from .services import WhatsAppService

logger = logging.getLogger(__name__)


class MessageHandler:
    """Processa mensagens recebidas e determina respostas automáticas."""

    def __init__(self, user):
        self.user = user
        self.whatsapp_service = WhatsAppService()
        self.plan = get_active_plan(user)

    def _esta_no_horario(self):
        """Verifica se está dentro do horário de atendimento."""
        if not plan_allows_horario(self.plan):
            return True

        try:
            config = self.user.config_horario
        except ConfiguracaoHorario.DoesNotExist:
            return True

        if not config.ativo:
            return True

        agora = timezone.localtime().time()
        return config.hora_inicial <= agora <= config.hora_final

    def _buscar_resposta_palavra_chave(self, texto):
        """Busca resposta automática pela palavra-chave."""
        texto_lower = texto.lower().strip()
        respostas = AutoResposta.objects.filter(user=self.user, status="ativa")

        for resposta in respostas:
            if resposta.palavra_chave.lower() in texto_lower:
                return resposta.resposta
        return None

    def _precisa_boas_vindas(self, telefone):
        """Verifica se o contato ainda não recebeu boas-vindas."""
        if not plan_allows_boas_vindas(self.plan):
            return False, None

        try:
            config = self.user.config_boas_vindas
        except ConfiguracaoBoasVindas.DoesNotExist:
            return False, None

        if not config.ativo:
            return False, None

        if ContatoAtendido.objects.filter(user=self.user, telefone=telefone).exists():
            return False, None

        return True, config.mensagem

    def process_incoming_message(self, telefone, conteudo, contato_nome="", jid=None):
        """
        Processa mensagem recebida e envia resposta automática se aplicável.
        Retorna a resposta enviada ou None.
        """
        if not self.plan:
            logger.info("Assinatura inativa — mensagem ignorada (user %s)", self.user.id)
            return None

        # Registra mensagem recebida
        Mensagem.objects.create(
            user=self.user,
            direcao="recebida",
            conteudo=conteudo,
            telefone_origem=telefone,
            contato_nome=contato_nome,
        )

        resposta_texto = None
        tipo_resposta = ""

        # Verifica horário de atendimento
        if not self._esta_no_horario():
            try:
                config_horario = self.user.config_horario
                resposta_texto = config_horario.mensagem_fora_horario
                tipo_resposta = "fora_horario"
            except ConfiguracaoHorario.DoesNotExist:
                pass

        # Verifica boas-vindas para novos contatos
        if not resposta_texto:
            precisa, mensagem_bv = self._precisa_boas_vindas(telefone)
            if precisa:
                resposta_texto = mensagem_bv
                tipo_resposta = "boas_vindas"
                ContatoAtendido.objects.create(user=self.user, telefone=telefone)

        # Busca resposta por palavra-chave
        if not resposta_texto:
            resposta_palavra = self._buscar_resposta_palavra_chave(conteudo)
            if resposta_palavra:
                resposta_texto = resposta_palavra
                tipo_resposta = "palavra_chave"

        # Envia resposta se encontrada
        if resposta_texto:
            delay = getattr(settings, "AUTORESPOSTA_DELAY_SEGUNDOS", 2)
            show_typing = getattr(settings, "AUTORESPOSTA_MOSTRAR_DIGITANDO", True)

            result = self.whatsapp_service.send_message(
                self.user.id,
                telefone,
                resposta_texto,
                jid=jid,
                delay_seconds=delay,
                show_typing=show_typing,
            )

            if result.get("success"):
                Mensagem.objects.create(
                    user=self.user,
                    direcao="enviada",
                    conteudo=resposta_texto,
                    telefone_destino=telefone,
                    tipo_resposta=tipo_resposta,
                )
                logger.info(
                    "Autoresposta (%s) enviada para %s (user %s)",
                    tipo_resposta, telefone, self.user.id,
                )
            else:
                logger.error("Falha ao enviar autoresposta: %s", result.get("error"))

        return resposta_texto
