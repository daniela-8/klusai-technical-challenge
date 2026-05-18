"""OpenAI-compatible LLM client.
Works with any provider that exposes an OpenAI-compatible API:
  - OpenAI:       (default, no base_url needed)
  - Google Gemini: base_url=https://generativelanguage.googleapis.com/v1beta/openai/
  - Groq:          base_url=https://api.groq.com/openai/v1
"""

from __future__ import annotations
import asyncio
import json
from typing import Any
import openai
from openai import AsyncOpenAI
from app.core import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
_LAST_LLM_CALL_TIME: float = 0.0
_LLM_LOCK = asyncio.Lock()
_MIN_INTERVAL = 5.0


async def _rate_limit_wait() -> None:
    """Wait until at least _MIN_INTERVAL seconds have passed since the last LLM call."""
    global _LAST_LLM_CALL_TIME
    import time

    async with _LLM_LOCK:
        now = time.monotonic()
        elapsed = now - _LAST_LLM_CALL_TIME
        if elapsed < _MIN_INTERVAL:
            wait = _MIN_INTERVAL - elapsed
            logger.info("rate_limit_waiting", wait_seconds=round(wait, 1))
            await asyncio.sleep(wait)
        _LAST_LLM_CALL_TIME = time.monotonic()


class LLMClient:
    """Async wrapper around any OpenAI-compatible API with structured output parsing."""

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        self._gemini_client = None
        if settings.has_openai_key:
            kwargs: dict[str, Any] = {
                "api_key": settings.openai_api_key,
                "max_retries": 0,
            }
            if settings.openai_base_url:
                kwargs["base_url"] = settings.openai_base_url
            self._client = AsyncOpenAI(**kwargs)
            logger.info(
                "llm_client_initialized",
                provider="gemini" if settings.openai_base_url else "openai",
                model=settings.openai_model,
            )
        if settings.has_gemini_key:
            try:
                from google import genai

                self._gemini_client = genai.Client(api_key=settings.gemini_api_key)
                logger.info("gemini_search_grounding_initialized")
            except ImportError:
                logger.warning("google_genai_not_installed")
            except Exception as e:
                logger.warning("gemini_client_init_failed", error=str(e))

    @property
    def is_available(self) -> bool:
        return self._client is not None

    @property
    def has_search_grounding(self) -> bool:
        return self._gemini_client is not None

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        response_format: dict[str, str] | None = None,
    ) -> str:
        """Send a chat completion request and return the response text.
        Rate limiting and retries are handled manually to protect the daily
        quota.  We retry up to 3 times on transient per-minute 429s, waiting
        the full retry delay the server suggests (or 60 seconds).  We
        immediately abort on daily-quota exhaustion.
        """
        if not self._client:
            raise RuntimeError("LLM client not initialized — missing API key")
        model = model or settings.openai_model
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            await _rate_limit_wait()
            logger.info(
                "llm_request",
                model=model,
                prompt_preview=user_prompt[:100],
                attempt=attempt,
            )
            try:
                kwargs: dict[str, Any] = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                }
                if response_format:
                    kwargs["response_format"] = response_format
                response = await self._client.chat.completions.create(**kwargs)
                text = response.choices[0].message.content or ""
                logger.info(
                    "llm_response",
                    model=model,
                    tokens=response.usage.total_tokens if response.usage else 0,
                )
                return text
            except openai.APIError as e:
                err_str = str(e)
                is_daily_exhausted = "RESOURCE_EXHAUSTED" in err_str and (
                    "PerDay" in err_str or "per_day" in err_str.lower()
                )
                if is_daily_exhausted:
                    logger.error(
                        "daily_quota_exhausted", model=model, error=err_str[:200]
                    )
                    raise ValueError(f"Daily quota exhausted for {model}: {e}") from e
                is_rate_limit = (
                    "429" in err_str
                    or "RESOURCE_EXHAUSTED" in err_str
                    or "Too Many Requests" in err_str
                )
                if is_rate_limit and attempt < max_attempts:
                    wait_time = 60.0
                    import re

                    delay_match = re.search(r'retryDelay["\s:]+(\d+)', err_str)
                    if delay_match:
                        wait_time = int(delay_match.group(1)) + 2
                    retry_match = re.search(
                        r"retry in (\d+\.?\d*)", err_str, re.IGNORECASE
                    )
                    if retry_match:
                        wait_time = float(retry_match.group(1)) + 2
                    logger.warning(
                        "rate_limit_hit",
                        model=model,
                        attempt=attempt,
                        wait_seconds=round(wait_time, 1),
                    )
                    await asyncio.sleep(wait_time)
                    continue
                is_service_error = "503" in err_str or "Service Unavailable" in err_str
                if is_service_error and attempt < max_attempts:
                    wait_time = 10.0 * attempt
                    logger.warning(
                        "service_unavailable",
                        model=model,
                        attempt=attempt,
                        wait_seconds=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise
        raise RuntimeError(f"LLM call failed after {max_attempts} attempts")

    async def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
    ) -> dict[str, Any]:
        """Send a chat request and parse the response as JSON."""
        system_prompt_with_json = (
            system_prompt + "\n\nIMPORTANT: You MUST respond with valid JSON only. "
            "No markdown, no code fences, no explanation — just the JSON object."
        )
        text = await self.chat(
            system_prompt_with_json,
            user_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        return self._parse_json_response(text)

    async def chat_json_with_search(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Send a chat request with Google Search grounding and parse as JSON.
        Uses the google-genai SDK directly (not OpenAI-compatible endpoint)
        to enable the `google_search` tool. The model can perform live Google
        searches during inference to cross-reference job descriptions and
        identify hiring companies with higher confidence.
        Falls back to regular chat_json() if the Gemini key is not configured.
        """
        if not self._gemini_client:
            logger.info("search_grounding_unavailable_fallback_to_chat_json")
            return await self.chat_json(
                system_prompt, user_prompt, model=model, temperature=temperature
            )
        await _rate_limit_wait()
        model = model or settings.openai_model
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                await _rate_limit_wait()
            try:
                from google.genai import types

                grounding_tool = types.Tool(google_search=types.GoogleSearch())
                full_prompt = (
                    f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\n"
                    f"IMPORTANT: You MUST respond with valid JSON only. "
                    f"No markdown, no code fences, no explanation — just the JSON object.\n\n"
                    f"USER REQUEST:\n{user_prompt}"
                )
                logger.info(
                    "gemini_search_grounded_request",
                    model=model,
                    prompt_preview=user_prompt[:100],
                    attempt=attempt,
                )
                response = self._gemini_client.models.generate_content(
                    model=model,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        tools=[grounding_tool],
                        temperature=temperature,
                        response_mime_type="application/json",
                    ),
                )
                text = response.text or ""
                grounding_meta = getattr(
                    response.candidates[0] if response.candidates else None,
                    "grounding_metadata",
                    None,
                )
                if grounding_meta:
                    search_queries = getattr(grounding_meta, "search_entry_point", None)
                    web_results = getattr(grounding_meta, "grounding_chunks", None)
                    logger.info(
                        "gemini_search_grounding_used",
                        has_search_queries=search_queries is not None,
                        num_web_results=len(web_results) if web_results else 0,
                    )
                else:
                    logger.info("gemini_search_grounding_not_triggered")
                return self._parse_json_response(text)
            except Exception as e:
                err_str = str(e)
                is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str
                if is_rate_limit and attempt < max_attempts:
                    wait_time = 60.0
                    logger.warning(
                        "gemini_search_rate_limit",
                        attempt=attempt,
                        wait_seconds=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                logger.warning(
                    "gemini_search_failed_fallback",
                    error=str(e),
                    attempt=attempt,
                )
                return await self.chat_json(
                    system_prompt, user_prompt, model=model, temperature=temperature
                )
        return await self.chat_json(
            system_prompt, user_prompt, model=model, temperature=temperature
        )

    @staticmethod
    def _parse_json_response(text: str) -> dict[str, Any]:
        """Parse a text response as JSON, handling markdown fences and noise."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if len(lines) > 1:
                text = "\n".join(lines[1:-1]).strip()
            else:
                text = text.replace("```json", "").replace("```", "").strip()
        if text.startswith("json"):
            text = text[4:].strip()
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
            text = text[start_idx : end_idx + 1]
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("json_parse_error", error=str(e), raw_text=text[:200])
            raise ValueError(f"Failed to parse LLM response as JSON: {e}") from e

    async def close(self) -> None:
        if self._client:
            await self._client.close()
