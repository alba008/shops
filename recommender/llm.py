# recommender/llm.py
from __future__ import annotations

import json
import logging
import os
import time
from typing import Callable, Iterable, List, Sequence

import requests
from django.conf import settings

# ---------------------------------------------------------------------
# Config (env-backed with Django settings overrides)
# ---------------------------------------------------------------------
HOST: str = getattr(settings, "OLLAMA_HOST", os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"))
MODEL: str = getattr(settings, "OLLAMA_MODEL", os.environ.get("OLLAMA_MODEL", "llama3:8b-instruct-q4_0"))
TIMEOUT: int = int(getattr(settings, "OLLAMA_TIMEOUT", os.environ.get("OLLAMA_TIMEOUT", 12)))
TEMPERATURE: float = float(getattr(settings, "OLLAMA_TEMPERATURE", os.environ.get("OLLAMA_TEMPERATURE", 0.2)))
MAX_CANDIDATES: int = int(getattr(settings, "OLLAMA_MAX_CANDIDATES", os.environ.get("OLLAMA_MAX_CANDIDATES", 30)))
RETRIES: int = int(getattr(settings, "OLLAMA_RETRIES", os.environ.get("OLLAMA_RETRIES", 2)))
BACKOFF_SEC: float = float(getattr(settings, "OLLAMA_BACKOFF_SEC", os.environ.get("OLLAMA_BACKOFF_SEC", 0.5)))

SYSTEM_PROMPT = (
  "You are an e-commerce merchandiser AI. Given a shopper context and a list of candidate products "
  "(JSON with id,name,price,category,tags), return ONLY a JSON array of product ids in ranking order. "
  "Rules: prefer diversity across categories/colors; when intent='similar' keep price near the anchor; "
  "never include the anchor or already-purchased IDs; if 'budget' is set, exclude items over budget; "
  "avoid near-duplicates from the same brand; do not invent ids; output only JSON."
)

_logger = logging.getLogger(__name__)


def _chat(messages: list[dict]) -> str:
    """Call Ollama /api/chat with minimal noise and light retries."""
    payload = {
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
            data = r.json()  # Expected: {"message": {"content": "..."}}
            content = (data.get("message") or {}).get("content", "")
            return content.strip()
        except Exception as e:
            if attempt > RETRIES:
                raise
            # Quiet retry with exponential-ish backoff
            time.sleep(BACKOFF_SEC * attempt)


def _coerce_json_id_list(s: str) -> List[int]:
    """
    Parse a JSON string that must be a list of integers.
    Returns [] on any validation failure (the caller will handle fallback).
    """
    try:
        parsed = json.loads(s)
        if not isinstance(parsed, list):
            return []
        out: List[int] = []
        for x in parsed:
            # allow numeric strings like "12" but coerce to int
            if isinstance(x, (int, float)) or (isinstance(x, str) and x.isdigit()):
                out.append(int(x))
            else:
                return []  # invalid type → reject whole output for safety
        return out
    except Exception:
        return []


def _dedupe_keep_order(ids: Iterable[int]) -> List[int]:
    seen = set()
    out: List[int] = []
    for pid in ids:
        if pid not in seen:
            out.append(pid)
            seen.add(pid)
    return out


def rerank_with_ollama(
    context: dict,
    candidates: Sequence[int],
    product_lookup: Callable[[int], object],
    *,
    max_candidates: int | None = None,
) -> List[int]:
    """
    Rerank candidate product IDs using Ollama (Llama 3).
    - context: arbitrary dict (intent, anchor_product_id, recent_product_ids, budget, etc.)
    - candidates: list of product IDs to rank
    - product_lookup: function(pid) -> product object with attrs: id, name, price, category, tags_list
    - max_candidates: optional cap; defaults to OLLAMA_MAX_CANDIDATES

    Returns a list of product IDs in the desired order.
    On any error or invalid model output, returns the original candidate order.
    """
    if not candidates:
        return []

    cap = max_candidates or MAX_CANDIDATES
    # Clamp + dedupe to keep prompt compact and deterministic
    base_list = _dedupe_keep_order(list(candidates))[:cap]

    # Build compact product JSON for the prompt
    prods = []
    for pid in base_list:
        try:
            p = product_lookup(pid)
        except Exception:
            # If lookup fails for one item, skip it rather than fail whole request
            continue

        prods.append(
            {
                "id": getattr(p, "id", pid),
                "name": getattr(p, "name", "") or "",
                "price": float(getattr(p, "price", 0.0) or 0.0),
                "category": getattr(p, "category", "") or "",
                "tags": list(getattr(p, "tags_list", []) or []),
            }
        )

    if not prods:
        return list(candidates)

    user_ctx = {
        "intent": context.get("intent", "similar"),
        "anchor_product_id": context.get("anchor_product_id"),
        "recent_product_ids": context.get("recent_product_ids", []),
        "budget": context.get("budget"),
    }

    # Compose the user message
    user_msg = (
        "Shopper context: " + json.dumps(user_ctx, ensure_ascii=False) + "\n"
        "Candidates: " + json.dumps(prods, ensure_ascii=False)
    )

    try:
        reply = _chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ]
        )
        ranked = _coerce_json_id_list(reply)

        if not ranked:
            # Model didn't return a valid JSON array → fallback
            return list(candidates)

        # Keep only IDs that were in the input candidate set
        ranked = [pid for pid in ranked if pid in base_list]

        # Append any missing candidates to preserve coverage
        tail = [pid for pid in base_list if pid not in ranked]
        ordered = ranked + tail

        # Finally, append any candidates that were clipped by cap (keep original order)
        overflow = [pid for pid in candidates if pid not in base_list]
        return ordered + overflow

    except Exception as e:
        # Quiet log: one line, no stack unless DEBUG
        _logger.exception("Ollama rerank failed; using baseline order: %s", e)
        return list(candidates)
