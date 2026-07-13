"""
Utilitários para verificar benefícios e limites do plano do usuário.
"""

from subscriptions.models import Plan


def get_active_plan(user):
    """Retorna o plano do usuário se a assinatura estiver ativa."""
    if user.is_staff:
        subscription = getattr(user, "subscription", None)
        if subscription and subscription.plan:
            return subscription.plan
        return Plan.objects.filter(slug="premium").first()

    subscription = getattr(user, "subscription", None)
    if subscription and subscription.esta_ativa:
        return subscription.plan
    return None


def get_plan_for_limits(user):
    """Plano usado para limites de cadastro (fallback: gratuito)."""
    plan = get_active_plan(user)
    if plan:
        return plan
    return Plan.objects.filter(slug="gratuito").first()


def can_create_autoresposta(user):
    """Verifica se o usuário pode criar mais uma resposta automática."""
    plan = get_plan_for_limits(user)
    if not plan:
        return False, "Nenhum plano disponível."

    if plan.respostas_ilimitadas:
        return True, None

    from autorespostas.models import AutoResposta

    count = AutoResposta.objects.filter(user=user).count()
    if count >= plan.max_respostas:
        return False, plan.max_respostas
    return True, None


def plan_allows_horario(plan):
    return bool(plan and plan.permite_horario)


def plan_allows_boas_vindas(plan):
    return bool(plan and plan.permite_boas_vindas)
