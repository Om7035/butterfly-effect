"""
ESAA Log Analyzer — reads activity_*.jsonl files in aggregate to find
systematic biases in the agent swarm.

Run manually or as a scheduled job:
    python -m butterfly.simulation.esaa_analyzer

Outputs:
  - Most frequently rejected variables (systematic bias)
  - Agent rejection rates by agent_id
  - Delta distribution per variable (are agents over/under-shooting?)
  - Consensus score per variable (do bullish/bearish agents agree?)
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger


@dataclass
class VariableStats:
    variable: str
    total_intentions: int = 0
    accepted: int = 0
    rejected: int = 0
    deltas: list[float] = field(default_factory=list)

    @property
    def rejection_rate(self) -> float:
        if self.total_intentions == 0:
            return 0.0
        return self.rejected / self.total_intentions

    @property
    def mean_delta(self) -> float:
        return sum(self.deltas) / len(self.deltas) if self.deltas else 0.0

    @property
    def delta_std(self) -> float:
        if len(self.deltas) < 2:
            return 0.0
        mean = self.mean_delta
        variance = sum((d - mean) ** 2 for d in self.deltas) / len(self.deltas)
        return variance ** 0.5

    @property
    def consensus_score(self) -> float:
        """1.0 = all agents agree direction, 0.0 = chaotic."""
        if not self.deltas:
            return 0.0
        positive = sum(1 for d in self.deltas if d > 0)
        negative = sum(1 for d in self.deltas if d < 0)
        majority = max(positive, negative)
        return majority / len(self.deltas)


def analyze_logs(data_dir: str = "data") -> dict:
    """
    Read all activity_*.jsonl files and compute aggregate statistics.
    Returns a report dict suitable for logging or storage.
    """
    data_path = Path(data_dir)
    log_files = list(data_path.glob("activity_*.jsonl"))

    if not log_files:
        logger.info(f"[ESAA_ANALYZER] No log files found in {data_dir}")
        return {"log_files": 0, "total_entries": 0}

    variable_stats: dict[str, VariableStats] = defaultdict(lambda: VariableStats(""))
    agent_stats: dict[str, dict] = defaultdict(lambda: {"accepted": 0, "rejected": 0})
    total_entries = 0
    total_accepted = 0
    total_rejected = 0

    for log_file in log_files:
        try:
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Skip sentinel entries
                    if entry.get("entry_type") == "projection_hash":
                        continue

                    var = entry.get("variable", "")
                    agent = entry.get("agent_id", "unknown")
                    delta = entry.get("delta", 0.0)
                    accepted = entry.get("accepted", False)

                    if not var:
                        continue

                    total_entries += 1
                    vs = variable_stats[var]
                    vs.variable = var
                    vs.total_intentions += 1
                    vs.deltas.append(delta)

                    if accepted:
                        vs.accepted += 1
                        total_accepted += 1
                        agent_stats[agent]["accepted"] += 1
                    else:
                        vs.rejected += 1
                        total_rejected += 1
                        agent_stats[agent]["rejected"] += 1

        except Exception as e:
            logger.warning(f"[ESAA_ANALYZER] Failed to read {log_file}: {e}")

    # Build report
    high_rejection = [
        {"variable": vs.variable, "rejection_rate": round(vs.rejection_rate, 3),
         "total": vs.total_intentions}
        for vs in variable_stats.values()
        if vs.rejection_rate > 0.3 and vs.total_intentions >= 5
    ]
    high_rejection.sort(key=lambda x: x["rejection_rate"], reverse=True)

    low_consensus = [
        {"variable": vs.variable, "consensus": round(vs.consensus_score, 3),
         "mean_delta": round(vs.mean_delta, 4), "std": round(vs.delta_std, 4)}
        for vs in variable_stats.values()
        if vs.consensus_score < 0.6 and vs.total_intentions >= 5
    ]
    low_consensus.sort(key=lambda x: x["consensus"])

    biased_agents = [
        {"agent_id": agent_id,
         "rejection_rate": round(stats["rejected"] / max(stats["accepted"] + stats["rejected"], 1), 3),
         "total": stats["accepted"] + stats["rejected"]}
        for agent_id, stats in agent_stats.items()
        if (stats["accepted"] + stats["rejected"]) >= 10
    ]
    biased_agents.sort(key=lambda x: x["rejection_rate"], reverse=True)

    report = {
        "log_files_analyzed": len(log_files),
        "total_entries": total_entries,
        "total_accepted": total_accepted,
        "total_rejected": total_rejected,
        "overall_rejection_rate": round(total_rejected / max(total_entries, 1), 3),
        "high_rejection_variables": high_rejection[:10],
        "low_consensus_variables": low_consensus[:10],
        "biased_agents": biased_agents[:10],
        "unique_variables": len(variable_stats),
        "unique_agents": len(agent_stats),
    }

    logger.info(
        f"[ESAA_ANALYZER] {len(log_files)} files, {total_entries} entries, "
        f"rejection_rate={report['overall_rejection_rate']:.1%}, "
        f"high_rejection_vars={len(high_rejection)}"
    )
    return report


if __name__ == "__main__":
    import sys
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    report = analyze_logs(data_dir)
    print(json.dumps(report, indent=2))
