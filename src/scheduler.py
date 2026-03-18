from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

from .crypto_social_bot import CryptoSocialBot
from .changelog_context import discover_changelog_sources
from .changelog_tracker import select_changelog_for_cycle


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _resolve_changelog_hint(every_n: int) -> Optional[str]:
    sources = discover_changelog_sources()
    selection = select_changelog_for_cycle(sources, every_n=every_n)
    if selection.use_changelog and selection.slug:
        return f"changelog:{selection.slug}"
    return None


async def run_scheduler(interval_minutes: int = 720) -> None:
    """
    Simple forever-loop scheduler for production deployments.

    - Uses CryptoSocialBot, which enforces 12-hour min spacing (1–2 tweets/day).
    - Sleeps for `interval_minutes` between attempts (default 720 = 12 hours),
      keeping tweets rare, insightful, and under verified-account limits.
    """
    bot = CryptoSocialBot()
    changelog_every_n = int(os.environ.get("CHANGELOG_EVERY_N", "5"))
    while True:
        project_hint = _resolve_changelog_hint(changelog_every_n)
        await bot.post_single_personality_tweet(project_hint=project_hint)
        await asyncio.sleep(interval_minutes * 60)


if __name__ == "__main__":
    asyncio.run(run_scheduler())
