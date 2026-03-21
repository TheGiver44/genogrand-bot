import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from src.crypto_social_bot import CryptoSocialBot


def _resolve_project_hint() -> str:
    slug = os.environ.get("CHANGELOG_SLUG", "boona").strip()
    if not slug:
        slug = "boona"
    return f"changelog:{slug}"


async def main() -> None:
    bot = CryptoSocialBot()
    project_hint = _resolve_project_hint()
    await bot.post_single_personality_tweet(project_hint=project_hint, attach_image=False)


if __name__ == "__main__":
    asyncio.run(main())
