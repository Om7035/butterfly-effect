"""Stage 1: LLM parsing — plain text → UniversalEvent + deep seeds."""
from __future__ import annotations

import asyncio
from loguru import logger


async def run(question: str) -> tuple:
    """
    Returns (event, deep_data_task).
    deep_data_task is a coroutine that can be awaited later (runs concurrently with fetch).
    """
    from butterfly.llm.event_parser import EventParser
    parser = EventParser()
    event = await parser.parse(question)
    deep_task = asyncio.create_task(parser.parse_deep(question, event.causal_seeds))
    return event, deep_task
