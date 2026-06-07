"""
Signals para criar perfil e assinatura automaticamente.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Cria perfil automaticamente ao criar usuário."""
    if created:
        UserProfile.objects.get_or_create(user=instance)

        # Cria assinatura gratuita (exceto superusuários criados via admin)
        if not instance.is_superuser:
            from subscriptions.models import Plan, Subscription

            plano = Plan.objects.filter(slug="gratuito").first()
            if plano:
                Subscription.objects.get_or_create(
                    user=instance,
                    defaults={
                        "plan": plano,
                        "status": "ativo",
                        "data_vencimento": timezone.now().date() + timedelta(days=30),
                    },
                )
