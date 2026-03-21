from pathlib import Path

from src.changelog_context import (
    build_changelog_context,
    build_changelog_tweet_local,
    discover_changelog_sources,
    select_changelog_source,
)


def test_discover_changelog_sources_includes_boona_and_self():
    sources = discover_changelog_sources()
    slugs = {source.slug for source in sources}
    assert "boona" in slugs
    assert "genogrand_bot" in slugs


def test_build_changelog_context_returns_snippet():
    sources = discover_changelog_sources()
    context = build_changelog_context(sources)
    assert isinstance(context, str)
    assert context.strip() != ""


def test_build_changelog_tweet_local_includes_cta_link_when_available():
    sources = discover_changelog_sources()
    source = select_changelog_source(sources, "boona")
    assert source is not None
    tweet = build_changelog_tweet_local(source, max_chars=4000)
    assert "http" in tweet.lower()
