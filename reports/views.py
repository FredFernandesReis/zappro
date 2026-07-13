"""
Views de relatórios - usuário e administrador.
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from subscriptions.models import Subscription
from whatsapp.models import Mensagem, WhatsAppConnection


@login_required
def user_reports_view(request):
    """Relatórios do usuário logado."""
    user = request.user
    mensagens = Mensagem.objects.filter(user=user)

    recebidas = mensagens.filter(direcao="recebida").count()
    enviadas = mensagens.filter(direcao="enviada").count()

    # Mensagens por tipo de resposta
    por_tipo = (
        mensagens.filter(direcao="enviada")
        .exclude(tipo_resposta="")
        .values("tipo_resposta")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    # Últimas 50 mensagens
    historico = mensagens.order_by("-criado_em")[:50]

    return render(request, "reports/user_reports.html", {
        "recebidas": recebidas,
        "enviadas": enviadas,
        "por_tipo": por_tipo,
        "historico": historico,
    })


@staff_member_required
def admin_reports_view(request):
    """Relatórios administrativos do sistema."""
    hoje = timezone.now().date()

    total_usuarios = User.objects.filter(is_staff=False).count()
    usuarios_ativos = Subscription.objects.filter(
        status="ativo", data_vencimento__gte=hoje
    ).count()
    usuarios_vencidos = Subscription.objects.filter(
        data_vencimento__lt=hoje
    ).count()

    mensagens_recebidas = Mensagem.objects.filter(direcao="recebida").count()
    mensagens_enviadas = Mensagem.objects.filter(direcao="enviada").count()

    conexoes_ativas = WhatsAppConnection.objects.filter(status="conectado").count()
    conexoes_total = WhatsAppConnection.objects.count()

    # Top usuários por mensagens
    top_usuarios = (
        User.objects.filter(is_staff=False)
        .annotate(total_msgs=Count("mensagens"))
        .order_by("-total_msgs")[:10]
    )

    return render(request, "reports/admin_reports.html", {
        "total_usuarios": total_usuarios,
        "usuarios_ativos": usuarios_ativos,
        "usuarios_vencidos": usuarios_vencidos,
        "mensagens_recebidas": mensagens_recebidas,
        "mensagens_enviadas": mensagens_enviadas,
        "conexoes_ativas": conexoes_ativas,
        "conexoes_total": conexoes_total,
        "top_usuarios": top_usuarios,
    })
