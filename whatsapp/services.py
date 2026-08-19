"""
Serviço de comunicação com o microserviço Baileys (Node.js).
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Cliente HTTP para o serviço WhatsApp Baileys."""

    def __init__(self):
        self.base_url = settings.WHATSAPP_SERVICE_URL
        self.secret = settings.WHATSAPP_SERVICE_SECRET
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Secret": self.secret,
        }

    def _request(self, method, endpoint, data=None, timeout=30):
        """Executa requisição ao serviço Node.js."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(
                method, url, json=data, headers=self.headers, timeout=timeout
            )
            try:
                payload = response.json()
            except ValueError:
                payload = {"success": False, "error": response.text[:200]}

            if response.status_code >= 400:
                logger.error(
                    "WhatsApp service %s %s -> %s: %s",
                    method, endpoint, response.status_code, payload,
                )
                return {
                    "success": False,
                    "error": payload.get("error") or f"HTTP {response.status_code}",
                }

            return payload
        except requests.exceptions.ConnectionError:
            logger.error("Serviço WhatsApp indisponível em %s", url)
            return {"success": False, "error": "Serviço WhatsApp indisponível. Verifique se o Node.js está rodando."}
        except requests.exceptions.RequestException as e:
            logger.error("Erro na requisição WhatsApp: %s", e)
            return {"success": False, "error": str(e)}

    def connect(self, user_id):
        """Inicia conexão e gera QR Code."""
        return self._request("POST", "/connect", {"userId": user_id})

    def disconnect(self, user_id):
        """Desconecta sessão WhatsApp."""
        return self._request("POST", "/disconnect", {"userId": user_id})

    def get_status(self, user_id):
        """Obtém status da conexão."""
        return self._request("GET", f"/status/{user_id}", timeout=5)

    def send_message(
        self,
        user_id,
        phone,
        message,
        jid=None,
        delay_seconds=0,
        show_typing=False,
        audio_path="",
    ):
        """Envia texto e, opcionalmente, áudio leve via WhatsApp."""
        delay = max(int(delay_seconds or 0), 0)
        payload = {
            "userId": user_id,
            "phone": phone,
            "message": message or "",
            "delaySeconds": delay,
            "showTyping": bool(show_typing),
        }
        if jid:
            payload["jid"] = jid
        if audio_path:
            payload["audioPath"] = audio_path
            payload["audioPtt"] = True
        # digitando mínimo ~3s no Node + margem de rede
        timeout = max(45, delay + 35)
        return self._request("POST", "/send", payload, timeout=timeout)
