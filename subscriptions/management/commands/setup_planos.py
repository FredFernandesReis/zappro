"""
Comando para criar planos padrão e superusuário inicial.
Uso: python manage.py setup_planos
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import UserProfile
from subscriptions.models import Plan, Subscription


class Command(BaseCommand):
    help = "Cria planos padrão e superusuário admin"

    def handle(self, *args, **options):
        planos = [
            {
                "nome": "Gratuito",
                "slug": "gratuito",
                "descricao": "Ideal para começar. 1 WhatsApp e até 10 respostas automáticas.",
                "max_whatsapp": 1,
                "max_respostas": 10,
                "permite_horario": False,
                "permite_boas_vindas": True,
                "preco_mensal": 0,
                "ordem": 1,
            },
            {
                "nome": "Básico",
                "slug": "basico",
                "descricao": "Respostas ilimitadas e horário de atendimento.",
                "max_whatsapp": 1,
                "max_respostas": 0,
                "permite_horario": True,
                "permite_boas_vindas": True,
                "preco_mensal": 29.90,
                "ordem": 2,
            },
            {
                "nome": "Premium",
                "slug": "premium",
                "descricao": "Todas as funcionalidades do ZapPro.",
                "max_whatsapp": 3,
                "max_respostas": 0,
                "permite_horario": True,
                "permite_boas_vindas": True,
                "preco_mensal": 59.90,
                "ordem": 3,
            },
        ]

        for plano_data in planos:
            plan, created = Plan.objects.update_or_create(
                slug=plano_data["slug"],
                defaults=plano_data,
            )
            status = "criado" if created else "atualizado"
            self.stdout.write(f"Plano {plan.nome} {status}.")

        # Cria superusuário se não existir
        if not User.objects.filter(username="admin").exists():
            admin = User.objects.create_superuser(
                username="admin",
                email="admin@zappro.com.br",
                password="admin123",
            )
            UserProfile.objects.get_or_create(user=admin)

            plano_premium = Plan.objects.get(slug="premium")
            Subscription.objects.create(
                user=admin,
                plan=plano_premium,
                status="ativo",
                data_vencimento=timezone.now().date() + timedelta(days=365),
            )
            self.stdout.write(self.style.SUCCESS(
                "Superusuário criado: admin / admin123"
            ))
        else:
            self.stdout.write("Superusuário 'admin' já existe.")

        self.stdout.write(self.style.SUCCESS("Setup concluído!"))
