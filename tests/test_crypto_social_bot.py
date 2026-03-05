import asyncio
import os
from pathlib import Path

from src.crypto_social_bot import CryptoSocialBot, RateLimiter
from src import tweet_tracker


class _FakeTwitterBot:
    def __init__(self) -> None:
        self.calls: list = []

    async def post_tweet(self, text, image_paths=None):  # type: ignore[override]
        self.calls.append({"text": text, "image_paths": image_paths})
        return {"success": True, "tweet_id": "fake123"}


def _setup_env_and_tracker(tmp_path: Path) -> None:
    os.environ.setdefault("TWITTER_API_KEY", "x")
    os.environ.setdefault("TWITTER_API_SECRET", "x")
    os.environ.setdefault("TWITTER_ACCESS_TOKEN", "x")
    os.environ.setdefault("TWITTER_ACCESS_TOKEN_SECRET", "x")
    tweet_tracker.TRACKER_FILE = tmp_path / ".tweet_tracker.json"


def _make_bot_with_fast_limiter() -> CryptoSocialBot:
    bot = CryptoSocialBot(rate_limiter=RateLimiter(min_seconds_between_tweets=0, max_tweets_per_hour=999))
    return bot


def test_post_single_personality_tweet_makes_one_call(tmp_path: Path):
    _setup_env_and_tracker(tmp_path)
    bot = _make_bot_with_fast_limiter()
    fake = _FakeTwitterBot()
    bot.twitter_bot = fake  # type: ignore[assignment]

    asyncio.run(bot.post_single_personality_tweet(attach_image=False))

    assert len(fake.calls) == 1


def test_tweet_is_recorded_after_posting(tmp_path: Path):
    _setup_env_and_tracker(tmp_path)
    bot = _make_bot_with_fast_limiter()
    fake = _FakeTwitterBot()
    bot.twitter_bot = fake  # type: ignore[assignment]

    asyncio.run(bot.post_single_personality_tweet(attach_image=False))

    assert tweet_tracker.TRACKER_FILE.exists()
    assert tweet_tracker.get_last_tweet_text() is not None
    assert tweet_tracker.get_last_tweet_time() is not None


def test_posted_tweet_text_is_unique(tmp_path: Path):
    _setup_env_and_tracker(tmp_path)
    bot = _make_bot_with_fast_limiter()
    fake = _FakeTwitterBot()
    bot.twitter_bot = fake  # type: ignore[assignment]

    for _ in range(3):
        asyncio.run(bot.post_single_personality_tweet(attach_image=False))

    texts = [c["text"] for c in fake.calls]
    assert len(set(texts)) == 3, f"Expected 3 unique tweets, got: {texts}"
