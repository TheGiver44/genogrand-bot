from __future__ import annotations

import json
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHANGELOG_DIR = PROJECT_ROOT / "data" / "changelogs"
SELF_CHANGELOG = PROJECT_ROOT / "CHANGELOG.md"
LINKS_FILE = CHANGELOG_DIR / "links.json"


@dataclass(frozen=True)
class ChangelogSource:
    slug: str
    name: str
    path: Path
    cta_label: Optional[str]
    links: List[str]


def _clean_md(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    return " ".join(text.strip().split())


def _load_links() -> Dict[str, Dict[str, object]]:
    if not LINKS_FILE.is_file():
        return {}
    try:
        raw = LINKS_FILE.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def discover_changelog_sources() -> List[ChangelogSource]:
    links_config = _load_links()
    sources: List[ChangelogSource] = []

    if CHANGELOG_DIR.exists():
        for path in sorted(CHANGELOG_DIR.glob("*.md")):
            slug = path.stem.lower()
            config = links_config.get(slug, {}) if isinstance(links_config, dict) else {}
            name = str(config.get("name", slug.replace("-", " "))).strip() or slug
            cta_label = str(config.get("cta_label")).strip() if config.get("cta_label") else None
            links = [str(link) for link in config.get("links", []) if isinstance(link, str)]
            sources.append(
                ChangelogSource(
                    slug=slug,
                    name=name,
                    path=path,
                    cta_label=cta_label,
                    links=links,
                )
            )

    if SELF_CHANGELOG.is_file():
        config = links_config.get("genogrand_bot", {}) if isinstance(links_config, dict) else {}
        name = str(config.get("name", "Geno Agent")).strip() or "Geno Agent"
        cta_label = str(config.get("cta_label")).strip() if config.get("cta_label") else None
        links = [str(link) for link in config.get("links", []) if isinstance(link, str)]
        sources.append(
            ChangelogSource(
                slug="genogrand_bot",
                name=name,
                path=SELF_CHANGELOG,
                cta_label=cta_label,
                links=links,
            )
        )

    return sources


def _extract_latest_section(text: str) -> str:
    lines = text.splitlines()
    header_indices = [i for i, line in enumerate(lines) if line.strip().startswith("## ")]
    if not header_indices:
        return ""
    start = header_indices[0]
    end = header_indices[1] if len(header_indices) > 1 else len(lines)
    return "\n".join(lines[start:end]).strip()


def _extract_section_heading(section: str) -> str:
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            return _clean_md(stripped.lstrip("# "))
    return "Update"


def _extract_bullets(section: str, limit: int = 4) -> List[str]:
    bullets: List[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(_clean_md(stripped[2:]))
        if len(bullets) >= limit:
            break
    return bullets


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    truncated = textwrap.shorten(text, width=max_chars, placeholder="...")
    return truncated if truncated else text[: max_chars - 3] + "..."


def build_changelog_context(
    sources: Iterable[ChangelogSource],
    max_chars: int = 1600,
) -> str:
    parts: List[str] = []
    for source in sources:
        try:
            raw = source.path.read_text(encoding="utf-8")
        except OSError:
            continue
        section = _extract_latest_section(raw)
        if not section:
            continue
        heading = _extract_section_heading(section)
        bullets = _extract_bullets(section, limit=4)
        snippet_lines = [f"[{source.slug}] {heading}"]
        for bullet in bullets:
            snippet_lines.append(f"- {bullet}")
        parts.append("\n".join(snippet_lines))

    if not parts:
        return ""

    combined = "\n\n".join(parts)
    return _truncate(combined, max_chars)


def select_changelog_source(
    sources: Iterable[ChangelogSource],
    project_slug: Optional[str],
) -> Optional[ChangelogSource]:
    if project_slug:
        normalized = project_slug.strip().lower()
        for source in sources:
            if source.slug == normalized:
                return source
    return next(iter(sources), None)


def build_changelog_tweet_local(
    source: ChangelogSource,
    max_chars: int,
) -> str:
    try:
        raw = source.path.read_text(encoding="utf-8")
    except OSError:
        return _truncate(f"Geno update: {source.name} shipped new changes.", max_chars)

    section = _extract_latest_section(raw)
    heading = _extract_section_heading(section) if section else f"{source.name} update"
    bullets = _extract_bullets(section, limit=3)

    prefix = f"Geno update on {source.name}: {heading}".strip()
    body = "; ".join(bullets)
    base = f"{prefix}. {body}" if body else prefix

    cta_link = source.links[0] if source.links else None
    cta_label = source.cta_label or "Details"
    cta = f" | {cta_label}: {cta_link}" if cta_link else ""

    if cta:
        available = max_chars - len(cta)
        if available < 10:
            return _truncate(prefix, max_chars)
        base = _truncate(base, available)
        return f"{base}{cta}"

    return _truncate(base, max_chars)
