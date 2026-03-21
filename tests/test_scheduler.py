from pathlib import Path

from src import changelog_tracker
from src.scheduler import _resolve_changelog_hint


def test_resolve_changelog_hint_returns_hint_when_due(tmp_path: Path):
    changelog_tracker.TRACKER_FILE = tmp_path / ".changelog_tracker.json"
    hint = _resolve_changelog_hint(every_n=1)
    assert hint is not None
    assert hint.startswith("changelog:")


def test_resolve_changelog_hint_returns_none_when_not_due(tmp_path: Path):
    changelog_tracker.TRACKER_FILE = tmp_path / ".changelog_tracker.json"
    hint = _resolve_changelog_hint(every_n=3)
    assert hint is None
