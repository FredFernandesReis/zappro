"""
Views do dashboard principal e páginas públicas.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from autorespostas.models import AutoResposta, ConfiguracaoBoasVindas
from whatsapp.models import Mensagem, WhatsAppConnection


def landing_view(request):
    """Página inicial pública do ZapPro."""
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    return render(request, "dashboard/landing.html")


def ajuda_view(request):
    """FAQ e ajuda — pública e também no painel."""
    return render(request, "dashboard/ajuda.html")


@login_required
def home_view(request):
    """Dashboard com métricas do usuário e checklist de onboarding."""
    user = request.user

    mensagens_recebidas = Mensagem.objects.filter(user=user, direcao="recebida").count()
    mensagens_enviadas = Mensagem.objects.filter(user=user, direcao="enviada").count()
    total_respostas = AutoResposta.objects.filter(user=user).count()
    respostas_ativas = AutoResposta.objects.filter(user=user, status="ativa").count()

    connection = WhatsAppConnection.objects.filter(user=user).first()
    subscription = getattr(user, "subscription", None)
    boas_vindas = ConfiguracaoBoasVindas.objects.filter(user=user).first()

    whatsapp_ok = bool(connection and connection.status == "conectado")
    resposta_ok = total_respostas > 0
    boas_vindas_ok = bool(boas_vindas and boas_vindas.ativo)
    onboarding_completo = whatsapp_ok and resposta_ok

    onboarding_steps = [
        {
            "titulo": "Conectar o WhatsApp",
            "descricao": "Escaneie o QR Code para vincular seu número.",
            "done": whatsapp_ok,
            "url": "whatsapp:connection",
            "cta": "Conectar agora",
        },
        {
            "titulo": "Criar a primeira resposta",
            "descricao": "Defina uma palavra-chave e a mensagem automática.",
            "done": resposta_ok,
            "url": "autorespostas:create",
            "cta": "Criar resposta",
        },
        {
            "titulo": "Ativar boas-vindas (opcional)",
            "descricao": "Mensagem automática no primeiro contato do cliente.",
            "done": boas_vindas_ok,
            "url": "autorespostas:boas_vindas",
            "cta": "Configurar",
            "opcional": True,
        },
    ]

    mensagens_recentes = Mensagem.objects.filter(user=user).order_by("-criado_em")[:10]

    context = {
        "mensagens_recebidas": mensagens_recebidas,
        "mensagens_enviadas": mensagens_enviadas,
        "total_respostas": total_respostas,
        "respostas_ativas": respostas_ativas,
        "connection": connection,
        "subscription": subscription,
        "mensagens_recentes": mensagens_recentes,
        "onboarding_steps": onboarding_steps,
        "onboarding_completo": onboarding_completo,
        "onboarding_progress": sum(1 for s in onboarding_steps if s["done"]),
        "onboarding_total": len(onboarding_steps),
    }

    return render(request, "dashboard/home.html", context)
