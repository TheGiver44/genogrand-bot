import json
import tempfile
from pathlib import Path

from src import tweet_tracker


def test_record_and_read_tweet(tmp_path: Path):
    tracker_file = tmp_path / ".tweet_tracker.json"
    tweet_tracker.TRACKER_FILE = tracker_file

    assert tweet_tracker.get_last_tweet_time() is None
    assert tweet_tracker.get_last_tweet_text() is None

    tweet_tracker.record_tweet(tweet_id="123", text="hello world")

    assert tracker_file.exists()
    assert tweet_tracker.get_last_tweet_text() == "hello world"
    assert tweet_tracker.get_last_tweet_time() is not None


def test_corrupted_tracker_returns_none(tmp_path: Path):
    tracker_file = tmp_path / ".tweet_tracker.json"
    tracker_file.write_text("not valid json", encoding="utf-8")
    tweet_tracker.TRACKER_FILE = tracker_file

    assert tweet_tracker.get_last_tweet_time() is None
    assert tweet_tracker.get_last_tweet_text() is None


def test_record_overwrites_previous(tmp_path: Path):
    tracker_file = tmp_path / ".tweet_tracker.json"
    tweet_tracker.TRACKER_FILE = tracker_file

    tweet_tracker.record_tweet(tweet_id="1", text="first")
    tweet_tracker.record_tweet(tweet_id="2", text="second")

    assert tweet_tracker.get_last_tweet_text() == "second"
    data = json.loads(tracker_file.read_text(encoding="utf-8"))
    assert data["last_tweet_id"] == "2"
