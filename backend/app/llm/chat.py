"""OpenAI-compatible chat completions — IT configures base URL, key, and model."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.config import Settings, effective_llm_api_key, effective_llm_model, get_settings

logger = logging.getLogger(__name__)


def chat_completion_json(
    system_prompt: str,
    user_message: str,
    *,
    settings: Optional[Settings] = None,
) -> Dict[str, Any]:
    """Returns parsed JSON from an OpenAI-compatible chat completion."""
    s = settings or get_settings()
    key = effective_llm_api_key(s)
    model = effective_llm_model(s)
    if not key:
        raise RuntimeError("LLM API key not configured (set LLM_API_KEY or OPENAI_API_KEY)")

    from openai import OpenAI

    kwargs: Dict[str, Any] = {"api_key": key}
    if s.llm_base_url:
        kwargs["base_url"] = s.llm_base_url
    client = OpenAI(**kwargs)
    logger.info("LLM request model=%s base_url=%s", model, s.llm_base_url or "default")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("LLM returned non-JSON: %s", raw[:500])
        raise RuntimeError("LLM response was not valid JSON") from e
