# assistant/llm_chat.py
from __future__ import annotations

import logging
import time
import os
from typing import List, Dict, Any

import requests

from django.conf import settings

# If you prefer to reuse config from recommender.llm:
# from recommender.llm import HOST, MODEL, TIMEOUT, TEMPERATURE, RETRIES, BACKOFF_SEC

# ---------------------------------------------------------------------
# Config (env-backed with Django settings overrides)
# ---------------------------------------------------------------------
HOST: str = getattr(settings, "OLLAMA_HOST", os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"))
MODEL: str = getattr(settings, "OLLAMA_MODEL", os.environ.get("OLLAMA_MODEL", "llama3:8b-instruct-q4_0"))
TIMEOUT: int = int(getattr(settings, "OLLAMA_TIMEOUT", os.environ.get("OLLAMA_TIMEOUT", 20)))
TEMPERATURE: float = float(getattr(settings, "OLLAMA_TEMPERATURE", os.environ.get("OLLAMA_TEMPERATURE", 0.3)))
RETRIES: int = int(getattr(settings, "OLLAMA_RETRIES", os.environ.get("OLLAMA_RETRIES", 2)))
BACKOFF_SEC: float = float(getattr(settings, "OLLAMA_BACKOFF_SEC", os.environ.get("OLLAMA_BACKOFF_SEC", 0.5)))

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# System prompt: SHOP ASSISTANT
# ---------------------------------------------------------------------
BASE_SYSTEM_PROMPT = """
You are the AI shopping assistant for Sockcs, an online store.

Tone:
- Warm, kind, concise, and honest.
- You are helpful and down-to-earth, not salesy or overexcited.

Capabilities:
- Answer questions about:
  - Products (styles, use cases, how to choose).
  - Orders in a general way (what order status means, where to check).
  - Shipping, returns, and store policies (general, not legal advice).
  - About us / services / how the shop works.

Hard rules:
- Do NOT invent specific order data (order numbers, tracking info, delivery dates).
- Do NOT invent stock levels, prices, or discount codes.
- When you are not sure, say you are not sure and suggest what the user can do on the website.
- If user asks for medical, legal, or financial advice, politely decline and redirect.

Formatting:
- Keep answers short and to the point unless the user asks for detail.
- Use bullet points when listing options.
"""

# ---------------------------------------------------------------------
# Low-level Ollama chat
# ---------------------------------------------------------------------
def _ollama_chat(messages: List[Dict[str, str]]) -> str:
    """
    messages: list of {role: 'system'|'user'|'assistant', content: str}
    Returns the assistant's content string.
    """
    payload: Dict[str, Any] = {
        "model": MODEL,
        "stream": False,
        "options": {"temperature": TEMPERATURE},
        "messages": messages,
    }

    attempt = 0
    while True:
        attempt += 1
        try:
            r = requests.post(f"{HOST}/api/chat", json=payload, timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json()
            content = (data.get("message") or {}).get("content", "")
            return (content or "").strip()
        except Exception as e:
            if attempt > RETRIES:
                _logger.exception("Ollama chat failed after %s attempts: %s", attempt, e)
                raise
            time.sleep(BACKOFF_SEC * attempt)


def _build_messages(history: List[Dict[str, str]], store_context: Dict[str, Any] | None = None) -> List[Dict[str, str]]:
    """
    history: [{role: 'user'|'assistant', content: '...'}, ...]
    store_context: optional dict to inject extra info (e.g. opening hours, basic policies).
    """
    msgs: List[Dict[str, str]] = [{"role": "system", "content": BASE_SYSTEM_PROMPT}]

    if store_context:
        msgs.append(
            {
                "role": "system",
                "content": f"Store context (non-sensitive, high-level info): {store_context}",
            }
        )

    # Only pass allowed roles from history
    for m in history:
        role = m.get("role")
        if role in ("user", "assistant"):
            msgs.append({"role": role, "content": m.get("content", "")})

    return msgs


def generate_shop_reply(
    history: List[Dict[str, str]],
    store_context: Dict[str, Any] | None = None,
) -> str:
    """
    High-level API for the rest of the app.

    history example:
    [
      {"role": "user", "content": "Hi"},
      {"role": "assistant", "content": "Hello, how can I help?"},
      {"role": "user", "content": "What socks are best for running?"}
    ]
    """
    if not history:
        raise ValueError("history must be non-empty")

    try:
        msgs = _build_messages(history, store_context=store_context)
        reply = _ollama_chat(msgs)
        return reply or "Sorry, I couldn't generate a response right now."
    except Exception as e:
        _logger.exception("generate_shop_reply failed: %s", e)
        return "I’m having trouble answering right now. Please try again later."
