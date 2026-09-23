import pytest

from todo_list_api.api.rate_limit import (
    IDLE_BUCKET_TTL_SECONDS,
    SWEEP_INTERVAL_SECONDS,
    TokenBucketRateLimiter,
)

pytestmark = pytest.mark.anyio


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def limiter(clock: FakeClock) -> TokenBucketRateLimiter:
    return TokenBucketRateLimiter(
        capacity=3,
        refill_per_second=0.5,
        clock=clock,
    )


async def test_burst_up_to_capacity_is_allowed(
    limiter: TokenBucketRateLimiter,
) -> None:
    decisions = [await limiter.acquire("clancy") for _ in range(3)]

    assert all(decision.allowed for decision in decisions)


async def test_request_beyond_capacity_is_rejected_with_retry_after(
    limiter: TokenBucketRateLimiter,
) -> None:
    for _ in range(3):
        await limiter.acquire("clancy")

    decision = await limiter.acquire("clancy")

    assert not decision.allowed
    assert decision.retry_after_seconds == 2


async def test_tokens_refill_over_time(
    limiter: TokenBucketRateLimiter, clock: FakeClock
) -> None:
    for _ in range(3):
        await limiter.acquire("clancy")
    clock.advance(2.0)

    assert (await limiter.acquire("clancy")).allowed


async def test_refill_never_exceeds_capacity(
    limiter: TokenBucketRateLimiter, clock: FakeClock
) -> None:
    await limiter.acquire("clancy")
    clock.advance(3600.0)

    decisions = [await limiter.acquire("clancy") for _ in range(4)]

    assert [decision.allowed for decision in decisions] == [True, True, True, False]


async def test_buckets_are_isolated_per_key(
    limiter: TokenBucketRateLimiter,
) -> None:
    for _ in range(3):
        await limiter.acquire("clancy")

    assert (await limiter.acquire("nico")).allowed


async def test_idle_buckets_are_evicted(
    limiter: TokenBucketRateLimiter, clock: FakeClock
) -> None:
    await limiter.acquire("clancy")
    clock.advance(IDLE_BUCKET_TTL_SECONDS + SWEEP_INTERVAL_SECONDS)

    await limiter.acquire("nico")

    assert "clancy" not in limiter._buckets  # pyright: ignore[reportPrivateUsage]
