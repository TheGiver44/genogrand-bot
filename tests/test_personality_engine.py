from pathlib import Path

from src.personality_engine import PersonalityEngine


def test_generate_project_tweet_basic():
    engine = PersonalityEngine(
        personality_dir=Path("personality"),
        projects_file=Path("projects-list.md"),
    )

    tweet = engine.generate_project_tweet()

    assert isinstance(tweet, str)
    assert tweet.strip() != ""
    assert len(tweet) <= 240
    # Avoid obvious promotional patterns
    assert "http" not in tweet.lower()
    for banned in ("pump.fun", "$", "memecoin", "#crypto", "#web3"):
        assert banned.lower() not in tweet.lower()
    # Allow at most one hashtag and keep it non-crypto
    hashtags = [token for token in tweet.split() if token.startswith("#")]
    assert len(hashtags) <= 1


def test_generate_project_tweet_not_repeated():
    engine = PersonalityEngine(
        personality_dir=Path("personality"),
        projects_file=Path("projects-list.md"),
    )

    seen = set()
    for _ in range(5):
        tweet = engine.generate_project_tweet()
        seen.add(tweet)

    # With our combinatorial template, it's extremely unlikely all 5 are identical.
    assert len(seen) > 1

