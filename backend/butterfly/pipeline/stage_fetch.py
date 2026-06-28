"""Stage 2: Evidence fetch — all sources concurrently, 7s hard timeout."""
from __future__ import annotations

import asyncio
from loguru import logger


async def run(event) -> tuple[list, list, dict]:
    """Returns (evidence, gdelt_items, fred_data). Never raises."""
    from butterfly.ingestion.universal_fetcher import UniversalFetcher
    from butterfly.api.analyze import _fetch_gdelt_evidence, _fetch_fred_data

    evidence, gdelt_items, fred_data = [], [], {}
    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                _safe(UniversalFetcher().fetch(event)),
                _safe(_fetch_gdelt_evidence(event)),
                _safe(_fetch_fred_data(event.domain)),
                return_exceptions=True,
            ),
            timeout=7.0,
        )
        if not isinstance(results[0], Exception): evidence = results[0] or []
        if not isinstance(results[1], Exception): gdelt_items = results[1] or []
        if not isinstance(results[2], Exception): fred_data = results[2] or {}
    except asyncio.TimeoutError:
        logger.warning("[STAGE_FETCH] Timeout (7s) — partial evidence")
    except Exception as e:
        logger.warning(f"[STAGE_FETCH] Error: {e}")

    logger.info(f"[STAGE_FETCH] evidence={len(evidence)} gdelt={len(gdelt_items)} fred={len(fred_data)}")
    return evidence, gdelt_items, fred_data


async def _safe(coro):
    try:
        return await coro
    except Exception:
        return []
