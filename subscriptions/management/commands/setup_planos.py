"""
Comando para criar planos padrão e superusuário inicial.
Uso: python manage.py setup_planos

Apenas o plano Mensal (R$ 29,90) fica ativo.
Contas comuns ficam pendentes até pagar na Cakto.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import UserProfile
from subscriptions.models import Plan, Subscription


class Command(BaseCommand):
    help = "Cria plano Mensal R$ 29,90 e superusuário admin"

    def handle(self, *args, **options):
        Plan.objects.exclude(slug="basico").update(ativo=False)
        self.stdout.write("Planos antigos desativados.")

        plan, created = Plan.objects.update_or_create(
            slug="basico",
            defaults={
                "nome": "Mensal",
                "descricao": "Plano mensal completo: WhatsApp, respostas ilimitadas, horário e boas-vindas.",
                "max_whatsapp": 1,
                "max_respostas": 0,
                "permite_horario": True,
                "permite_boas_vindas": True,
                "preco_mensal": Decimal("29.90"),
                "ativo": True,
                "ordem": 1,
            },
        )
        status = "criado" if created else "atualizado"
        self.stdout.write(f"Plano {plan.nome} R$ {plan.preco_mensal} {status}.")

        # Todas as assinaturas apontam ao Mensal, mas NÃO ficam liberadas
        hoje = timezone.localdate()
        pendentes = (
            Subscription.objects.exclude(user__is_staff=True)
            .exclude(user__is_superuser=True)
            .update(plan=plan, status="suspenso", data_vencimento=hoje)
        )
        self.stdout.write(
            f"{pendentes} assinatura(s) de clientes marcadas como pendentes (aguardam Cakto)."
        )

        if not User.objects.filter(username="admin").exists():
            admin = User.objects.create_superuser(
                username="admin",
                email="admin@zappro.com.br",
                password="admin123",
            )
            UserProfile.objects.get_or_create(user=admin)
            Subscription.objects.create(
                user=admin,
                plan=plan,
                status="ativo",
                data_vencimento=hoje + timedelta(days=365),
            )
            self.stdout.write(self.style.SUCCESS("Superusuário criado: admin / admin123"))
        else:
            self.stdout.write("Superusuário 'admin' já existe.")
            admin = User.objects.get(username="admin")
            Subscription.objects.update_or_create(
                user=admin,
                defaults={
                    "plan": plan,
                    "status": "ativo",
                    "data_vencimento": hoje + timedelta(days=365),
                },
            )

        self.stdout.write(self.style.SUCCESS("Setup concluído!"))
