import asyncio
from datetime import datetime, timedelta

from src.crypto_social_bot import RateLimiter


def test_rate_limiter_defaults_enforce_12_hour_spacing():
    rl = RateLimiter()
    assert rl.min_seconds_between_tweets == 43200  # 12 hours, 1–2 tweets/day
    assert rl.max_tweets_per_hour == 2


def test_rate_limiter_mark_tweeted_updates_state():
    rl = RateLimiter()
    assert rl._last_tweet_at is None  # type: ignore[attr-defined]
    assert rl._recent_tweets == []
    rl.mark_tweeted()
    assert rl._last_tweet_at is not None  # type: ignore[attr-defined]
    assert len(rl._recent_tweets) == 1


def test_rate_limiter_waits_when_called_too_soon():
    rl = RateLimiter(min_seconds_between_tweets=1, max_tweets_per_hour=5)
    rl._last_tweet_at = datetime.utcnow()  # type: ignore[attr-defined]

    async def run_wait() -> float:
        start = datetime.utcnow()
        await rl.wait_if_needed()
        end = datetime.utcnow()
        return (end - start).total_seconds()

    slept = asyncio.run(run_wait())
    assert slept >= 0.9

