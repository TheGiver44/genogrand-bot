from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRACKER_FILE = PROJECT_ROOT / ".tweet_tracker.json"


def get_last_tweet_time() -> Optional[datetime]:
    """Read the timestamp of the most recent tweet from local tracker file."""
    if not TRACKER_FILE.exists():
        return None
    try:
        data = json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
        return datetime.fromisoformat(data["last_tweet_at"])
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.warning("Could not parse tweet tracker file: %s", exc)
        return None


def get_last_tweet_text() -> Optional[str]:
    """Read the text of the most recent tweet from local tracker file."""
    if not TRACKER_FILE.exists():
        return None
    try:
        data = json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
        return data.get("last_tweet_text")
    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("Could not parse tweet tracker file: %s", exc)
        return None


def record_tweet(tweet_id: str, text: str) -> None:
    """Persist the latest tweet metadata to a local tracker file."""
    data = {
        "last_tweet_at": datetime.utcnow().isoformat(),
        "last_tweet_id": tweet_id,
        "last_tweet_text": text,
    }
    TRACKER_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
