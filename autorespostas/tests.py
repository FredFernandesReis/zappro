from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from subscriptions.models import Plan, Subscription

from .models import AutoResposta, ConfiguracaoBoasVindas


class ModelosProntosTests(TestCase):
    def setUp(self):
        plan = Plan.objects.create(
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
                "plan": plan,
                "status": "ativo",
                "data_vencimento": timezone.localdate() + timedelta(days=30),
            },
        )
        self.client.force_login(self.user)

    def test_aplica_modelo_com_respostas_e_boas_vindas(self):
        response = self.client.post(
            reverse("autorespostas:modelos"),
            {"modelo": "barbearia"},
        )

        self.assertRedirects(response, reverse("autorespostas:list"))
        self.assertEqual(AutoResposta.objects.filter(user=self.user).count(), 5)
        config = ConfiguracaoBoasVindas.objects.get(user=self.user)
        self.assertTrue(config.ativo)
        self.assertEqual(len(config.mensagens_ativas()), 3)

    def test_reaplicar_modelo_atualiza_sem_duplicar(self):
        url = reverse("autorespostas:modelos")
        self.client.post(url, {"modelo": "loja"})
        self.client.post(url, {"modelo": "loja"})

        self.assertEqual(AutoResposta.objects.filter(user=self.user).count(), 5)
