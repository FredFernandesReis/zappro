from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from autorespostas.models import AutoResposta
from subscriptions.models import Plan, Subscription

from .message_handler import MessageHandler
from .models import Mensagem


class MessageHandlerProtectionTests(TestCase):
    def setUp(self):
        self.plan = Plan.objects.create(
            nome="Mensal",
            slug="basico",
            max_respostas=0,
            permite_horario=True,
            permite_boas_vindas=True,
            preco_mensal=Decimal("29.90"),
            ativo=True,
        )
        self.user = User.objects.create_user("cliente", password="teste123")
        Subscription.objects.update_or_create(
            user=self.user,
            defaults={
                "plan": self.plan,
                "status": "ativo",
                "data_vencimento": timezone.localdate() + timedelta(days=30),
            },
        )
        self.handler = MessageHandler(self.user)

    def test_keyword_accepts_number_and_text_aliases(self):
        AutoResposta.objects.create(
            user=self.user,
            palavra_chave="1 | preço",
            resposta="O corte custa R$ 45.",
        )

        self.assertEqual(
            self.handler._buscar_resposta_palavra_chave("1"),
            "O corte custa R$ 45.",
        )
        self.assertEqual(
            self.handler._buscar_resposta_palavra_chave("Qual é o preço?"),
            "O corte custa R$ 45.",
        )
        self.assertEqual(
            self.handler._buscar_resposta_palavra_chave("Quais são os preços?"),
            "O corte custa R$ 45.",
        )
        self.assertIsNone(
            self.handler._buscar_resposta_palavra_chave("Meu telefone é 31999999999")
        )

    @override_settings(AUTORESPOSTA_COOLDOWN_CONTATO_SEGUNDOS=15)
    def test_blocks_burst_for_same_contact(self):
        Mensagem.objects.create(
            user=self.user,
            direcao="enviada",
            conteudo="Resposta anterior",
            telefone_destino="5531999999999",
            tipo_resposta="palavra_chave",
        )

        permitido, motivo = self.handler._pode_enviar_autoresposta(
            "5531999999999", "Outra resposta"
        )

        self.assertFalse(permitido)
        self.assertIn("cooldown", motivo)

    @override_settings(
        AUTORESPOSTA_COOLDOWN_CONTATO_SEGUNDOS=0,
        AUTORESPOSTA_REPETIDA_INTERVALO_MINUTOS=5,
    )
    def test_blocks_repeated_response(self):
        Mensagem.objects.create(
            user=self.user,
            direcao="enviada",
            conteudo="Nosso horário é de 9h às 18h.",
            telefone_destino="5531888888888",
            tipo_resposta="palavra_chave",
        )

        permitido, motivo = self.handler._pode_enviar_autoresposta(
            "5531888888888", "Nosso horário é de 9h às 18h."
        )

        self.assertFalse(permitido)
        self.assertIn("repetida", motivo)
