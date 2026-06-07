"""
Views do dashboard principal.
"""

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render

from autorespostas.models import AutoResposta
from whatsapp.models import Mensagem, WhatsAppConnection


@login_required
def home_view(request):
    """Dashboard com métricas do usuário."""
    user = request.user

    mensagens_recebidas = Mensagem.objects.filter(user=user, direcao="recebida").count()
    mensagens_enviadas = Mensagem.objects.filter(user=user, direcao="enviada").count()
    total_respostas = AutoResposta.objects.filter(user=user).count()
    respostas_ativas = AutoResposta.objects.filter(user=user, status="ativa").count()

    connection = WhatsAppConnection.objects.filter(user=user).first()
    subscription = getattr(user, "subscription", None)

    # Mensagens recentes
    mensagens_recentes = Mensagem.objects.filter(user=user).order_by("-criado_em")[:10]

    context = {
        "mensagens_recebidas": mensagens_recebidas,
        "mensagens_enviadas": mensagens_enviadas,
        "total_respostas": total_respostas,
        "respostas_ativas": respostas_ativas,
        "connection": connection,
        "subscription": subscription,
        "mensagens_recentes": mensagens_recentes,
    }

    return render(request, "dashboard/home.html", context)
