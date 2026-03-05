"""
Isolated test proving the old get_latest_tweet_time API approach is gone
and the file-based tracker works correctly as a replacement.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

from src import tweet_tracker
from src.crypto_social_bot import CryptoSocialBot, RateLimiter
import os


def test_tracker_seeds_rate_limiter_on_init(tmp_path: Path):
    """
    Simulate a restart: write a tracker file with a recent timestamp,
    then create a CryptoSocialBot and verify the rate limiter is seeded
    from the file (not from an API call that would 401).
    """
    os.environ.setdefault("TWITTER_API_KEY", "x")
    os.environ.setdefault("TWITTER_API_SECRET", "x")
    os.environ.setdefault("TWITTER_ACCESS_TOKEN", "x")
    os.environ.setdefault("TWITTER_ACCESS_TOKEN_SECRET", "x")

    tracker_file = tmp_path / ".tweet_tracker.json"
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)

    data = {
        "last_tweet_at": five_min_ago.isoformat(),
        "last_tweet_id": "999",
        "last_tweet_text": "previous tweet text here",
    }
    tracker_file.write_text(json.dumps(data), encoding="utf-8")
    tweet_tracker.TRACKER_FILE = tracker_file

    bot = CryptoSocialBot()

    assert bot.rate_limiter._last_tweet_at is not None  # type: ignore[attr-defined]
    assert len(bot.rate_limiter._recent_tweets) == 1  # type: ignore[attr-defined]
    assert "previous tweet text here" in bot.personality._history


def test_tracker_not_present_starts_fresh(tmp_path: Path):
    """
    Without a tracker file the bot should start with no rate limiter
    history and no personality history.
    """
    os.environ.setdefault("TWITTER_API_KEY", "x")
    os.environ.setdefault("TWITTER_API_SECRET", "x")
    os.environ.setdefault("TWITTER_ACCESS_TOKEN", "x")
    os.environ.setdefault("TWITTER_ACCESS_TOKEN_SECRET", "x")

    tweet_tracker.TRACKER_FILE = tmp_path / "nonexistent.json"

    bot = CryptoSocialBot()

    assert bot.rate_limiter._last_tweet_at is None  # type: ignore[attr-defined]
    assert len(bot.rate_limiter._recent_tweets) == 0  # type: ignore[attr-defined]
    assert len(bot.personality._history) == 0
