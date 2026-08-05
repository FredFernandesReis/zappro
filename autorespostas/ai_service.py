"""
Assistente de IA para sugerir respostas automáticas (Groq — cota gratuita).
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
- Use português brasileiro, tom simpático, natural e humano (não formal demais).
- Cada palavra-chave deve ser curta (1-3 palavras).
- Crie entre 3 e 8 respostas úteis (preço, horário, endereço, agendamento, etc. quando fizer sentido).
- Textos curtos (2-4 frases), como alguém digitando no WhatsApp.
- Não invente preços/horários/endereços se o usuário não informou; peça contato de forma genérica.
- Inclua EXATAMENTE 3 variações diferentes de boas-vindas no array boas_vindas (mesmo sentido, textos distintos).

Formato exato:
{
  "resumo": "frase curta do que entendeu",
  "boas_vindas": ["variação 1", "variação 2", "variação 3"],
  "respostas": [
    {"palavra_chave": "preço", "resposta": "texto..."},
    {"palavra_chave": "horário", "resposta": "texto..."}
  ]
}
"""


def ai_configured() -> bool:
    return bool(getattr(settings, "GROQ_API_KEY", ""))


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

    bv_raw = data.get("boas_vindas")
    bv_list: list[str] = []
    if isinstance(bv_raw, list):
        for item in bv_raw:
            texto = str(item or "").strip()[:2000]
            if texto:
                bv_list.append(texto)
    elif isinstance(bv_raw, str) and bv_raw.strip():
        bv_list.append(bv_raw.strip()[:2000])

    # Garante até 3 slots para o frontend
    while len(bv_list) < 3:
        bv_list.append("")
    bv_list = bv_list[:3]

    return {
        "resumo": str(data.get("resumo") or "").strip()[:300],
        "boas_vindas": bv_list[0],
        "boas_vindas_lista": bv_list,
        "respostas": itens[:10],
    }


def _call_groq(prompt: str) -> str:
    api_key = getattr(settings, "GROQ_API_KEY", "")
    model = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
    url = "https://api.groq.com/openai/v1/chat/completions"
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
            "A IA demorou demais para responder. Tente de novo em instantes."
        ) from exc
    except requests.RequestException as exc:
        logger.error("Groq connection error: %s", exc)
        raise RuntimeError(
            "Não foi possível conectar à Groq pelo servidor. Verifique a internet do VPS."
        ) from exc

    if resp.status_code >= 400:
        logger.error("Groq error %s: %s", resp.status_code, resp.text[:800])
        detail = ""
        try:
            detail = str(resp.json().get("error", {}).get("message") or "")
        except Exception:
            detail = ""
        if resp.status_code == 401:
            raise RuntimeError("Chave GROQ_API_KEY inválida. Gere em console.groq.com")
        if resp.status_code == 429:
            raise RuntimeError(
                "Limite gratuito da Groq atingido. Aguarde alguns minutos e tente de novo."
            )
        raise RuntimeError(
            detail[:220] if detail else "Falha ao consultar a IA. Verifique GROQ_API_KEY."
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
        raise RuntimeError("IA não configurada. Defina GROQ_API_KEY no .env")

    raw = _call_groq(texto)
    data = _extract_json(raw)
    return _normalize_suggestions(data)
