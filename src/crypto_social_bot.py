from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Sequence

from .base_bot import TwitterBot
from .personality_engine import PersonalityEngine


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class RateLimiter:
    """Very simple in-memory rate limiter to avoid hitting Twitter limits."""

    # Default: strictly no more than 1 tweet every 30 minutes
    min_seconds_between_tweets: int = 1800
    max_tweets_per_hour: int = 2
    _last_tweet_at: Optional[datetime] = None
    _recent_tweets: List[datetime] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self._recent_tweets is None:
            self._recent_tweets = []

    async def wait_if_needed(self) -> None:
        now = datetime.utcnow()

        if self._last_tweet_at is not None:
            delta = (now - self._last_tweet_at).total_seconds()
            if delta < self.min_seconds_between_tweets:
                sleep_for = self.min_seconds_between_tweets - delta
                await asyncio.sleep(sleep_for)

        one_hour_ago = now - timedelta(hours=1)
        self._recent_tweets = [
            ts for ts in self._recent_tweets if ts >= one_hour_ago
        ]

        if len(self._recent_tweets) >= self.max_tweets_per_hour:
            oldest = min(self._recent_tweets)
            wait_until = oldest + timedelta(hours=1)
            sleep_for = max(0.0, (wait_until - now).total_seconds())
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)

    def mark_tweeted(self) -> None:
        now = datetime.utcnow()
        self._last_tweet_at = now
        self._recent_tweets.append(now)


class CryptoSocialBot:
    """
    High-level coordinator that:
    - loads your personality documents
    - generates tweets in your voice
    - posts them to Twitter with basic rate limiting
    """

    def __init__(
        self,
        images_dir: Optional[Path] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        self.images_dir = images_dir or PROJECT_ROOT / "images"
        self.rate_limiter = rate_limiter or RateLimiter()
        self.personality = PersonalityEngine()
        self.twitter_bot = self._build_twitter_bot()

        # Seed rate limiter with the timestamp of the latest tweet so that
        # restarts respect spacing between tweets as much as possible.
        latest = self.twitter_bot.get_latest_tweet_time()
        if latest is not None and self.rate_limiter._last_tweet_at is None:  # type: ignore[attr-defined]
            self.rate_limiter._last_tweet_at = latest  # type: ignore[attr-defined]
            self.rate_limiter._recent_tweets.append(latest)  # type: ignore[attr-defined]

    def _build_twitter_bot(self) -> TwitterBot:
        api_key = os.environ.get("TWITTER_API_KEY")
        api_secret = os.environ.get("TWITTER_API_SECRET")
        access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
        access_token_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

        missing = [
            name
            for name, value in [
                ("TWITTER_API_KEY", api_key),
                ("TWITTER_API_SECRET", api_secret),
                ("TWITTER_ACCESS_TOKEN", access_token),
                ("TWITTER_ACCESS_TOKEN_SECRET", access_token_secret),
            ]
            if not value
        ]
        if missing:
            missing_str = ", ".join(missing)
            raise RuntimeError(
                f"Missing required Twitter credentials in environment: {missing_str}"
            )

        return TwitterBot(
            api_key=api_key or "",
            api_secret=api_secret or "",
            access_token=access_token or "",
            access_token_secret=access_token_secret or "",
        )

    def _pick_images(self, limit: int = 1) -> Sequence[Path]:
        if not self.images_dir.exists() or not self.images_dir.is_dir():
            return []
        image_files = sorted(
            [
                p
                for p in self.images_dir.iterdir()
                if p.is_file()
                and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}
            ]
        )
        return image_files[:limit]

    async def post_single_personality_tweet(
        self,
        project_hint: Optional[str] = None,
        attach_image: bool = True,
    ) -> None:
        """Generate one tweet and post it to Twitter."""
        tweet_text = self.personality.generate_project_tweet(project_hint=project_hint)

        await self.rate_limiter.wait_if_needed()

        image_paths: Sequence[Path] = []
        if attach_image:
            image_paths = self._pick_images(limit=1)

        result = await self.twitter_bot.post_tweet(
            text=tweet_text,
            image_paths=image_paths or None,
        )

        self.rate_limiter.mark_tweeted()

        if result and result.get("success"):
            print(f"Tweet posted successfully: {result.get('tweet_id')}")
        else:
            print(f"Error posting tweet: {result}")


async def main() -> None:
    """
    Manual test entrypoint.

    This will:
    - load your personality and projects
    - generate a tweet in your style
    - post exactly one tweet (optionally with an image)
    """
    bot = CryptoSocialBot()
    await bot.post_single_personality_tweet()


if __name__ == "__main__":
    asyncio.run(main())

