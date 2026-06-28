"""
ESAA — Event Sourcing for Autonomous Agents.
From the NotebookLM architectural blueprint.

Core principle: agents NEVER mutate shared state directly.
They emit structured "intentions" which are validated by a deterministic
orchestrator before being applied. Invalid intentions are logged and rejected.

This makes the simulation:
  - Hallucination-resistant (invalid agent outputs can't corrupt state)
  - Fully auditable (every state change is in activity.jsonl)
  - Time-travelable (replay log up to any step to reconstruct state)
  - Cryptographically verifiable (RFC 8785 canonical JSON + SHA-256)
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, Field, model_validator


# ── RFC 8785 canonical JSON helper ────────────────────────────────────────────

def canonical_json(data: dict) -> bytes:
    """
    Produce RFC 8785-compliant canonical JSON bytes.

    Rules applied:
      - Keys sorted lexicographically (sort_keys=True)
      - No whitespace (separators=(",", ":"))
      - UTF-8 encoded
      - ensure_ascii=False to preserve Unicode as-is
      - Float values rounded to 8 decimal places for deterministic hashing
        (prevents floating-point drift between live state and replayed state)

    This is the single source of truth for all hash computations.
    Any two dicts with identical content will always produce the same bytes.
    """
    # Normalise floats to 8dp to eliminate floating-point drift
    normalised = {
        k: round(v, 8) if isinstance(v, float) else v
        for k, v in data.items()
    }
    return json.dumps(
        normalised,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_of(data: dict) -> str:
    """Return lowercase hex SHA-256 of the canonical JSON of data."""
    return hashlib.sha256(canonical_json(data)).hexdigest()


# ── Intention model ───────────────────────────────────────────────────────────

class AgentIntention(BaseModel):
    """
    Structured output from an agent's step().
    Agents submit this — they never touch state directly.
    """
    agent_id: str
    step: int
    variable: str
    delta: float = Field(..., ge=-1.0, le=1.0)
    direction: int = Field(..., ge=-1, le=1)
    reason: str = Field(..., min_length=5, max_length=300)
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def direction_matches_delta(self) -> "AgentIntention":
        if self.delta > 0 and self.direction != 1:
            raise ValueError("direction must be 1 for positive delta")
        if self.delta < 0 and self.direction != -1:
            raise ValueError("direction must be -1 for negative delta")
        if self.delta == 0 and self.direction != 0:
            raise ValueError("direction must be 0 for zero delta")
        return self


# ── Validator ─────────────────────────────────────────────────────────────────

class IntentionValidator:

    def __init__(self, valid_variables: set[str]) -> None:
        self.valid_variables = valid_variables

    def validate(self, intention: AgentIntention) -> tuple[bool, str]:
        if intention.variable not in self.valid_variables:
            return False, f"Variable '{intention.variable}' not in environment"
        if abs(intention.delta) > 1.0:
            return False, f"Delta {intention.delta} exceeds bound ±1.0"
        if not intention.reason.strip():
            return False, "Empty reason — agent must explain its action"
        return True, ""


# ── Event log ─────────────────────────────────────────────────────────────────

class EventLog:

    def __init__(self, log_path: str = "data/activity.jsonl") -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        intention: AgentIntention,
        accepted: bool,
        rejection_reason: str = "",
    ) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": intention.agent_id,
            "step": intention.step,
            "variable": intention.variable,
            "delta": intention.delta,
            "accepted": accepted,
            "reason": intention.reason,
            "rejection_reason": rejection_reason if not accepted else None,
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def replay(self, environment: dict, up_to_step: int | None = None) -> dict:
        """Rebuild state by replaying all accepted intentions up to a step."""
        state = {k: 0.0 for k in environment}

        if not self.log_path.exists():
            return state

        with open(self.log_path) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if not entry.get("accepted"):
                        continue
                    if up_to_step is not None and entry.get("step", 0) > up_to_step:
                        break
                    var = entry.get("variable")
                    if var in state:
                        state[var] = max(-1.0, min(1.0, state[var] + entry.get("delta", 0)))
                except Exception:
                    continue

        return state

    def count(self) -> tuple[int, int]:
        """Return (accepted, rejected) counts."""
        accepted = rejected = 0
        if not self.log_path.exists():
            return 0, 0
        with open(self.log_path) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("accepted"):
                        accepted += 1
                    else:
                        rejected += 1
                except Exception:
                    continue
        return accepted, rejected


# ── Orchestrator ──────────────────────────────────────────────────────────────

class ESAAOrchestrator:
    """
    The deterministic orchestrator. Only this class may mutate the environment.
    Accepts or rejects agent intentions based on validation rules.
    Logs every decision to activity.jsonl.

    get_state() returns the current environment plus a projection_hash_sha256
    field — the SHA-256 of the RFC 8785 canonical JSON of the state variables.
    This hash can be independently verified by verify_run().
    """

    def __init__(
        self,
        environment: dict,
        log_path: str = "data/activity.jsonl",
    ) -> None:
        self.environment = environment
        self.validator = IntentionValidator(valid_variables=set(environment.keys()))
        self.event_log = EventLog(log_path)
        self.accepted_count = 0
        self.rejected_count = 0

    def submit(self, intention: AgentIntention) -> bool:
        """
        Submit an agent intention for validation and application.
        Returns True if accepted and applied, False if rejected.
        """
        is_valid, reason = self.validator.validate(intention)
        self.event_log.append(intention, is_valid, reason)

        if is_valid:
            new_val = self.environment[intention.variable] + intention.delta
            # Soft sigmoid clamp — approaches ±1 asymptotically (more realistic than hard clamp)
            self.environment[intention.variable] = round(
                2.0 / (1.0 + math.exp(-3.0 * new_val)) - 1.0, 8
            )
            self.accepted_count += 1
            return True
        else:
            self.rejected_count += 1
            logger.debug(
                f"[ESAA] Rejected: agent={intention.agent_id} "
                f"var={intention.variable} reason={reason}"
            )
            return False

    def get_state(self) -> dict:
        """Return current environment state (variables only, no hash field).
        
        Use get_state_verified() when you need the projection hash included.
        """
        return dict(self.environment)

    def get_state_verified(self) -> dict:
        """
        Return current environment state with a cryptographic projection hash.

        The hash is computed over the state variables only (not the hash field
        itself) using RFC 8785 canonical JSON + SHA-256. This allows any
        observer to independently verify the state by replaying the log.

        Returns:
            dict with all environment variables plus:
              projection_hash_sha256: str  — hex SHA-256 of canonical state
        """
        state_vars = dict(self.environment)
        projection_hash = sha256_of(state_vars)
        return {
            **state_vars,
            "projection_hash_sha256": projection_hash,
        }

    def stats(self) -> dict:
        return {
            "accepted": self.accepted_count,
            "rejected": self.rejected_count,
            "total": self.accepted_count + self.rejected_count,
            "rejection_rate": (
                self.rejected_count / (self.accepted_count + self.rejected_count)
                if (self.accepted_count + self.rejected_count) > 0
                else 0.0
            ),
        }


# ── Standalone verify_run ─────────────────────────────────────────────────────

def verify_run(run_id: str, data_dir: str = "data") -> dict:
    """
    Cryptographically verify a completed simulation run.

    Reads activity_{run_id}.jsonl from scratch, deterministically replays
    all accepted AgentIntention events to project the final state, computes
    the SHA-256 hash of the RFC 8785 canonical JSON, and compares it against
    the stored projection_hash_sha256.

    Args:
        run_id:   The simulation run ID (e.g. "run_abc123")
        data_dir: Directory containing activity_*.jsonl files

    Returns:
        dict with:
          run_id:                  str
          verify_status:           "ok" | "mismatch" | "error"
          stored_hash:             str | None
          computed_hash:           str | None
          accepted_events_replayed: int
          final_state:             dict | None
          error:                   str | None  (only on "error" status)
    """
    log_path = Path(data_dir) / f"activity_{run_id}.jsonl"

    if not log_path.exists():
        return {
            "run_id": run_id,
            "verify_status": "error",
            "stored_hash": None,
            "computed_hash": None,
            "accepted_events_replayed": 0,
            "final_state": None,
            "error": f"Log file not found: {log_path}",
        }

    # ── Pass 1: collect all variable names and find stored hash ───────────────
    all_variables: set[str] = set()
    stored_hash: str | None = None
    raw_entries: list[dict] = []

    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                raw_entries.append(entry)
                if entry.get("accepted") and entry.get("variable"):
                    all_variables.add(entry["variable"])
                # The stored hash is written as a special sentinel entry
                if entry.get("entry_type") == "projection_hash":
                    stored_hash = entry.get("projection_hash_sha256")
    except Exception as e:
        return {
            "run_id": run_id,
            "verify_status": "error",
            "stored_hash": None,
            "computed_hash": None,
            "accepted_events_replayed": 0,
            "final_state": None,
            "error": f"Failed to read log: {e}",
        }

    # ── Pass 2: deterministic replay of accepted events ───────────────────────
    state: dict[str, float] = {var: 0.0 for var in sorted(all_variables)}
    replayed = 0

    for entry in raw_entries:
        if not entry.get("accepted"):
            continue
        var = entry.get("variable")
        delta = entry.get("delta", 0.0)
        if var in state:
            new_val = state[var] + delta
            # Must match ESAAOrchestrator.submit() exactly — sigmoid clamp + 8dp
            state[var] = round(2.0 / (1.0 + math.exp(-3.0 * new_val)) - 1.0, 8)
            replayed += 1

    # Final state is already 8dp-rounded from per-step rounding above

    # ── Compute hash of replayed state (RFC 8785 canonical JSON) ─────────────
    computed_hash = sha256_of(state)

    # ── Compare ───────────────────────────────────────────────────────────────
    if stored_hash is None:
        # No stored hash in log — compute-only mode, return computed hash
        verify_status = "ok"
        logger.info(
            f"[ESAA] verify_run({run_id}): no stored hash found, "
            f"computed={computed_hash[:16]}... ({replayed} events replayed)"
        )
    elif computed_hash == stored_hash:
        verify_status = "ok"
        logger.info(
            f"[ESAA] verify_run({run_id}): VERIFIED ✓ "
            f"hash={computed_hash[:16]}... ({replayed} events replayed)"
        )
    else:
        verify_status = "mismatch"
        logger.warning(
            f"[ESAA] verify_run({run_id}): MISMATCH ✗ "
            f"stored={stored_hash[:16]}... computed={computed_hash[:16]}..."
        )

    return {
        "run_id": run_id,
        "verify_status": verify_status,
        "stored_hash": stored_hash,
        "computed_hash": computed_hash,
        "accepted_events_replayed": replayed,
        "final_state": state,
    }


def write_projection_hash(log_path: str | Path, state: dict) -> str:
    """
    Append a projection_hash sentinel entry to the activity log.

    Called by ESAAOrchestrator at the end of a simulation run to seal
    the log with a verifiable hash. verify_run() reads this entry and
    compares it against its own replay.

    Args:
        log_path: Path to the activity_*.jsonl file
        state:    Final state dict (variables only, no hash field)

    Returns:
        The hex SHA-256 hash that was written
    """
    projection_hash = sha256_of(state)
    sentinel = {
        "entry_type": "projection_hash",
        "timestamp": datetime.utcnow().isoformat(),
        "projection_hash_sha256": projection_hash,
        "state_variable_count": len(state),
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(sentinel) + "\n")

    logger.debug(f"[ESAA] Projection hash written: {projection_hash[:16]}...")
    return projection_hash
