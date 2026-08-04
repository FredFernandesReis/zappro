"""
Comando para criar planos padrão e superusuário inicial.
Uso: python manage.py setup_planos

Apenas o plano Mensal (R$ 29,90) fica ativo para venda/exibição.
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
        # Desativa planos antigos (não apaga — assinaturas podem referenciar)
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

        # Migra assinaturas ativas para o Mensal e estende vencimento (ambiente de teste)
        venc = timezone.now().date() + timedelta(days=90)
        atualizadas = Subscription.objects.update(plan=plan, status="ativo", data_vencimento=venc)
        self.stdout.write(f"{atualizadas} assinatura(s) apontando para Mensal até {venc}.")

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
                data_vencimento=timezone.now().date() + timedelta(days=365),
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
                    "data_vencimento": timezone.now().date() + timedelta(days=365),
                },
            )

        self.stdout.write(self.style.SUCCESS("Setup concluído!"))
