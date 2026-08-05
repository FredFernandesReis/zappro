"""
Assistente de IA para sugerir respostas automáticas (OpenAI).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um assistente do ZapPro, sistema de autoresposta para WhatsApp de pequenos negócios no Brasil.
Sua função é criar respostas automáticas por palavra-chave a partir da descrição do negócio do usuário.

Regras:
- Responda APENAS com JSON válido (sem markdown).
- Use português brasileiro, tom simpático e profissional.
- Cada palavra-chave deve ser curta (1-3 palavras), sem acento opcional mas pode ter.
- Crie entre 3 e 8 respostas úteis (preço, horário, endereço, agendamento, etc. quando fizer sentido).
- Não invente preços/horários/endereços se o usuário não informou; peça contato/WhatsApp de forma genérica.
- Inclua uma sugestão de mensagem de boas-vindas no campo boas_vindas.

Formato exato:
{
  "resumo": "frase curta do que entendeu",
  "boas_vindas": "texto da boas-vindas",
  "respostas": [
    {"palavra_chave": "preço", "resposta": "texto..."},
    {"palavra_chave": "horário", "resposta": "texto..."}
  ]
}
"""


def ai_configured() -> bool:
    return bool(getattr(settings, "OPENAI_API_KEY", ""))


def _extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("Resposta vazia da IA")

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.I)
    if fence:
        text = fence.group(1).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("IA não retornou JSON válido")
        data = json.loads(text[start : end + 1])

    if not isinstance(data, dict):
        raise ValueError("JSON inválido")
    return data


def _normalize_suggestions(data: dict[str, Any]) -> dict[str, Any]:
    respostas_raw = data.get("respostas") or data.get("suggestions") or []
    itens = []
    seen = set()
    for item in respostas_raw:
        if not isinstance(item, dict):
            continue
        chave = str(item.get("palavra_chave") or item.get("keyword") or "").strip()
        texto = str(item.get("resposta") or item.get("reply") or "").strip()
        if not chave or not texto:
            continue
        key_norm = chave.lower()
        if key_norm in seen:
            continue
        seen.add(key_norm)
        itens.append(
            {
                "palavra_chave": chave[:100],
                "resposta": texto[:2000],
            }
        )

    if not itens:
        raise ValueError("A IA não gerou respostas utilizáveis")

    return {
        "resumo": str(data.get("resumo") or "").strip()[:300],
        "boas_vindas": str(data.get("boas_vindas") or "").strip()[:2000],
        "respostas": itens[:10],
    }


def _call_openai(prompt: str) -> str:
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Descrição do negócio:\n{prompt}"},
        ],
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=45)
    except requests.Timeout as exc:
        raise RuntimeError(
            "A OpenAI demorou demais para responder. Tente de novo em instantes."
        ) from exc
    except requests.RequestException as exc:
        logger.error("OpenAI connection error: %s", exc)
        raise RuntimeError(
            "Não foi possível conectar à OpenAI pelo servidor. Verifique a internet do VPS."
        ) from exc

    if resp.status_code >= 400:
        logger.error("OpenAI error %s: %s", resp.status_code, resp.text[:800])
        detail = ""
        try:
            detail = str(resp.json().get("error", {}).get("message") or "")
        except Exception:
            detail = ""
        low = detail.lower()
        if resp.status_code == 401:
            raise RuntimeError("Chave OPENAI_API_KEY inválida. Gere outra em platform.openai.com.")
        if resp.status_code == 429 or "quota" in low or "billing" in low or "insufficient" in low:
            raise RuntimeError(
                "Sem crédito/limite na OpenAI. Adicione billing em platform.openai.com/account/billing."
            )
        raise RuntimeError(
            detail[:220] if detail else "Falha ao consultar a IA. Verifique OPENAI_API_KEY e billing."
        )

    body = resp.json()
    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Resposta inesperada da IA") from exc


def generate_autorespostas(descricao: str) -> dict[str, Any]:
    """Gera sugestões de respostas a partir da descrição do negócio."""
    texto = (descricao or "").strip()
    if len(texto) < 10:
        raise ValueError("Descreva seu negócio com pelo menos algumas frases.")

    if not ai_configured():
        raise RuntimeError("IA não configurada. Defina OPENAI_API_KEY no .env")

    raw = _call_openai(texto)
    data = _extract_json(raw)
    return _normalize_suggestions(data)
