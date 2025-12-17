from time import perf_counter
from aiogram import BaseMiddleware

from prometheus_client import Counter, Histogram

events_total = Counter(
    "bot_events_total",
    "Total incoming updates",
    ["event_type"]
)


handler_latency = Histogram(
    "bot_handler_latency_seconds",
    "Handler execution time"
)


class MetricsMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        events_total.labels(
            event_type=event.__class__.__name__
        ).inc()

        start = perf_counter()
        try:
            return await handler(event, data)
        finally:
            handler_latency.observe(perf_counter() - start)

