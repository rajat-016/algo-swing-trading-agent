import time
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from threading import Lock

from core.logging import logger


@dataclass
class LatencyRecord:
    min_ms: float = 0.0
    max_ms: float = 0.0
    avg_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    count: int = 0


@dataclass
class ServiceMetrics:
    latency: LatencyRecord = field(default_factory=LatencyRecord)
    error_count: int = 0
    success_count: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[float] = None


class MetricsCollector:
    def __init__(self, window_size: int = 3600):
        self._window_size = window_size
        self._lock = Lock()
        self._services: Dict[str, ServiceMetrics] = defaultdict(ServiceMetrics)
        self._latency_buckets: Dict[str, List[float]] = defaultdict(
            lambda: deque(maxlen=10000)
        )
        self._throughput: Dict[str, List[float]] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self._error_log: List[Dict] = []
        self._api_calls: Dict[str, int] = defaultdict(int)
        self._api_errors: Dict[str, int] = defaultdict(int)

    def record_latency(self, service: str, latency_ms: float):
        with self._lock:
            bucket = self._latency_buckets[service]
            bucket.append(latency_ms)
            self._throughput[service].append(time.time())
            svc = self._services[service]
            svc.success_count += 1
            self._update_latency_stats(service, bucket)

    def record_error(self, service: str, error: str):
        with self._lock:
            svc = self._services[service]
            svc.error_count += 1
            svc.last_error = error
            svc.last_error_time = time.time()
            self._throughput[service].append(time.time())
            if len(self._error_log) >= 1000:
                self._error_log.pop(0)
            self._error_log.append({
                "service": service,
                "error": error,
                "timestamp": time.time(),
            })

    def record_api_call(self, endpoint: str, status_code: int):
        with self._lock:
            self._api_calls[endpoint] += 1
            if status_code >= 400:
                self._api_errors[endpoint] += 1

    def get_service_metrics(self, service: str) -> Optional[ServiceMetrics]:
        with self._lock:
            svc = self._services.get(service)
            if svc is None:
                return None
            bucket = self._latency_buckets.get(service, [])
            if bucket:
                self._update_latency_stats(service, bucket)
            return svc

    def get_all_metrics(self) -> Dict:
        with self._lock:
            result = {}
            for service, svc in self._services.items():
                bucket = self._latency_buckets.get(service, [])
                if bucket:
                    self._update_latency_stats(service, bucket)
                d = asdict(svc)
                d["throughput_rpm"] = self._calculate_throughput(service)
                result[service] = d
            return result

    def get_latency_summary(self) -> Dict[str, dict]:
        with self._lock:
            result = {}
            for service, bucket in self._latency_buckets.items():
                if bucket:
                    self._update_latency_stats(service, bucket)
                svc = self._services.get(service)
                if svc:
                    result[service] = asdict(svc.latency)
                    result[service]["throughput_rpm"] = self._calculate_throughput(service)
            return result

    def get_api_metrics(self) -> Dict:
        with self._lock:
            endpoints = {}
            for endpoint in set(list(self._api_calls.keys()) + list(self._api_errors.keys())):
                endpoints[endpoint] = {
                    "total_calls": self._api_calls.get(endpoint, 0),
                    "errors": self._api_errors.get(endpoint, 0),
                    "error_rate": (
                        self._api_errors.get(endpoint, 0) / self._api_calls.get(endpoint, 1)
                        if self._api_calls.get(endpoint, 0) > 0
                        else 0
                    ),
                }
            return {"endpoints": endpoints, "recent_errors": self._error_log[-50:]}

    def get_health_summary(self) -> Dict:
        with self._lock:
            total_errors = sum(s.error_count for s in self._services.values())
            total_calls = sum(s.success_count + s.error_count for s in self._services.values())
            degrading = []
            for service, svc in self._services.items():
                bucket = self._latency_buckets.get(service, [])
                if len(bucket) >= 10:
                    recent = list(bucket)[-10:]
                    if statistics.median(recent) > 5000:
                        degrading.append(service)
            return {
                "total_services": len(self._services),
                "total_calls": total_calls,
                "total_errors": total_errors,
                "error_rate": total_errors / total_calls if total_calls > 0 else 0,
                "degraded_services": degrading,
                "services_with_recent_errors": [
                    s for s, svc in self._services.items()
                    if svc.last_error_time and (time.time() - svc.last_error_time) < 300
                ],
            }

    def _update_latency_stats(self, service: str, bucket: List[float]):
        svc = self._services[service]
        if not bucket:
            return
        sorted_ms = sorted(bucket)
        n = len(sorted_ms)
        svc.latency = LatencyRecord(
            min_ms=sorted_ms[0],
            max_ms=sorted_ms[-1],
            avg_ms=statistics.mean(sorted_ms),
            p50_ms=sorted_ms[n // 2],
            p95_ms=sorted_ms[int(n * 0.95)],
            p99_ms=sorted_ms[int(n * 0.99)],
            count=n,
        )

    def _calculate_throughput(self, service: str) -> float:
        now = time.time()
        cutoff = now - 60
        recent = [t for t in self._throughput[service] if t > cutoff]
        return len(recent)


_collector: Optional[MetricsCollector] = None
_collector_lock = Lock()


def get_metrics_collector() -> MetricsCollector:
    global _collector
    if _collector is None:
        with _collector_lock:
            if _collector is None:
                _collector = MetricsCollector()
    return _collector
