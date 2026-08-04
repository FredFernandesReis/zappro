"""
Signals para criar perfil e assinatura pendente (só libera após pagamento Cakto).
"""

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Cria perfil. Contas novas ficam sem acesso até pagar na Cakto."""
    if created:
        UserProfile.objects.get_or_create(user=instance)

        if not instance.is_superuser and not instance.is_staff:
            from subscriptions.models import Plan, Subscription

            plano = Plan.objects.filter(slug="basico", ativo=True).first()
            if plano:
                Subscription.objects.get_or_create(
                    user=instance,
                    defaults={
                        "plan": plano,
                        "status": "suspenso",
                        # vencido: exige pagamento para ativar
                        "data_vencimento": timezone.localdate(),
                    },
                )
