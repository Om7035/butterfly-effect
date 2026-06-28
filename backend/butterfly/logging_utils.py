"""Enhanced logging utilities for debugging and monitoring.

Provides:
- Rich, colorized terminal output
- Timing measurements
- Progress tracking
- Structured logging with context
"""

import sys
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Any, Dict

from loguru import logger


# Configure loguru with enhanced formatting
def setup_logging(debug: bool = False) -> None:
    """Initialize enhanced logging with colors and timing."""
    logger.remove()

    # Enhanced format with timestamps, colors, and context
    fmt = (
        "<level>[{time:HH:mm:ss.SSS}]</level> "
        "<level>{level: <8}</level> | "
        "<cyan>{name}:{function}:{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stdout,
        level="DEBUG" if debug else "INFO",
        format=fmt,
        colorize=True,
    )


class DebugTimer:
    """Context manager for timing operations with logging."""

    def __init__(self, label: str, logger_fn=None):
        self.label = label
        self.logger_fn = logger_fn or logger.info
        self.start_time = None
        self.elapsed = None

    def __enter__(self):
        self.start_time = time.time()
        logger.info(f"⏱️  START: {self.label}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.time() - self.start_time

        if exc_type:
            logger.error(f"❌ FAILED: {self.label} ({self.elapsed:.2f}s) - {exc_type.__name__}: {exc_val}")
        else:
            logger.info(f"✅ DONE: {self.label} ({self.elapsed:.2f}s)")

        return False


@contextmanager
def debug_block(label: str):
    """Context manager for block-level logging."""
    logger.info(f"▶️  BLOCK START: {label}")
    start = time.time()
    try:
        yield
        elapsed = time.time() - start
        logger.info(f"◀️  BLOCK END: {label} ({elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"❌ BLOCK ERROR: {label} ({elapsed:.2f}s) - {type(e).__name__}: {e}")
        raise


def log_data_sample(label: str, data: Any, max_items: int = 3) -> None:
    """Log a sample of data for debugging."""
    if isinstance(data, dict):
        logger.debug(f"📊 {label} (dict with {len(data)} keys):")
        for i, (k, v) in enumerate(data.items()):
            if i >= max_items:
                logger.debug(f"   ... and {len(data) - max_items} more")
                break
            logger.debug(f"   {k}: {str(v)[:100]}")

    elif isinstance(data, (list, tuple)):
        logger.debug(f"📊 {label} (list with {len(data)} items):")
        for i, item in enumerate(data):
            if i >= max_items:
                logger.debug(f"   ... and {len(data) - max_items} more")
                break
            logger.debug(f"   [{i}] {str(item)[:100]}")

    else:
        logger.debug(f"📊 {label}: {str(data)[:200]}")


def log_stage(stage: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Log a pipeline stage with structured output."""
    icons = {
        "start": "▶️ ",
        "running": "⚙️ ",
        "done": "✅",
        "error": "❌",
        "warning": "⚠️ ",
        "info": "ℹ️ ",
    }

    icon = icons.get(status, "• ")

    msg = f"{icon} STAGE [{stage}] {status.upper()}"

    if details:
        msg += " | " + " | ".join(f"{k}={v}" for k, v in details.items())

    if status == "error":
        logger.error(msg)
    elif status == "warning":
        logger.warning(msg)
    else:
        logger.info(msg)


def log_fetch_result(source: str, success: bool, count: int, latency: float, error: Optional[str] = None) -> None:
    """Log results from a data fetch operation."""
    status = "✅ SUCCESS" if success else "❌ FAILED"
    msg = f"FETCH [{source:15}] {status} | items={count:4} | {latency:6.2f}s"

    if error:
        logger.error(f"{msg} | error: {error}")
    elif success:
        logger.info(msg)
    else:
        logger.warning(msg)


def log_graph_build(nodes: int, edges: int, hops: int, elapsed: float) -> None:
    """Log graph building completion."""
    logger.info(
        f"📈 GRAPH BUILT | nodes={nodes} | edges={edges} | max_hops={hops} | {elapsed:.2f}s"
    )


def log_confidence_update(node_id: str, old_conf: float, new_conf: float, reason: str) -> None:
    """Log confidence score updates."""
    change = new_conf - old_conf
    icon = "📈" if change >= 0 else "📉"
    logger.debug(
        f"{icon} CONFIDENCE [{node_id:20}] {old_conf:.2f} → {new_conf:.2f} ({change:+.2f}) | {reason}"
    )


def log_simulation_tick(tick: int, agents: int, active: int, avg_certainty: float) -> None:
    """Log simulation progress."""
    progress = f"{active}/{agents}".ljust(8)
    logger.debug(
        f"⚙️  SIM TICK {tick:3d} | agents {progress} | avg_certainty={avg_certainty:.2f}"
    )


def log_backtest_result(case_name: str, predicted_hops: int, actual_hops: int, similarity: float, passed: bool) -> None:
    """Log backtesting results."""
    status = "✅ PASS" if passed else "⚠️  MISMATCH"
    logger.info(
        f"🧪 BACKTEST [{case_name:25}] {status} | predicted={predicted_hops} actual={actual_hops} | similarity={similarity:.2f}"
    )


def log_evidence_match(node_id: str, source: str, keyword: str, confidence_delta: float) -> None:
    """Log evidence matching for confidence updates."""
    direction = "+" if confidence_delta >= 0 else ""
    logger.debug(
        f"🔍 EVIDENCE [{node_id:20}] {source:15} keyword='{keyword}' delta={direction}{confidence_delta:+.2f}"
    )


class ProgressBar:
    """Simple progress bar for long-running operations."""

    def __init__(self, total: int, label: str = "Progress"):
        self.total = total
        self.label = label
        self.current = 0
        self.start_time = time.time()

    def update(self, increment: int = 1) -> None:
        """Update progress."""
        self.current += increment
        elapsed = time.time() - self.start_time

        if self.current % max(1, self.total // 10) == 0 or self.current == self.total:
            pct = (self.current / self.total) * 100
            rate = self.current / elapsed if elapsed > 0 else 0

            if self.current == self.total:
                logger.info(f"📊 {self.label}: {self.current}/{self.total} (100%) ✅ | {elapsed:.1f}s total")
            else:
                eta_secs = (self.total - self.current) / rate if rate > 0 else 0
                logger.info(f"📊 {self.label}: {self.current}/{self.total} ({pct:.0f}%) | {rate:.1f}/s | ETA {eta_secs:.0f}s")


# Module-level convenience functions
debug_timer = DebugTimer
log = logger

