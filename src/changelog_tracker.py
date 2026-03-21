from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .changelog_context import ChangelogSource

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRACKER_FILE = PROJECT_ROOT / ".changelog_tracker.json"


@dataclass(frozen=True)
class ChangelogSelection:
    use_changelog: bool
    slug: Optional[str]


def _load_state() -> dict:
    if not TRACKER_FILE.is_file():
        return {}
    try:
        raw = TRACKER_FILE.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _save_state(state: dict) -> None:
    TRACKER_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def select_changelog_for_cycle(
    sources: List[ChangelogSource],
    every_n: int,
) -> ChangelogSelection:
    if every_n <= 0 or not sources:
        return ChangelogSelection(use_changelog=False, slug=None)

    state = _load_state()
    count = int(state.get("count", 0)) + 1
    use_changelog = count % every_n == 0
    slug: Optional[str] = None

    if use_changelog:
        last_index = int(state.get("last_index", -1))
        next_index = (last_index + 1) % len(sources)
        slug = sources[next_index].slug
        state["last_index"] = next_index

    state["count"] = count
    _save_state(state)

    return ChangelogSelection(use_changelog=use_changelog, slug=slug)
