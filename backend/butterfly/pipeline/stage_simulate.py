"""Stage 4: C-Path + hybrid simulation."""
from __future__ import annotations

import os
from loguru import logger


async def run(event, graph: dict, run_id: str, data_dir: str):
    """Returns (dag, cci_scores, sim_result). Never raises — returns empty result on failure."""
    from butterfly.causal.dag import DAGBuilder
    from butterfly.causal.cpath import CPathCalculator
    from butterfly.simulation.universal_runner import UniversalRunner, UniversalSimulationResult

    dag = DAGBuilder().build_from_graph_data(graph)
    cci_scores = CPathCalculator().calculate(dag, "root")

    os.makedirs(data_dir, exist_ok=True)
    log_path = os.path.join(data_dir, f"activity_{run_id}.jsonl")

    try:
        sim_result = await UniversalRunner().run(
            event, graph, steps=168, log_path=log_path,
            precomputed_dag=dag, precomputed_cci=cci_scores,
        )
        logger.info(f"[STAGE_SIM] mode={sim_result.mode} agents={sim_result.agent_count} steps={sim_result.steps_completed}")
        return dag, cci_scores, sim_result
    except Exception as e:
        logger.error(f"[STAGE_SIM] Failed: {e}")
        return dag, cci_scores, UniversalSimulationResult()
