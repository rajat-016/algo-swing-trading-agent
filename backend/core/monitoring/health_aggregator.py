import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from core.logging import logger


@dataclass
class HealthComponent:
    name: str
    status: str  # healthy, degraded, unhealthy
    message: str = ""
    latency_ms: float = 0.0
    details: Optional[Dict] = None


class SystemHealthAggregator:
    def __init__(self):
        self._checks: Dict[str, Callable[[], HealthComponent]] = {}

    def register_check(self, name: str, check_fn: Callable[[], HealthComponent]):
        self._checks[name] = check_fn

    def run_all(self) -> Dict:
        components = {}
        overall_status = "healthy"
        degraded_count = 0
        unhealthy_count = 0

        for name, check_fn in self._checks.items():
            start = time.monotonic()
            try:
                result = check_fn()
            except Exception as e:
                result = HealthComponent(
                    name=name,
                    status="unhealthy",
                    message=f"Check raised exception: {e}",
                )
            elapsed = (time.monotonic() - start) * 1000
            result.latency_ms = round(elapsed, 1)
            components[name] = asdict(result)

            if result.status == "unhealthy":
                unhealthy_count += 1
                overall_status = "unhealthy"
            elif result.status == "degraded":
                degraded_count += 1
                if overall_status != "unhealthy":
                    overall_status = "degraded"

        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": components,
            "summary": {
                "total": len(components),
                "healthy": sum(
                    1 for c in components.values() if c.get("status") == "healthy"
                ),
                "degraded": degraded_count,
                "unhealthy": unhealthy_count,
            },
            "response_time_ms": round(
                sum(c.get("latency_ms", 0) for c in components.values()), 1
            ),
        }


_aggregator: Optional[SystemHealthAggregator] = None


def get_health_aggregator() -> SystemHealthAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = SystemHealthAggregator()
    return _aggregator
