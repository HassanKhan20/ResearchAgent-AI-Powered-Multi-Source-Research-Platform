"""Thin structured-output wrapper around Claude.

Every agent asks for a Pydantic model back. If no API key is configured, or the call
fails or is declined, `structured()` returns None and the caller falls back to its
heuristic implementation, so the pipeline always produces a report.
"""

import logging
from typing import TypeVar

from pydantic import BaseModel

from ..config import get_settings

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

_client = None


def _get_client():
    global _client
    if _client is None:
        from anthropic import AsyncAnthropic

        _client = AsyncAnthropic(api_key=get_settings().anthropic_api_key)
    return _client


async def structured(system: str, prompt: str, schema: type[T], max_tokens: int = 16000) -> T | None:
    settings = get_settings()
    if not settings.llm_enabled:
        return None
    try:
        response = await _get_client().beta.messages.parse(
            model=settings.llm_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
            output_config={"effort": settings.llm_effort},
            # Retry on a substitute model server-side if a safety classifier declines.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except Exception as exc:
        log.warning("LLM call for %s failed, using heuristics: %s", schema.__name__, exc)
        return None
    if response.stop_reason in ("refusal", "max_tokens"):
        log.warning("LLM call for %s stopped with %s, using heuristics", schema.__name__, response.stop_reason)
        return None
    return response.parsed_output
