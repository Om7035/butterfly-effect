"""
LLM Adapter Interface — standardizes all LLM calls through a single Protocol.

All LLM providers (Gemini, Mistral, Anthropic) implement LLMAdapter.
This means if any provider changes their API, only one adapter breaks,
not the entire parsing pipeline.

Usage:
    adapter = get_adapter()
    result = await adapter.complete("You are an analyst.", "Analyze this event.")
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from loguru import logger


@runtime_checkable
class LLMAdapter(Protocol):
    """Standard interface for all LLM providers."""

    async def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 2048,
    ) -> str:
        """Call the LLM and return raw text response."""
        ...

    @property
    def name(self) -> str:
        """Provider name for logging."""
        ...


class GeminiAdapter:
    name = "gemini"

    async def complete(self, system: str, user: str, max_tokens: int = 2048) -> str:
        from butterfly.config import settings
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not set")

        from google import genai
        from google.genai import types as genai_types
        import asyncio

        client = genai.Client(api_key=settings.gemini_api_key)
        loop = asyncio.get_event_loop()

        for model in ("gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash"):
            try:
                def _call(m=model):
                    return client.models.generate_content(
                        model=m,
                        contents=user,
                        config=genai_types.GenerateContentConfig(
                            system_instruction=system,
                            max_output_tokens=max(max_tokens, 2048),
                            temperature=0.1,
                            response_mime_type="application/json",
                        ),
                    )
                resp = await loop.run_in_executor(None, _call)
                return resp.text.strip()
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    continue
                raise
        raise RuntimeError("All Gemini models rate limited")


class MistralAdapter:
    name = "mistral"

    async def complete(self, system: str, user: str, max_tokens: int = 2048) -> str:
        from butterfly.config import settings
        if not settings.mistral_api_key:
            raise RuntimeError("MISTRAL_API_KEY not set")

        from mistralai.client.sdk import Mistral
        import asyncio

        client = Mistral(api_key=settings.mistral_api_key)
        loop = asyncio.get_event_loop()

        def _call():
            return client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=0.1,
            )

        resp = await loop.run_in_executor(None, _call)
        return resp.choices[0].message.content.strip()


class AnthropicAdapter:
    name = "anthropic"

    async def complete(self, system: str, user: str, max_tokens: int = 2048) -> str:
        from butterfly.config import settings
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")

        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        resp = await client.messages.create(
            model="claude-haiku-4-20250514",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text.strip()


def get_adapter() -> LLMAdapter:
    """Return the best available adapter in priority order."""
    from butterfly.config import settings

    if settings.gemini_api_key:
        return GeminiAdapter()
    if settings.mistral_api_key:
        return MistralAdapter()
    if settings.anthropic_api_key:
        return AnthropicAdapter()
    raise RuntimeError("No LLM API key configured. Set GEMINI_API_KEY or MISTRAL_API_KEY.")


async def complete_with_fallback(system: str, user: str, max_tokens: int = 2048) -> str:
    """
    Try adapters in priority order with automatic fallback.
    Equivalent to the existing llm_complete() but using the adapter interface.
    """
    from butterfly.config import settings

    adapters: list[LLMAdapter] = []
    if settings.gemini_api_key:
        adapters.append(GeminiAdapter())
    if settings.mistral_api_key:
        adapters.append(MistralAdapter())
    if settings.anthropic_api_key:
        adapters.append(AnthropicAdapter())

    if not adapters:
        raise RuntimeError("No LLM API key configured.")

    last_err = None
    for adapter in adapters:
        try:
            result = await adapter.complete(system, user, max_tokens)
            logger.debug(f"[LLM] {adapter.name} responded: {len(result)} chars")
            return result
        except Exception as e:
            logger.warning(f"[LLM] {adapter.name} failed: {e} — trying next")
            last_err = e

    raise RuntimeError(f"All LLM adapters failed. Last error: {last_err}")
