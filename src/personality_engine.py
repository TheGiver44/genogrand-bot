from __future__ import annotations

import logging
import os
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_AI_AVAILABLE = False
_gemini_model = None
_groq_client = None

try:
    import google.generativeai as genai  # type: ignore[import-untyped]

    _api_key = os.environ.get("GEMINI_API_KEY", "")
    if _api_key:
        genai.configure(api_key=_api_key)
        _gemini_model = genai.GenerativeModel("gemini-2.0-flash")
        _AI_AVAILABLE = True
except ImportError:
    pass

try:
    from groq import Groq

    _groq_key = os.environ.get("GROQ_API_KEY", "")
    if _groq_key:
        _groq_client = Groq(api_key=_groq_key)
except ImportError:
    _groq_client = None


@dataclass
class PersonalityProfile:
    """Lightweight container for the user's story and writing style."""

    how_i_write: str
    story: str
    projects_raw: str


class PersonalityEngine:
    """
    Agentic tweet generator that writes in the user's authentic voice.

    Primary path: uses Google Gemini (free tier) with full personality
    context to craft a unique tweet every time.

    Fallback path: a local algorithm with wide variety and zero shared
    prefixes so tweets never start with the same words.
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
        self._history: List[str] = []

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
        lines = self.profile.projects_raw.splitlines()
        return [line.strip() for line in lines if "http" in line]

    def _load_data_context(self) -> str:
        """Load recent crypto context and ideas from data/ for richer, timely tweets."""
        data_dir = PROJECT_ROOT / "data"
        if not data_dir.exists() or not data_dir.is_dir():
            return ""
        parts: List[str] = []
        for name in ("february-2026-cryptoroundup.txt", "prompts.md"):
            path = data_dir / name
            if not path.is_file():
                continue
            try:
                raw = path.read_text(encoding="utf-8")
                # Keep snippet to avoid token overflow; prompts.md use GenoGrand tweet section
                if name == "prompts.md":
                    raw = raw[:800]
                parts.append(raw[:1200].strip())
            except OSError:
                continue
        if not parts:
            return ""
        return "\n\n=== RECENT CONTEXT / IDEAS (use for relevance, do not quote verbatim) ===\n" + "\n".join(parts)

    def _build_system_prompt(self) -> str:
        data_context = self._load_data_context()
        return (
            "You are ghostwriting tweets for a crypto builder named Geno (@genogrand_eth). "
            "You must write EXACTLY like him using the voice, emotion, and style from his "
            "personal documents below. Each tweet must be VERY insightful and engaging—the kind that stops the scroll.\n\n"
            "THEME (weave in subtly, never preachy): Build in public. The next crypto renaissance is not traders as kings—it's "
            "developers and development democratized. AI is democratizing access to crypto so anyone can build and "
            "become their own bank as easy as 1-2-3. Be secretive but authentic and open.\n\n"
            "=== HOW HE WRITES ===\n"
            f"{self.profile.how_i_write[:1500]}\n\n"
            "=== HIS STORY ===\n"
            f"{self.profile.story[:1500]}\n\n"
            + (f"{data_context}\n\n" if data_context else "")
            + "RULES:\n"
            "- Max 230 characters. This is a HARD limit, count carefully.\n"
            "- Pure text only. No links, no URLs, no @mentions, no emojis.\n"
            "- No hashtags like #crypto #web3 #memecoin. At most one emotional hashtag like #truth or #realtalk.\n"
            "- Never shill tokens, tickers, or projects by name.\n"
            "- Each tweet must feel like a completely different thought.\n"
            "- Vary sentence structure: sometimes start with 'I', sometimes a question, "
            "sometimes a statement about the world, sometimes raw emotion.\n"
            "- Channel real pain, real lessons, vulnerability, builder mentality, "
            "family sacrifice, and honest reflection.\n"
            "- Sound like a real person posting at 2am, not a brand account.\n"
            "- Use psychological engagement (e.g. Cialdini-style) where it fits: scarcity of insight, social proof of builders, commitment to the craft.\n"
        )

    def _generate_with_ai(self, last_tweet: Optional[str] = None) -> Optional[str]:
        history_context = ""
        if last_tweet:
            history_context = f"\nThe LAST tweet was: \"{last_tweet}\"\nDo NOT repeat or paraphrase it. Write something completely different.\n"

        user_message = (
            f"{history_context}"
            "\nWrite exactly ONE tweet. Output only the tweet text, nothing else."
        )

        # Prefer GROQ when available (fast, insightful).
        if _groq_client is not None:
            tweet = self._generate_with_groq(user_message)
            if tweet is not None:
                return tweet

        # Fallback to Gemini.
        if _AI_AVAILABLE and _gemini_model is not None:
            tweet = self._generate_with_gemini(user_message)
            if tweet is not None:
                return tweet

        return None

    def _generate_with_groq(self, user_message: str) -> Optional[str]:
        if _groq_client is None:
            return None
        try:
            response = _groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": user_message},
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.85,
                max_tokens=120,
            )
            text = (response.choices[0].message.content or "").strip().strip('"').strip("'")
            if not text:
                return None
            if len(text) > 240:
                text = text[:237] + "..."
            if "http" in text.lower() or text.strip().startswith("@"):
                return None
            return text
        except Exception as exc:
            logger.warning("GROQ generation failed, trying fallback: %s", exc)
            return None

    def _generate_with_gemini(self, user_message: str) -> Optional[str]:
        if not _AI_AVAILABLE or _gemini_model is None:
            return None
        prompt = f"{self._build_system_prompt()}{user_message}"
        try:
            response = _gemini_model.generate_content(prompt)
            text = response.text.strip().strip('"').strip("'")
            if len(text) > 240:
                text = text[:237] + "..."
            if "http" in text.lower() or text.startswith("@"):
                return None
            return text
        except Exception as exc:
            logger.warning("Gemini generation failed, falling back to local: %s", exc)
            return None

    def _generate_local(self) -> str:
        now = datetime.utcnow()
        ts = now.strftime("%H:%M")

        openers = [
            "I lost my dad while grinding in this space and it changed everything about how I see money.",
            "People keep asking me why I build. Honestly, I'm still figuring that out myself.",
            "The hardest part of this journey isn't the losses, it's what you miss while chasing wins.",
            "Some nights I stare at the screen and wonder if any of this was worth what it cost me.",
            "I used to think making it meant financial freedom. Now I think it means something deeper.",
            "Nobody tells you that building in this space can break you in ways money can't fix.",
            "There's a version of me from two years ago who wouldn't recognize where I am now.",
            f"It's {ts} UTC and I'm wide awake thinking about every decision that led me here.",
            "You ever build something you're proud of and still feel like you failed the people who matter most?",
            "Lost my tech job, lost my father, almost lost myself. But I'm still here building.",
            "The trenches teach you things no course or thread ever will.",
            "What I've learned from every failed project is that the real loss is the time, not the money.",
            "Winning doesn't feel the same when the person you were winning for isn't here anymore.",
            "I've shipped projects that hit six figures and projects that went to zero. Both taught me something.",
            "Every builder in this space carries weight that doesn't show up on chain.",
        ]

        closers = [
            "Still processing, still building. #truth",
            "Not looking for sympathy, just being honest about the journey.",
            "If you've been through it, you know exactly what I mean. #realtalk",
            "The grind is real but so is the cost. Remember that.",
            "Take care of your people before you take care of your portfolio.",
            "This space will humble you if you let it. I'm proof of that.",
            "Some lessons you can only learn by living through them.",
            "Building hits different when it's personal. #truth",
            "Money comes and goes. The people you love don't always come back.",
            "Stay honest with yourself even when nobody's watching.",
        ]

        tweet = f"{random.choice(openers)} {random.choice(closers)}"

        attempts = 0
        while tweet in self._history and attempts < 10:
            tweet = f"{random.choice(openers)} {random.choice(closers)}"
            attempts += 1

        if len(tweet) > 240:
            tweet = tweet[:237] + "..."

        return tweet

    def generate_project_tweet(
        self,
        project_hint: Optional[str] = None,
    ) -> str:
        """
        Generate a single unique tweet in the user's authentic voice.

        Tries AI first (Gemini), falls back to local combinatorial algorithm.
        Tracks recent history to avoid repeats.
        """
        last_tweet = self._history[-1] if self._history else None

        tweet = self._generate_with_ai(last_tweet=last_tweet)

        if tweet is None or tweet in self._history:
            tweet = self._generate_local()

        self._history.append(tweet)
        if len(self._history) > 50:
            self._history = self._history[-50:]

        return tweet
