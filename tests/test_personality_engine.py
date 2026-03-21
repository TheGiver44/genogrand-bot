from pathlib import Path

from src.personality_engine import PersonalityEngine


def _make_engine() -> PersonalityEngine:
    return PersonalityEngine(
        personality_dir=Path("personality"),
        projects_file=Path("projects-list.md"),
    )


def test_generate_tweet_within_character_limit():
    engine = _make_engine()
    for _ in range(10):
        tweet = engine.generate_project_tweet()
        assert isinstance(tweet, str)
        assert tweet.strip() != ""
        assert len(tweet) <= engine.max_tweet_chars


def test_generate_tweet_no_links_or_shill():
    engine = _make_engine()
    for _ in range(10):
        tweet = engine.generate_project_tweet()
        assert "http" not in tweet.lower()
        for banned in ("pump.fun", "$", "memecoin", "#crypto", "#web3"):
            assert banned.lower() not in tweet.lower()


def test_generate_tweet_at_most_one_hashtag():
    engine = _make_engine()
    for _ in range(10):
        tweet = engine.generate_project_tweet()
        hashtags = [t for t in tweet.split() if t.startswith("#")]
        assert len(hashtags) <= 1


def test_consecutive_tweets_are_unique():
    engine = _make_engine()
    tweets = [engine.generate_project_tweet() for _ in range(10)]
    unique = set(tweets)
    assert len(unique) >= 5, f"Expected >= 5 unique tweets out of 10, got {len(unique)}"


def test_tweets_do_not_share_same_opening():
    engine = _make_engine()
    tweets = [engine.generate_project_tweet() for _ in range(10)]
    first_words = [t.split()[0] for t in tweets]
    assert len(set(first_words)) > 1, "All tweets start with the same word"


def test_finalize_tweet_closes_dangling_thought():
    engine = _make_engine()
    raw = "It's not just about the tech, it's about the people, it's about creating a community that's"
    finalized = engine._finalize_tweet(raw, allow_links=False)
    assert finalized.endswith((".", "!", "?"))
    assert "mission" in finalized.lower()
