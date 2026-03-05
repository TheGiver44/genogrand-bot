import os

import pytest

from src.crypto_social_bot import CryptoSocialBot


class _FakeTwitterBot:
    def __init__(self) -> None:
        self.calls = []

    async def post_tweet(self, text, image_paths=None):  # type: ignore[override]
        self.calls.append({"text": text, "image_paths": image_paths})
        return {"success": True, "tweet_id": "fake123"}


@pytest.mark.asyncio
async def test_post_single_personality_tweet_makes_one_call(monkeypatch):
    # Provide dummy credentials so CryptoSocialBot can initialize.
    os.environ.setdefault("TWITTER_API_KEY", "x")
    os.environ.setdefault("TWITTER_API_SECRET", "x")
    os.environ.setdefault("TWITTER_ACCESS_TOKEN", "x")
    os.environ.setdefault("TWITTER_ACCESS_TOKEN_SECRET", "x")

    bot = CryptoSocialBot()
    fake = _FakeTwitterBot()
    bot.twitter_bot = fake  # type: ignore[assignment]

    await bot.post_single_personality_tweet(attach_image=False)

    assert len(fake.calls) == 1

