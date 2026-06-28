"""Stage 3: Graph build — evidence NER + LLM seeds + deep seeds + FRED enrichment."""
from __future__ import annotations

import asyncio
from loguru import logger


async def run(event, evidence: list, fred_data: dict, deep_task=None) -> dict:
    """Returns graph dict. Never raises."""
    from butterfly.api.analyze import _build_graph, _apply_fred_to_graph, _merge_deep_seeds

    graph = _build_graph(event, evidence=evidence if evidence else None)

    if fred_data:
        graph = _apply_fred_to_graph(graph, fred_data)

    # Merge deep parse if ready
    if deep_task is not None:
        try:
            deep_data = await asyncio.wait_for(asyncio.shield(deep_task), timeout=1.0)
            if deep_data.get("deep_causal_seeds"):
                graph = _merge_deep_seeds(graph, deep_data, event)
                logger.info(f"[STAGE_GRAPH] Deep seeds merged: {len(deep_data['deep_causal_seeds'])}")
        except (asyncio.TimeoutError, Exception) as e:
            logger.debug(f"[STAGE_GRAPH] Deep parse not ready: {e}")

    logger.info(f"[STAGE_GRAPH] nodes={len(graph['nodes'])} edges={len(graph['edges'])}")
    return graph
