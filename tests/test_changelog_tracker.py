from pathlib import Path

from src.changelog_context import ChangelogSource
from src import changelog_tracker


def test_select_changelog_for_cycle_respects_every_n(tmp_path: Path):
    tracker_file = tmp_path / ".changelog_tracker.json"
    changelog_tracker.TRACKER_FILE = tracker_file
    sources = [
        ChangelogSource(slug="one", name="One", path=Path("one.md"), cta_label=None, links=[]),
        ChangelogSource(slug="two", name="Two", path=Path("two.md"), cta_label=None, links=[]),
    ]

    selection = changelog_tracker.select_changelog_for_cycle(sources, every_n=3)
    assert selection.use_changelog is False
    assert selection.slug is None

    selection = changelog_tracker.select_changelog_for_cycle(sources, every_n=3)
    assert selection.use_changelog is False
    assert selection.slug is None

    selection = changelog_tracker.select_changelog_for_cycle(sources, every_n=3)
    assert selection.use_changelog is True
    assert selection.slug == "one"


def test_select_changelog_for_cycle_round_robins_sources(tmp_path: Path):
    tracker_file = tmp_path / ".changelog_tracker.json"
    changelog_tracker.TRACKER_FILE = tracker_file
    sources = [
        ChangelogSource(slug="alpha", name="Alpha", path=Path("a.md"), cta_label=None, links=[]),
        ChangelogSource(slug="beta", name="Beta", path=Path("b.md"), cta_label=None, links=[]),
    ]

    for _ in range(2):
        changelog_tracker.select_changelog_for_cycle(sources, every_n=2)

    selection = changelog_tracker.select_changelog_for_cycle(sources, every_n=2)
    assert selection.slug == "alpha"

    changelog_tracker.select_changelog_for_cycle(sources, every_n=2)
    selection = changelog_tracker.select_changelog_for_cycle(sources, every_n=2)
    assert selection.slug == "beta"
