from __future__ import annotations

import asyncio
from pathlib import Path

from .crypto_social_bot import CryptoSocialBot


PROJECT_ROOT = Path(__file__).resolve().parents[1]


async def run_scheduler(interval_minutes: int = 720) -> None:
    """
    Simple forever-loop scheduler for production deployments.

    - Uses CryptoSocialBot, which enforces 12-hour min spacing (1–2 tweets/day).
    - Sleeps for `interval_minutes` between attempts (default 720 = 12 hours),
      keeping tweets rare, insightful, and under verified-account limits.
    """
    bot = CryptoSocialBot()
    while True:
        await bot.post_single_personality_tweet()
        await asyncio.sleep(interval_minutes * 60)


if __name__ == "__main__":
    asyncio.run(run_scheduler())

