"""
Multi-provider LLM client — tries providers in priority order.

Priority: Gemini (free tier) → Mistral (free tier) → Anthropic → rule-based fallback

Usage:
    from butterfly.llm.providers import llm_complete

    text = await llm_complete(
        system="You are an analyst...",
        user="Analyze this event...",
        max_tokens=1024,
    )
"""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger


async def llm_complete(
    system: str,
    user: str,
    max_tokens: int = 1024,
    json_mode: bool = True,
) -> str:
    """Call the best available LLM provider. Returns raw text response.

    Tries in order: Gemini → Mistral → Anthropic → raises RuntimeError.
    """
    from butterfly.config import settings

    # ── 1. Gemini (free tier: 15 req/min, 1M tokens/day) ─────────────────────
    if settings.gemini_api_key:
        try:
            return await _gemini(settings.gemini_api_key, system, user, max_tokens)
        except Exception as e:
            logger.warning(f"Gemini failed: {e} — trying Mistral")

    # ── 2. Mistral (free tier: Le Chat / La Plateforme free models) ───────────
    if settings.mistral_api_key:
        try:
            return await _mistral(settings.mistral_api_key, system, user, max_tokens)
        except Exception as e:
            logger.warning(f"Mistral failed: {e} — trying Anthropic")

    # ── 3. Anthropic (paid, but check anyway) ─────────────────────────────────
    if settings.anthropic_api_key:
        try:
            return await _anthropic(settings.anthropic_api_key, system, user, max_tokens)
        except Exception as e:
            logger.warning(f"Anthropic failed: {e}")

    raise RuntimeError("No LLM provider available — set GEMINI_API_KEY or MISTRAL_API_KEY in backend/.env")


# ── Provider implementations ──────────────────────────────────────────────────

async def _gemini(api_key: str, system: str, user: str, max_tokens: int) -> str:
    """Call Google Gemini 1.5 Flash (free tier)."""
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system,
        generation_config=genai.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=0.3,
        ),
    )
    # Run in thread pool since google-generativeai is sync
    import asyncio
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: model.generate_content(user))
    text = response.text.strip()
    logger.debug(f"Gemini response: {len(text)} chars")
    return text


async def _mistral(api_key: str, system: str, user: str, max_tokens: int) -> str:
    """Call Mistral (mistral-small-latest is free on La Plateforme)."""
    from mistralai import Mistral

    client = Mistral(api_key=api_key)
    import asyncio
    loop = asyncio.get_event_loop()

    def _call():
        return client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )

    response = await loop.run_in_executor(None, _call)
    text = response.choices[0].message.content.strip()
    logger.debug(f"Mistral response: {len(text)} chars")
    return text


async def _anthropic(api_key: str, system: str, user: str, max_tokens: int) -> str:
    """Call Anthropic Claude."""
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=api_key)
    resp = await client.messages.create(
        model="claude-haiku-4-20250514",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text.strip()


def extract_json(text: str) -> Any:
    """Extract JSON from LLM response, stripping markdown fences."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    # Find first { or [ and last } or ]
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue
    return json.loads(text)  # last attempt, will raise if invalid
