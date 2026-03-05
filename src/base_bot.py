from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import tweepy


class TwitterBot:
    """
    Thin wrapper around Tweepy that handles basic tweeting and
    optional media uploads.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_token_secret: str,
    ) -> None:
        """Initialize Twitter bot with API credentials."""
        self.auth = tweepy.OAuthHandler(api_key, api_secret)
        self.auth.set_access_token(access_token, access_token_secret)

        # v2 client for posting tweets
        self.client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )

        # v1.1 API for media uploads
        self.media_api = tweepy.API(self.auth)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def _upload_media(self, image_paths: Sequence[Path]) -> List[str]:
        media_ids: List[str] = []
        for image_path in image_paths:
            try:
                media = self.media_api.media_upload(filename=str(image_path))
                media_ids.append(media.media_id_string)
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.error("Error uploading media %s: %s", image_path, exc)
        return media_ids

    async def post_tweet(
        self,
        text: str,
        image_paths: Optional[Sequence[Path]] = None,
    ) -> Optional[Dict[str, object]]:
        """Post a tweet (optionally with images) with error handling."""
        try:
            media_ids: Optional[Sequence[str]] = None
            if image_paths:
                media_ids = self._upload_media(image_paths)
                if not media_ids:
                    self.logger.warning("No media_ids returned; tweeting text only.")

            response = self.client.create_tweet(text=text, media_ids=media_ids)
            tweet_id = response.data["id"]
            self.logger.info("Tweet posted successfully! Tweet ID: %s", tweet_id)
            return {
                "success": True,
                "tweet_id": tweet_id,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error("Error posting tweet: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "timestamp": datetime.now().isoformat(),
            }

    async def schedule_tweets(
        self,
        tweets: List[str],
        interval_minutes: int = 60,
    ) -> None:
        """Schedule multiple tweets with a specified interval."""
        for tweet in tweets:
            result = await self.post_tweet(tweet)
            if result and result.get("success"):
                self.logger.info(
                    "Waiting %s minutes until next tweet...", interval_minutes
                )
                time.sleep(interval_minutes * 60)
            else:
                self.logger.error("Stopping schedule due to error")
                break
