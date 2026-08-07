"""
Performance and evaluation inspection hooks for Antigravity SDK.
Logs tool latency, payload byte sizes, and execution metrics to JSONL.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from config import METRICS_LOG_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("metrics_hook")


class MetricsHook:
    """SDK lifecycle inspection hook for performance logging and observability."""

    def __init__(self, log_path=METRICS_LOG_PATH):
        self.log_path = log_path
        self._tool_start_times: Dict[str, float] = {}

    def pre_tool_call(self, tool_name: str, args: Dict[str, Any]) -> None:
        """Invoked immediately before a tool is executed."""
        call_key = f"{tool_name}_{time.time()}"
        self._tool_start_times[tool_name] = time.time()
        logger.info(f"[PRE_TOOL_CALL] Executing tool '{tool_name}' with args: {args}")

    def post_tool_call(self, tool_name: str, args: Dict[str, Any], result: Any, error: Optional[Exception] = None) -> Dict[str, Any]:
        """
        Invoked immediately after a tool finishes execution. Calculates latency, payload size, and logs telemetry.
        """
        start_time = self._tool_start_times.pop(tool_name, time.time())
        latency_ms = round((time.time() - start_time) * 1000, 2)
        
        # Calculate payload size
        try:
            payload_bytes = len(json.dumps(result))
        except Exception:
            payload_bytes = len(str(result))

        metric_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "tool_name": tool_name,
            "args": args,
            "latency_ms": latency_ms,
            "payload_bytes": payload_bytes,
            "status": "error" if error else "success",
            "error_message": str(error) if error else None
        }

        # Append to JSONL metrics log file
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(metric_record) + "\n")
        except Exception as e:
            logger.error(f"Failed to log metric record: {e}")

        logger.info(f"[POST_TOOL_CALL] Tool '{tool_name}' completed in {latency_ms}ms, payload: {payload_bytes} bytes")
        return metric_record


# Global hook instance
metrics_hook = MetricsHook()
