"""
Lógica de processamento de mensagens recebidas e envio de autorespostas.
"""

import logging
import random
import re
import unicodedata
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from autorespostas.models import AutoResposta, ConfiguracaoBoasVindas, ConfiguracaoHorario
from subscriptions.plan_utils import get_active_plan, plan_allows_boas_vindas, plan_allows_horario

from .models import ContatoAtendido, Mensagem, WhatsAppConnection
from .services import WhatsAppService

logger = logging.getLogger(__name__)


def _normalizar(texto):
    """minúsculas sem acento — 'Preço' e 'preco' batem igualmente."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto).lower().strip())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


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
        """Busca resposta por palavra-chave ou alias separado por ``|``."""
        texto_norm = _normalizar(texto)
        respostas = AutoResposta.objects.filter(user=self.user, status="ativa")

        for resposta in respostas:
            aliases = re.split(r"[|;,]+", resposta.palavra_chave)
            for alias in aliases:
                chave = _normalizar(alias)
                if not chave:
                    continue
                # Evita falsos positivos: alias "1" não dispara dentro de telefone,
                # e "preço" não dispara dentro de outra palavra.
                plural = "" if chave.endswith("s") or chave.isdigit() else "s?"
                padrao = rf"(?<!\w){re.escape(chave)}{plural}(?!\w)"
                if re.search(padrao, texto_norm):
                    return resposta.resposta
        return None

    def _pode_enviar_autoresposta(self, telefone, resposta_texto):
        """
        Impede rajadas e repetições para o mesmo contato.

        Isso reduz respostas duplicadas quando o cliente envia várias mensagens
        seguidas, sem bloquear conversas normais depois do intervalo.
        """
        agora = timezone.now()
        enviadas = Mensagem.objects.filter(
            user=self.user,
            direcao="enviada",
            telefone_destino=telefone,
        )

        cooldown = max(
            int(getattr(settings, "AUTORESPOSTA_COOLDOWN_CONTATO_SEGUNDOS", 15)),
            0,
        )
        ultima = enviadas.first()
        if ultima and cooldown:
            decorrido = (agora - ultima.criado_em).total_seconds()
            if decorrido < cooldown:
                return False, f"cooldown de {cooldown}s"

        repetida_minutos = max(
            int(getattr(settings, "AUTORESPOSTA_REPETIDA_INTERVALO_MINUTOS", 5)),
            0,
        )
        if repetida_minutos and enviadas.filter(
            conteudo=resposta_texto,
            criado_em__gte=agora - timedelta(minutes=repetida_minutos),
        ).exists():
            return False, f"resposta repetida em {repetida_minutos}min"

        max_hora = max(
            int(getattr(settings, "AUTORESPOSTA_MAX_POR_CONTATO_HORA", 10)),
            0,
        )
        if max_hora and enviadas.filter(
            criado_em__gte=agora - timedelta(hours=1)
        ).count() >= max_hora:
            return False, f"limite de {max_hora} respostas/hora"

        return True, ""

    def _precisa_boas_vindas(self, telefone):
        """
        Boas-vindas para contato novo ou que ficou sem falar
        pelo intervalo configurado (padrão: 20 minutos).
        """
        if not plan_allows_boas_vindas(self.plan):
            return False, None

        try:
            config = self.user.config_boas_vindas
        except ConfiguracaoBoasVindas.DoesNotExist:
            return False, None

        if not config.ativo:
            return False, None

        intervalo = int(getattr(settings, "BOAS_VINDAS_INTERVALO_MINUTOS", 20))
        contato = ContatoAtendido.objects.filter(user=self.user, telefone=telefone).first()
        if contato:
            decorrido = timezone.now() - contato.primeira_mensagem_em
            if decorrido < timedelta(minutes=max(intervalo, 1)):
                return False, None
            # Passou o intervalo: permite boas-vindas de novo
            contato.delete()

        mensagem = config.escolher_mensagem()
        if not mensagem:
            return False, None
        return True, mensagem

    def _delay_humano(self, texto=""):
        """Atraso aleatório + um pouco mais se a mensagem for longa."""
        base = int(getattr(settings, "AUTORESPOSTA_DELAY_SEGUNDOS", 7))
        variacao = int(getattr(settings, "AUTORESPOSTA_DELAY_VARIACAO_SEGUNDOS", 5))
        base = max(base, 5)
        variacao = max(variacao, 0)
        # ~+1s a cada 70 caracteres, teto +4s (mais tempo "digitando")
        extra = min(max(len(texto or "") // 70, 0), 4)
        return base + extra + random.randint(0, variacao)

    def _registrar_boas_vindas(self, telefone):
        ContatoAtendido.objects.update_or_create(
            user=self.user,
            telefone=telefone,
            defaults={},
        )
        # Garante timestamp atual (auto_now_add não atualiza sozinho)
        ContatoAtendido.objects.filter(user=self.user, telefone=telefone).update(
            primeira_mensagem_em=timezone.now()
        )

    def process_incoming_message(self, telefone, conteudo, contato_nome="", jid=None):
        """
        Processa mensagem recebida e envia resposta automática se aplicável.
        Retorna a resposta enviada ou None.
        """
        # Sempre registra recebida no painel (mesmo sem plano ativo)
        Mensagem.objects.create(
            user=self.user,
            direcao="recebida",
            conteudo=conteudo,
            telefone_origem=telefone,
            contato_nome=contato_nome,
        )

        if not self.plan:
            logger.info(
                "Assinatura inativa — mensagem salva, sem autoresposta (user %s)",
                self.user.id,
            )
            return None

        resposta_texto = None
        tipo_resposta = ""

        if not self._esta_no_horario():
            try:
                config_horario = self.user.config_horario
                resposta_texto = config_horario.mensagem_fora_horario
                tipo_resposta = "fora_horario"
            except ConfiguracaoHorario.DoesNotExist:
                pass

        # Palavra-chave primeiro (ex.: "Preço") — senão boas-vindas engolem o teste
        if not resposta_texto:
            resposta_palavra = self._buscar_resposta_palavra_chave(conteudo)
            if resposta_palavra:
                resposta_texto = resposta_palavra
                tipo_resposta = "palavra_chave"

        if not resposta_texto:
            precisa, mensagem_bv = self._precisa_boas_vindas(telefone)
            if precisa:
                resposta_texto = mensagem_bv
                tipo_resposta = "boas_vindas"

        if resposta_texto:
            pode_enviar, motivo = self._pode_enviar_autoresposta(
                telefone, resposta_texto
            )
            if not pode_enviar:
                logger.info(
                    "Autoresposta ignorada para %s (user %s): %s",
                    telefone,
                    self.user.id,
                    motivo,
                )
                return None

            delay = self._delay_humano(resposta_texto)
            show_typing = getattr(settings, "AUTORESPOSTA_MOSTRAR_DIGITANDO", True)

            result = self.whatsapp_service.send_message(
                self.user.id,
                telefone,
                resposta_texto,
                jid=jid,
                delay_seconds=delay,
                show_typing=show_typing,
            )

            if result.get("success") and result.get("messageId"):
                if tipo_resposta == "boas_vindas":
                    self._registrar_boas_vindas(telefone)

                Mensagem.objects.create(
                    user=self.user,
                    direcao="enviada",
                    conteudo=resposta_texto,
                    telefone_destino=telefone,
                    tipo_resposta=tipo_resposta,
                )
                logger.info(
                    "Autoresposta (%s) enviada para %s (user %s, id %s, delay %ss)",
                    tipo_resposta,
                    telefone,
                    self.user.id,
                    result.get("messageId"),
                    delay,
                )
            else:
                logger.error(
                    "Falha ao enviar autoresposta para %s (user %s): %s",
                    telefone,
                    self.user.id,
                    result.get("error") or "sem confirmação do WhatsApp",
                )
                return None

        return resposta_texto
