from __future__ import annotations

import logging
import os
import random
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .changelog_context import (
    build_changelog_context,
    build_changelog_tweet_local,
    discover_changelog_sources,
    select_changelog_source,
)

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
        self.max_tweet_chars = int(os.environ.get("TWEET_MAX_CHARS", "4000"))
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
        # Full roundup for maximum insight and real takes
        roundup_path = data_dir / "february-2026-cryptoroundup.txt"
        if roundup_path.is_file():
            try:
                parts.append(roundup_path.read_text(encoding="utf-8").strip())
            except OSError:
                pass
        # GenoGrand tweet/style guidance from prompts.md (first ~2000 chars covers Tweets, Thread, Shitposter, Twitter Posts)
        prompts_path = data_dir / "prompts.md"
        if prompts_path.is_file():
            try:
                raw = prompts_path.read_text(encoding="utf-8")
                # Use GenoGrand sections: Tweets, Twitter Thread, Shitposter, Twitter Posts
                parts.append(raw[:2200].strip())
            except OSError:
                pass
        if not parts:
            return ""
        return "\n\n=== RECENT CONTEXT / IDEAS (use for relevance and real takes; do not quote verbatim) ===\n" + "\n".join(parts)

    def _build_system_prompt(
        self,
        changelog_context: str = "",
        allow_links: bool = False,
    ) -> str:
        data_context = self._load_data_context()
        max_chars = self.max_tweet_chars
        link_rule = (
            "- Links are allowed ONLY when sharing changelog/project updates, and only 1 link max as a CTA.\n"
            if allow_links
            else "- Pure text only. No links, no URLs, no @mentions, no emojis.\n"
        )
        parts = [
            "You are ghostwriting tweets for a crypto builder named Geno (@genogrand_eth). "
            "You must write EXACTLY like him using the voice, emotion, and style from his "
            "personal documents below.\n\n",
            "TWEET STYLE (from prompts.md): Craft LONG, insightful tweets. Expand on the subject as much as the character limit allows. "
            "Use Cialdini's methods of persuasion and psychology for engagement. Express passion about how memecoins aren't what they used to be "
            "and how communities often aren't trying to create something that grows and is self-sustainable. Provide REAL takes, education, and "
            "actionable insight. Every tweet must INVOKE EMOTION—vulnerability, hope, frustration, conviction, or reflection.\n\n",
            "THEME (weave in subtly): Build in public. The next crypto renaissance is developers and development democratized; AI is democratizing "
            "access so anyone can build and become their own bank. Be secretive but authentic and open.\n\n",
            f"=== HOW HE WRITES ===\n{self.profile.how_i_write[:2500]}\n\n",
            f"=== HIS STORY ===\n{self.profile.story[:2500]}\n\n",
        ]
        if data_context:
            parts.append(f"{data_context}\n\n")
        if changelog_context:
            parts.append(f"=== CHANGELOG CONTEXT (use for project update tweets) ===\n{changelog_context}\n\n")
        parts += [
            "RULES:\n",
            f"- Max {max_chars} characters. Use the full length when it adds insight, education, or emotional punch. This is a HARD limit—count carefully.\n",
            link_rule,
            "- No hashtags like #crypto #web3 #memecoin. At most one emotional hashtag like #truth or #realtalk.\n",
            "- Never shill tokens, tickers, or projects by name.\n",
            "- Each tweet must feel like a completely different thought. Long-form takes, not one-liners.\n",
            "- Vary sentence structure: sometimes start with 'I', sometimes a question, sometimes a statement about the world, sometimes raw emotion.\n",
            "- Channel real pain, real lessons, vulnerability, builder mentality, family sacrifice, and honest reflection. Invoke emotion.\n",
            "- Sound like a real person posting at 2am, not a brand account.\n",
            "- Use psychological engagement (Cialdini-style): scarcity of insight, social proof of builders, commitment to the craft.\n",
            "- When speaking about changelog updates, Geno can speak in third person or as the AI agent.\n",
            "- Be agentic: highlight the change, why it matters, and the next move in one tight flow.\n",
        ]
        return "".join(parts)

    def _generate_with_ai(
        self,
        last_tweet: Optional[str] = None,
        changelog_context: str = "",
        allow_links: bool = False,
    ) -> Optional[str]:
        history_context = ""
        if last_tweet:
            history_context = f"\nThe LAST tweet was: \"{last_tweet}\"\nDo NOT repeat or paraphrase it. Write something completely different.\n"

        user_message = (
            f"{history_context}"
            f"\nWrite exactly ONE tweet. Use the full {self.max_tweet_chars} characters if it adds insight, education, or emotion. Output only the tweet text, nothing else."
        )

        # Prefer GROQ when available (fast, insightful).
        if _groq_client is not None:
            tweet = self._generate_with_groq(
                user_message,
                changelog_context=changelog_context,
                allow_links=allow_links,
            )
            if tweet is not None:
                return tweet

        # Fallback to Gemini.
        if _AI_AVAILABLE and _gemini_model is not None:
            tweet = self._generate_with_gemini(
                user_message,
                changelog_context=changelog_context,
                allow_links=allow_links,
            )
            if tweet is not None:
                return tweet

        return None

    def _generate_with_groq(
        self,
        user_message: str,
        changelog_context: str = "",
        allow_links: bool = False,
    ) -> Optional[str]:
        if _groq_client is None:
            return None
        try:
            response = _groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": self._build_system_prompt(
                            changelog_context=changelog_context,
                            allow_links=allow_links,
                        ),
                    },
                    {"role": "user", "content": user_message},
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.85,
                max_tokens=200,
            )
            text = (response.choices[0].message.content or "").strip().strip('"').strip("'")
            if not text:
                return None
            finalized = self._finalize_tweet(text, allow_links=allow_links)
            return finalized or None
        except Exception as exc:
            logger.warning("GROQ generation failed, trying fallback: %s", exc)
            return None

    def _generate_with_gemini(
        self,
        user_message: str,
        changelog_context: str = "",
        allow_links: bool = False,
    ) -> Optional[str]:
        if not _AI_AVAILABLE or _gemini_model is None:
            return None
        prompt = f"{self._build_system_prompt(changelog_context=changelog_context, allow_links=allow_links)}{user_message}"
        try:
            response = _gemini_model.generate_content(prompt)
            text = response.text.strip().strip('"').strip("'")
            finalized = self._finalize_tweet(text, allow_links=allow_links)
            return finalized or None
        except Exception as exc:
            logger.warning("Gemini generation failed, falling back to local: %s", exc)
            return None

    def _generate_local(self) -> str:
        now = datetime.utcnow()
        ts = now.strftime("%H:%M")

        openers = [
            "I lost my dad while grinding in this space and it changed everything about how I see money. What we build has to mean something beyond the chart.",
            "People keep asking me why I build. Honestly, I'm still figuring that out myself. But I know the answer isn't in another pump.",
            "The hardest part of this journey isn't the losses, it's what you miss while chasing wins. Took me too long to learn that.",
            "Some nights I stare at the screen and wonder if any of this was worth what it cost me. Then I remember why I started.",
            "I used to think making it meant financial freedom. Now I think it means something deeper. Building something that outlives the cycle.",
            "Nobody tells you that building in this space can break you in ways money can't fix. The trenches teach you anyway.",
            "There's a version of me from two years ago who wouldn't recognize where I am now. Loss does that. So does building through it.",
            f"It's {ts} UTC and I'm wide awake thinking about every decision that led me here. Some I'd take back. Most I wouldn't.",
            "You ever build something you're proud of and still feel like you failed the people who matter most? That weight doesn't show on chain.",
            "Lost my tech job, lost my father, almost lost myself. But I'm still here building. Some days that's the only take that matters.",
            "The trenches teach you things no course or thread ever will. Real builders know the difference between hype and craft.",
            "What I've learned from every failed project is that the real loss is the time, not the money. Time you can't get back.",
            "Winning doesn't feel the same when the person you were winning for isn't here anymore. Build for something bigger than the bag.",
            "I've shipped projects that hit six figures and projects that went to zero. Both taught me something. Mostly about who I'm building for.",
            "Every builder in this space carries weight that doesn't show up on chain. Acknowledge it. Then keep building.",
        ]

        closers = [
            "Still processing, still building. #truth",
            "Not looking for sympathy, just being honest about the journey. If you've built, you know.",
            "If you've been through it, you know exactly what I mean. #realtalk",
            "The grind is real but so is the cost. Take care of your people first.",
            "Take care of your people before you take care of your portfolio. I learned that the hard way.",
            "This space will humble you if you let it. I'm proof of that. Still here.",
            "Some lessons you can only learn by living through them. No thread can replace that.",
            "Building hits different when it's personal. #truth",
            "Money comes and goes. The people you love don't always come back. Build accordingly.",
            "Stay honest with yourself even when nobody's watching. That's the only edge that lasts.",
        ]

        tweet = f"{random.choice(openers)} {random.choice(closers)}"

        attempts = 0
        while tweet in self._history and attempts < 10:
            tweet = f"{random.choice(openers)} {random.choice(closers)}"
            attempts += 1

        return self._finalize_tweet(tweet, allow_links=False)

    def _finalize_tweet(self, text: str, allow_links: bool) -> str:
        cleaned = " ".join(text.strip().split())
        if not cleaned:
            return ""
        if cleaned.startswith("@"):
            return ""
        if not allow_links and "http" in cleaned.lower():
            return ""

        max_chars = self.max_tweet_chars
        if len(cleaned) > max_chars:
            cleaned = self._truncate_to_sentence(cleaned, max_chars)

        return self._ensure_complete_thought(cleaned, max_chars)

    def _truncate_to_sentence(self, text: str, max_chars: int) -> str:
        prefix = text[:max_chars]
        last_end = max(prefix.rfind("."), prefix.rfind("!"), prefix.rfind("?"))
        if last_end >= 40:
            return prefix[: last_end + 1].strip()
        last_space = prefix.rfind(" ")
        if last_space > 0:
            return prefix[:last_space].strip()
        return prefix.strip()

    def _ensure_complete_thought(self, text: str, max_chars: int) -> str:
        if not text:
            return text
        terminal = text.endswith((".", "!", "?"))
        dangling = bool(
            re.search(
                r"(and|or|but|so|because|that|which|to|of|for|in|with|as|about|it's|thats|that's)$",
                text,
                re.IGNORECASE,
            )
        )
        if terminal and not dangling:
            return text

        closing = " That's the mission."
        if len(text) + len(closing) <= max_chars:
            return text.rstrip(".!?") + closing

        trimmed = text[: max_chars - len(closing)].rstrip()
        if not trimmed:
            return text[:max_chars].rstrip(".!?") + "."
        return trimmed + closing

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
        changelog_sources = discover_changelog_sources()
        changelog_context = ""
        allow_links = False

        if project_hint and project_hint.startswith("changelog:"):
            slug = project_hint.split(":", 1)[1].strip()
            source = select_changelog_source(changelog_sources, slug)
            if source is not None:
                changelog_context = build_changelog_context([source])
                allow_links = True
                tweet = self._generate_with_ai(
                    last_tweet=last_tweet,
                    changelog_context=changelog_context,
                    allow_links=allow_links,
                )
                if tweet is None:
                    tweet = build_changelog_tweet_local(source, self.max_tweet_chars)
                self._history.append(tweet)
                if len(self._history) > 50:
                    self._history = self._history[-50:]
                return tweet

        if not project_hint and changelog_sources:
            changelog_context = build_changelog_context(changelog_sources)

        tweet = self._generate_with_ai(
            last_tweet=last_tweet,
            changelog_context=changelog_context,
            allow_links=allow_links,
        )

        if tweet is None or tweet in self._history:
            tweet = self._generate_local()

        self._history.append(tweet)
        if len(self._history) > 50:
            self._history = self._history[-50:]

        return tweet
