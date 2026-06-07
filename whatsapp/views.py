"""
Views de conexão WhatsApp e webhook de mensagens.
"""

import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django.contrib.auth.models import User

from .message_handler import MessageHandler
from .models import WhatsAppConnection
from .services import WhatsAppService

logger = logging.getLogger(__name__)


@login_required
def connection_view(request):
    """Página de conexão WhatsApp com QR Code."""
    connection, _ = WhatsAppConnection.objects.get_or_create(user=request.user)
    service = WhatsAppService()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "connect":
            result = service.connect(request.user.id)
            if result.get("success"):
                connection.status = "aguardando_qr"
                if result.get("qrCode"):
                    connection.qr_code = result["qrCode"]
                connection.save()
                messages.info(request, "Escaneie o QR Code com seu WhatsApp.")
            else:
                messages.error(request, result.get("error", "Erro ao conectar."))

        elif action == "disconnect":
            result = service.disconnect(request.user.id)
            connection.status = "desconectado"
            connection.qr_code = ""
            connection.numero_telefone = ""
            connection.save()
            messages.success(request, "WhatsApp desconectado com sucesso.")

        return redirect("whatsapp:connection")

    # Atualiza status em tempo real
    status_result = service.get_status(request.user.id)
    if status_result.get("success"):
        connection.status = status_result.get("status", connection.status)
        if status_result.get("qrCode"):
            connection.qr_code = status_result["qrCode"]
        if status_result.get("phone"):
            connection.numero_telefone = status_result["phone"]
        connection.save()

    return render(request, "whatsapp/connection.html", {
        "connection": connection,
    })


@login_required
def status_api(request):
    """API JSON para polling do status da conexão."""
    connection, _ = WhatsAppConnection.objects.get_or_create(user=request.user)
    service = WhatsAppService()
    result = service.get_status(request.user.id)

    if result.get("success"):
        connection.status = result.get("status", connection.status)
        if result.get("qrCode"):
            connection.qr_code = result["qrCode"]
        if result.get("phone"):
            connection.numero_telefone = result["phone"]
        connection.save()

    return JsonResponse({
        "status": connection.status,
        "status_display": connection.get_status_display(),
        "qr_code": connection.qr_code,
        "phone": connection.numero_telefone,
    })


@csrf_exempt
@require_POST
def webhook_view(request):
    """
    Webhook recebido do serviço Baileys.
    Processa mensagens recebidas e atualiza status de conexão.
    """
    # Valida secret
    secret = request.headers.get("X-API-Secret", "")
    if secret != settings.WHATSAPP_SERVICE_SECRET:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    event_type = data.get("type")
    user_id = data.get("userId")

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    connection, _ = WhatsAppConnection.objects.get_or_create(user=user)

    if event_type == "connection.update":
        connection.status = data.get("status", connection.status)
        if data.get("phone"):
            connection.numero_telefone = data["phone"]
        if data.get("qrCode"):
            connection.qr_code = data["qrCode"]
        connection.save()

    elif event_type == "message.received":
        telefone = data.get("from", "")
        conteudo = data.get("message", "")
        contato_nome = data.get("pushName", "")
        jid = data.get("jid", "")

        handler = MessageHandler(user)
        handler.process_incoming_message(telefone, conteudo, contato_nome, jid=jid)

    return JsonResponse({"success": True})
