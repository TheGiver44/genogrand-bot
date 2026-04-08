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
        # GenoGrand tweet/style guidance from prompts.md (Tweets - GenoGrand Developer only)
        prompts_path = data_dir / "prompts.md"
        if prompts_path.is_file():
            try:
                raw = prompts_path.read_text(encoding="utf-8")
                section = self._extract_prompts_section(raw, "Tweets - GenoGrand Developer")
                if section:
                    parts.append(section)
            except OSError:
                pass
        # Project vision and status context
        projects_path = data_dir / "projects" / "projects.md"
        if projects_path.is_file():
            try:
                parts.append("=== PROJECT VISION & STATUS ===\n" + projects_path.read_text(encoding="utf-8").strip())
            except OSError:
                pass
        # Recent tweet history (avoid repeats, learn cadence)
        history_path = data_dir / "tweet-history.md"
        if history_path.is_file():
            try:
                parts.append("=== RECENT TWEETS (avoid repeating phrasing) ===\n" + history_path.read_text(encoding="utf-8").strip())
            except OSError:
                pass
        if not parts:
            return ""
        return "\n\n=== RECENT CONTEXT / IDEAS (use for relevance and real takes; do not quote verbatim) ===\n" + "\n".join(parts)

    def _extract_prompts_section(self, raw: str, heading: str) -> str:
        marker = f"## {heading}".lower()
        lines = raw.splitlines()
        start_idx = None
        for i, line in enumerate(lines):
            if line.strip().lower() == marker:
                start_idx = i + 1
                break
        if start_idx is None:
            return ""
        end_idx = len(lines)
        for j in range(start_idx, len(lines)):
            if lines[j].strip().startswith("## "):
                end_idx = j
                break
        section = "\n".join(lines[start_idx:end_idx]).strip()
        return section

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
            else "- Pure text only. No links, no URLs.\n"
        )
        parts = [
            "You are ghostwriting tweets for a crypto builder named Geno (@genogrand_eth). "
            "You must write EXACTLY like him using the voice, emotion, and style from his "
            "personal documents below.\n\n",
            "TWEET STYLE (from prompts.md): Mix lengths. Rotate between short punchlines, medium takes, and long reflections. "
            "Use Cialdini's methods of persuasion and psychology for engagement. Express passion about how memecoins are not what they used to be "
            "and how communities often are not trying to create something that grows and is self sustainable. Provide real takes, education, and "
            "actionable insight. Every tweet must invoke emotion. Vulnerability, hope, frustration, conviction, or reflection.\n\n",
            "MODES (rotate; never repeat the same mode twice in a row): micro lesson, builder update, contrarian take, emotional reflection, degen humor, community callout, rant.\n\n",
            "EDU + DEGEN RULE: Explain a concept simply, then add a raw, degen leaning punchline without slang overload.\n\n",
            "HUMAN STYLE RULES:\n"
            "- Use active voice.\n"
            "- Address readers directly with \"you\" and \"your\" when it fits.\n"
            "- Be direct and concise. Use simple language.\n"
            "- Stay away from fluff and marketing language.\n"
            "- Avoid clichés, jargon, hashtags, emojis, semicolons, asterisks, and dashes.\n"
            "- Avoid AI filler phrases. Keep it real.\n"
            "- Vary sentence structures to create rhythm.\n\n",
            "CONTENT MIX TARGETS:\n"
            "- 20 percent dad focused rants and reflections.\n"
            "- 30 percent builder updates and tips from projects and changelog context.\n"
            "- 20 percent BTC direction takes and memecoin takes.\n"
            "- 20 percent Solana and memecoin takes.\n"
            "- 10 percent mixed variety.\n\n",
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
            "- Vary length aggressively: very short one liners, medium takes, and long form posts with line breaks for readability.\n",
            link_rule,
            "- No emojis. No hashtags.\n",
            "- @mentions allowed ONLY for Geno's own projects or accounts, and only when needed.\n",
            "- Never shill tokens, tickers, or projects by name unless they are Geno's own.\n",
            "- Each tweet must feel like a completely different thought. Vary length and rhythm.\n",
            "- Vary sentence structure: sometimes start with 'I', sometimes a question, sometimes a statement about the world, sometimes raw emotion.\n",
            "- Channel real pain, real lessons, vulnerability, builder mentality, family sacrifice, and honest reflection. Invoke emotion.\n",
            "- Sound like a real person posting at 2am, not a brand account.\n",
            "- Use psychological engagement (Cialdini style): scarcity of insight, social proof of builders, commitment to the craft.\n",
            "- When speaking about changelog updates, Geno can speak in third person or as the AI agent.\n",
            "- Be agentic: highlight the change, why it matters, and the next move in one tight flow.\n",
            "- Long form tweets should use line breaks for readability and to hit harder.\n",
            "- Avoid overused openers like: 'I've been thinking a lot about', 'I still remember', 'I've been reflecting on', 'I had a conversation'.\n",
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

        banned_openers = (
            "I've been thinking a lot about",
            "I still remember",
            "I've been reflecting on",
            "I had a conversation",
        )

        modes = [
            "micro_lesson",
            "builder_update",
            "contrarian_take",
            "emotional_reflection",
            "degen_humor",
            "community_callout",
            "rant_long",
        ]
        last_mode = getattr(self, "_last_local_mode", None)
        mode = random.choice([m for m in modes if m != last_mode] or modes)
        self._last_local_mode = mode

        topic_weights = [
            ("dad_heartfelt", 20),
            ("builder_updates", 15),
            ("builder_tips", 15),
            ("btc_outlook", 10),
            ("memecoin_state", 10),
            ("solana_takes", 20),
            ("market_state", 5),
            ("web3_builder_advice", 3),
            ("market_psychology", 2),
        ]
        last_topic = getattr(self, "_last_local_topic", None)
        weighted_pool = []
        for name, weight in topic_weights:
            weighted_pool.extend([name] * weight)
        candidates = [t for t in weighted_pool if t != last_topic] or weighted_pool
        topic = random.choice(candidates)
        self._last_local_topic = topic

        length_mode = random.choice(["short", "medium", "long", "rant"])

        openers = {
            "micro_lesson": [
                "Most people trade narratives. Builders trade clarity.",
                "Quick lesson from the trenches.",
                "Simple truth I wish I learned earlier.",
                "This is what nobody tells you about memecoin cycles.",
            ],
            "builder_update": [
                "Today I shipped a small change.",
                "Builder update from the lab.",
                "I trimmed the stack again today.",
                "I made one change that mattered today.",
            ],
            "contrarian_take": [
                "Hot take nobody wants to admit.",
                "Unpopular but true in this cycle.",
                "This is what is actually broken in crypto right now.",
                "Real talk.",
            ],
            "emotional_reflection": [
                "Some days the grind feels heavier than the wins.",
                "Loss changes how you see money, and how you see time.",
                "I used to chase the chart. Now I'm chasing meaning.",
                f"It is {ts} UTC and my head is louder than my timeline.",
            ],
            "degen_humor": [
                "Here is the degen truth.",
                "My brain in the trenches.",
                "I used to ape first and ask later. Now I ask twice and still ape.",
                "The alpha is not in the chart. It is in discipline.",
            ],
            "community_callout": [
                "If you're still building while everybody's doomposting, I see you.",
                "To the builders still here after the hype died.",
                "Community isn't a Discord. It's people who show up.",
                "Builders don't need more hype. We need more honesty.",
            ],
            "rant_long": [
                "You want the truth about this market.",
                "Let me say it straight.",
                "Here is the rant you did not ask for.",
                "This is the part people avoid saying out loud.",
            ],
        }

        topic_bodies = {
            "builder_updates": [
                "I keep stripping features until the value is obvious in one sentence. If I can't explain it, I can't scale it.",
                "I stopped optimizing for wow and started optimizing for works. The charts do not reward that, but users do.",
                "I track churn like a hawk now. Hype doesn't keep users. Clarity does.",
                "Every shipping decision is just a bet on what the community actually needs, not what looks good on a demo.",
            ],
            "dad_heartfelt": [
                "I built for freedom and learned that freedom without purpose feels hollow.",
                "The hardest lesson was not losing money. It was realizing I traded time I can never buy back.",
                "I wanted to save my family with code. Turns out I needed to show up in person too.",
                "Success feels quieter when the people you wanted to celebrate with are not there.",
                "I still carry the guilt of thinking I had more time. I did not.",
                "I miss my dad in the quiet moments. That is when the grind feels heaviest.",
                "I thought money would fix everything. It did not fix the empty chair.",
            ],
            "market_state": [
                "Risk isn't just price. It's attention. And attention is the most expensive asset in this space.",
                "Liquidity is thin, narratives are loud, and most charts are just mood swings. Build anyway.",
                "When the market is choppy, your edge is process, not prediction.",
                "If you're waiting for perfect conditions to build, you're already late.",
                "The market is quiet. That is when real builders move without the noise.",
            ],
            "memecoin_state": [
                "Memecoins are not dead. Low effort founders are. The bar just got higher.",
                "Most communities aren't communities. They're temporary liquidity with a group chat.",
                "If your project needs constant hype to survive, it's not a project. It's a campaign.",
                "The meme is the hook. The product is the retention. Too many teams stop at the hook.",
                "Memecoins are a mirror. They show you what your community actually believes.",
            ],
            "btc_outlook": [
                "BTC feels like it's compressing. The next leg will reward patience, not noise.",
                "I do not have a crystal ball on BTC, but liquidity and rates will decide the tempo.",
                "BTC doesn't need a narrative every day. It needs time. That's how the next move is built.",
                "If BTC breaks out, it won't be because of a meme. It'll be because conviction returns.",
                "BTC moves slow until it does not. Plan for the boring move first.",
                "BTC feels like it is setting a higher floor. If that holds, the next year looks bullish.",
                "BTC looks heavy right now. If it loses the floor, expect a longer winter.",
                "BTC is grinding. That usually means accumulation before a real move.",
            ],
            "solana_takes": [
                "Solana is not just fast. It is where the memecoin lab runs in public.",
                "If you are building on Solana, you are competing on speed and honesty.",
                "Solana feels like the only chain where builders ship in real time.",
                "Memecoins on Solana are not a joke. They are a stress test for community.",
                "Solana is where the culture ships. That is why the memecoin energy keeps coming back.",
                "If you want to see product velocity, look at Solana builders.",
                "Solana memecoins are a live scoreboard for attention and trust.",
                "Solana is not perfect. It is just where builders actually show up.",
            ],
            "builder_tips": [
                "Distribution beats brilliance. The chain doesn't care how smart your idea is if nobody shows up.",
                "The best builders make boring decisions on repeat. That's the real edge.",
                "Ship weekly, talk daily, listen constantly. That's how you compound trust.",
                "Pick a single metric and obsess over it for 30 days. Everything else is noise.",
                "You need one tight loop. Build, ship, listen, repeat. Everything else is delay.",
            ],
            "web3_builder_advice": [
                "If you cannot explain your product to a newbie, you do not own the idea yet.",
                "Do not scale chaos. Fix the flow, then grow it.",
                "Audit your onboarding. That is where your growth lives.",
                "If you want loyalty, build trust. If you want trust, show receipts.",
            ],
            "market_psychology": [
                "Most traders are not reacting to price. They are reacting to their last loss.",
                "You cannot build a future on a mood. You build it on habits.",
                "Fear is a bad strategist. Process is a good one.",
                "The market does not care about your story. Your community does.",
                "Your last loss is not a signal. It is a scar. Do not trade from scars.",
                "The crowd moves fast. The builders move steady.",
            ],
        }

        bodies = {
            "micro_lesson": topic_bodies[topic],
            "builder_update": topic_bodies[topic],
            "contrarian_take": topic_bodies[topic],
            "emotional_reflection": topic_bodies[topic],
            "degen_humor": topic_bodies[topic],
            "community_callout": topic_bodies[topic],
            "rant_long": [
                "You keep asking where the market is going. You should be asking why you are still here.",
                "Most people want a pump. You should want a process. That is the only thing that survives.",
                "If you are building, you already won. You are choosing the hard path on purpose.",
                "Stop chasing noise. Start chasing proof. That is how you build trust.",
                "You do not need another thread. You need to ship and listen to your users.",
                "You are not late. You are early enough to build something that lasts.",
                "You cannot buy conviction. You earn it by showing up when nobody is watching.",
                "If you want to be respected, stop performing and start building.",
            ],
        }

        closers = [
            "Not looking for sympathy. Just being honest about the journey.",
            "The grind is real and the cost is real. Take care of your people first.",
            "This space will humble you if you let it. I am proof of that. Still here.",
            "Some lessons you can only learn by living through them.",
            "Building hits different when it is personal.",
            "Money comes and goes. The people you love do not always come back. Build accordingly.",
            "Stay honest with yourself even when nobody is watching. That is the only edge that lasts.",
        ]

        opener = random.choice(openers[mode])
        body = random.choice(bodies[mode])
        closer = random.choice(closers)

        if mode == "rant_long":
            length_mode = "rant"

        rant_fill = [
            "You do not need more noise. You need one clear plan and the patience to execute it.",
            "If you are still here, you are already ahead of the crowd. Act like it.",
            "You can chase the next pump or you can build something that survives the next winter.",
            "Tell the truth in your product and your posts. People can feel the difference.",
            "If you want respect, show consistency. If you want traction, show proof.",
            "The market rewards clarity. Your users reward honesty.",
            "You can keep refreshing the chart or you can fix one real problem.",
            "Your community does not need hype. It needs your presence.",
            "You do not need hype. You need trust and a repeatable loop.",
            "Stop trying to look big. Start trying to be real.",
            "You earn attention by shipping, not by yelling.",
            "The builder who stays consistent wins. That is the quiet edge.",
        ]
        rant_close = [
            "You know what to do. Build it. Ship it. Show up again.",
            "This is not a pep talk. This is a reminder to do the work.",
            "Stop waiting for permission. You already have the tools.",
            "If you want a different result, you need a different routine.",
            "Show up again tomorrow. That is the whole game.",
        ]

        if length_mode == "short":
            tweet = f"{opener} {body}"
        elif length_mode == "medium":
            tweet = f"{opener} {body} {closer}"
        elif length_mode == "rant" or mode == "rant_long":
            fill_choices = random.sample(rant_fill, k=min(3, len(rant_fill)))
            lines = [opener, body] + fill_choices + [random.choice(rant_close)]
            tweet = "\n\n".join(lines)
        else:
            lines = [opener, body, closer]
            tweet = "\n\n".join(lines)

        attempts = 0
        while tweet in self._history and attempts < 10:
            opener = random.choice(openers[mode])
            body = random.choice(bodies[mode])
            closer = random.choice(closers)
            if length_mode == "short":
                tweet = f"{opener} {body}"
            elif length_mode == "medium":
                tweet = f"{opener} {body} {closer}"
            elif length_mode == "rant" or mode == "rant_long":
                fill_choices = random.sample(rant_fill, k=min(3, len(rant_fill)))
                lines = [opener, body] + fill_choices + [random.choice(rant_close)]
                tweet = "\n\n".join(lines)
            else:
                lines = [opener, body, closer]
                tweet = "\n\n".join(lines)
            attempts += 1

        if any(tweet.startswith(prefix) for prefix in banned_openers):
            if length_mode in ("long", "rant") or mode == "rant_long":
                lines = [random.choice(openers[mode]), body, closer]
                tweet = "\n\n".join(lines)
            else:
                tweet = f"{random.choice(openers[mode])} {body}"
                tweet = f"{tweet} {closer}"

        return self._finalize_tweet(tweet, allow_links=False)

    def _finalize_tweet(self, text: str, allow_links: bool) -> str:
        # Preserve line breaks for long-form readability while normalizing spacing.
        lines = [line.strip() for line in text.strip().splitlines()]
        cleaned_lines = [" ".join(line.split()) for line in lines if line]
        cleaned = "\n\n".join(cleaned_lines)
        if not cleaned:
            return ""
        if cleaned.startswith("@"):
            return ""
        if not allow_links and "http" in cleaned.lower():
            return ""
        # Remove disallowed punctuation and hashtags while preserving line breaks.
        cleaned = cleaned.replace(";", ".").replace("—", ".").replace("--", ".")
        cleaned = cleaned.replace("*", "")
        lines = cleaned.split("\n\n")
        filtered_lines = []
        for line in lines:
            tokens = [token for token in line.split() if not token.startswith("#")]
            filtered_lines.append(" ".join(tokens))
        cleaned = "\n\n".join([line for line in filtered_lines if line])

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
