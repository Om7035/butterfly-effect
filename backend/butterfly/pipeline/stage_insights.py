"""Stage 5: LLM insights + SNN verification against fetched evidence."""
from __future__ import annotations

from loguru import logger


async def run(event, graph: dict, sim_result, dag, cci_scores: dict, evidence: list) -> tuple[list, dict]:
    """Returns (insights, snn_summary). Never raises."""
    from butterfly.causal.snn_gate import SNNVerificationGate
    from butterfly.api.analyze import _build_insights

    raw_insights: list[dict] = []
    try:
        from butterfly.causal.log_extractor import CausalLogExtractor
        chain = CausalLogExtractor().extract(graph, sim_result, event)
        from butterfly.llm.insight_generator import InsightGenerator
        raw_insights = await InsightGenerator().generate(chain, event)
        logger.info(f"[STAGE_INSIGHTS] LLM generated {len(raw_insights)}")
    except Exception as e:
        logger.warning(f"[STAGE_INSIGHTS] LLM failed ({e}), using structural fallback")
        raw_insights = _build_insights(event, graph)

    snn = SNNVerificationGate()
    verified = snn.verify_batch(raw_insights, dag, cci_scores, evidence=evidence)
    insights = snn.to_frontend_format(verified)
    snn_summary = {
        "total": len(verified),
        "verified": sum(1 for v in verified if v.snn_verified),
        "rejected": sum(1 for v in verified if not v.snn_verified),
    }
    logger.info(f"[STAGE_INSIGHTS] SNN: {snn_summary}")
    return insights, snn_summary
