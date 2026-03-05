from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import random


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class PersonalityProfile:
    """Lightweight container for the user's story and writing style."""

    how_i_write: str
    story: str
    projects_raw: str


class PersonalityEngine:
    """
    Generates tweets that loosely follow the user's tone and focus areas.

    This is intentionally simple to start with – it uses static documents
    and templates instead of any external AI services, so it is safe to
    run locally and extend over time.
    """

    def __init__(
        self,
        personality_dir: Optional[Path] = None,
        projects_file: Optional[Path] = None,
    ) -> None:
        base_dir = PROJECT_ROOT
        self.personality_dir = personality_dir or base_dir / "personality"
        self.projects_file = projects_file or base_dir / "projects-list.md"
        self.profile = self._load_profile()
        self._last_tweet: Optional[str] = None

    def _load_profile(self) -> PersonalityProfile:
        how_i_write_path = self.personality_dir / "howiwrite.txt"
        story_path = self.personality_dir / "story.txt"

        how_i_write = how_i_write_path.read_text(encoding="utf-8")
        story = story_path.read_text(encoding="utf-8")
        projects_raw = self.projects_file.read_text(encoding="utf-8")

        return PersonalityProfile(
            how_i_write=how_i_write,
            story=story,
            projects_raw=projects_raw,
        )

    def list_project_links(self) -> List[str]:
        """
        Very small heuristic: treat each non-empty line in projects-list
        that contains 'http' as a potential project or resource link.
        """
        lines = self.profile.projects_raw.splitlines()
        return [line.strip() for line in lines if "http" in line]

    def generate_project_tweet(
        self,
        project_hint: Optional[str] = None,
    ) -> str:
        """
        Generate a single tweet that reflects the user's journey.

        We keep things text-only, avoid links and shill language, and add a bit
        of controlled variability so tweets are not exact duplicates.
        """
        base_tone = (
            "Most days it feels less like chasing a bag and more like wrestling with "
            "what this whole crypto journey has cost and taught me."
        )

        now = datetime.utcnow()
        day_str = now.strftime("%b %d")
        time_str = now.strftime("%H:%M UTC")

        openings = [
            f"{base_tone} {day_str} at {time_str} hits different.",
            f"{base_tone} {day_str} {time_str} has me in my head again.",
            f"{base_tone} On {day_str} around {time_str} it feels heavier than usual.",
        ]

        middles = [
            "I'm replaying conversations I can't have anymore and trades I should've walked away from.",
            "I'm realizing how much of this grind was really about trying to protect the people I love.",
            "I'm weighing what this space has taken from me against what it's actually given back.",
        ]

        endings = [
            "No charts, no tickers, just honesty about why I'm still here. #truth",
            "Not here to sell you anything, just sharing what it really feels like. #truth",
            "If you feel this too, you're probably in the trenches for real. #truth",
        ]

        tweet = " ".join(
            [random.choice(openings), random.choice(middles), random.choice(endings)]
        )

        # Avoid repeating the exact same tweet text back-to-back.
        attempts = 0
        while self._last_tweet is not None and tweet == self._last_tweet and attempts < 5:
            tweet = " ".join(
                [
                    random.choice(openings),
                    random.choice(middles),
                    random.choice(endings),
                ]
            )
            attempts += 1

        # Keep under 240 characters for non-verified accounts.
        if len(tweet) > 240:
            tweet = tweet[:237] + "..."

        self._last_tweet = tweet

        return tweet

