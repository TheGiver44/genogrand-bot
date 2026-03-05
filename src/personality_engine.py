from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


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
        Generate a single tweet that reflects the user's journey and
        highlights one project/link from projects-list.

        This is deliberately conservative in length and style so it is
        safe to post without manual editing.
        """
        base_tone = (
            "Most days it feels less like chasing a bag and more like wrestling with "
            "what this whole crypto journey has cost and taught me."
        )

        tweet = (
            f"{base_tone} No tickers, no charts, just trying to process the wins, "
            "losses, and the stuff I wish I had said to the people I was grinding "
            "for while they were still here. #truth"
        )

        # Twitter / X hard limit is 280 characters – keep a safety buffer.
        if len(tweet) > 260:
            tweet = tweet[:257] + "..."

        return tweet

