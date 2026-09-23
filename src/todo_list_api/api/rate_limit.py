import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from anyio import Lock

IDLE_BUCKET_TTL_SECONDS = 900.0
SWEEP_INTERVAL_SECONDS = 60.0

type MonotonicClock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


class RateLimiter(Protocol):
    async def acquire(self, key: str) -> RateLimitDecision: ...


@dataclass(slots=True)
class _Bucket:
    tokens: float
    updated_at: float


@dataclass
class TokenBucketRateLimiter:
    capacity: int
    refill_per_second: float
    clock: MonotonicClock = time.monotonic
    _buckets: dict[str, _Bucket] = field(default_factory=dict, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)
    _swept_at: float = field(default=0.0, init=False)

    async def acquire(self, key: str) -> RateLimitDecision:
        async with self._lock:
            now = self.clock()
            self._sweep(now)
            bucket = self._refilled(key, now)

            if bucket.tokens < 1.0:
                return RateLimitDecision(
                    allowed=False,
                    retry_after_seconds=self._retry_after(bucket.tokens),
                )

            bucket.tokens -= 1.0
            return RateLimitDecision(allowed=True)

    def _refilled(self, key: str, now: float) -> _Bucket:
        bucket = self._buckets.get(key)

        if bucket is None:
            bucket = _Bucket(tokens=float(self.capacity), updated_at=now)
            self._buckets[key] = bucket
            return bucket

        elapsed = max(now - bucket.updated_at, 0.0)
        bucket.tokens = min(
            float(self.capacity),
            bucket.tokens + elapsed * self.refill_per_second,
        )
        bucket.updated_at = now
        return bucket

    def _retry_after(self, tokens: float) -> int:
        return max(1, math.ceil((1.0 - tokens) / self.refill_per_second))

    def _sweep(self, now: float) -> None:
        if now - self._swept_at < SWEEP_INTERVAL_SECONDS:
            return

        self._swept_at = now
        stale = [
            key
            for key, bucket in self._buckets.items()
            if now - bucket.updated_at > IDLE_BUCKET_TTL_SECONDS
        ]
        for key in stale:
            del self._buckets[key]
