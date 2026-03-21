## GenoGrand Twitter Agent

This repo contains a fully automated, rate-limited Twitter/X bot that posts in your voice using personality documents and (optionally) an AI model. It is designed to run 24/7 on platforms like Railway with very low tweet frequency and strict safety rules.

### Features

- **Personality-aware tweets** driven by `personality/howiwrite.txt` and `personality/story.txt`.
- **Optional AI generation** via GROQ (primary) or Google Gemini (fallback), with personality + `data/` context and prompt engineering for insightful, engaging tweets.
- **Local combinatorial generator** producing unique, human-feeling tweets even without AI.
- **File-based tweet tracker** (`.tweet_tracker.json`) to:
  - Remember last tweet time across restarts.
  - Avoid repeating the last tweet text.
- **Rate limiting** (verified account):
  - At most 1–2 tweets per day (12-hour minimum between tweets).
  - Scheduler runs every 12 hours (720 minutes) between attempts.
- **Automated tests** (16 total) verifying:
  - Uniqueness and content rules for tweets.
  - Tracker behavior.
  - Rate limiter spacing.
  - Posting orchestration (one API call per tweet).

### Quick Start (Local)

1. **Install dependencies**

```bash
pip install -r requirements.txt
```

2. **Set Twitter/X credentials in your shell**

```bash
export TWITTER_API_KEY="..."
export TWITTER_API_SECRET="..."
export TWITTER_ACCESS_TOKEN="..."
export TWITTER_ACCESS_TOKEN_SECRET="..."
```

3. **(Optional) Enable AI-powered tweets**

```bash
export GEMINI_API_KEY="your_google_gemini_key"
```

Without `GEMINI_API_KEY`, the bot uses the local generator only.

4. **Run tests**

```bash
python -m pytest -v
```

5. **Post a single tweet manually**

```bash
python -m src.crypto_social_bot
```

6. **Run the scheduler (local or production)**

```bash
python -m src.scheduler
```

This will:

- Generate a tweet in your voice (AI + fallback).
- Wait according to the rate limiter (30 min min spacing).
- Sleep 35 minutes between iterations.

### Deployment (Railway Summary)

- Deploy from the GitHub repo.
- Set environment variables in the Railway service:
  - `TWITTER_API_KEY`
  - `TWITTER_API_SECRET`
  - `TWITTER_ACCESS_TOKEN`
  - `TWITTER_ACCESS_TOKEN_SECRET`
  - (Optional) `GEMINI_API_KEY`
- Set start command to:

```bash
python -m src.scheduler
```

#### Python version pinning

A `.python-version` file pins the build to **Python 3.12**. This prevents Railpack/mise from auto-selecting Python 3.13's freethreaded build (`freethreaded-install_only_stripped`), which ships without a `lib/` directory and causes the build to fail with:

```
mise ERROR Failed to install core:python@3.13.x: Python installation is missing a `lib` directory
```

Do not remove `.python-version` or bump it to `3.13` until the upstream freethreaded packaging issue is resolved in mise.

### Safety & Constraints

- Tweets:
  - Max 240 characters (to be safe for non-verified accounts).
  - No links or URLs.
  - No token tickers, memecoin shill, or crypto hashtags (`#crypto`, `#web3`, etc.).
  - At most one emotional hashtag (e.g. `#truth`, `#realtalk`) when used.
- Rate limiting:
  - `RateLimiter` enforces spacing; tests ensure the behavior.
  - `.tweet_tracker.json` persists timing across restarts.

### Project Structure

- `src/base_bot.py` — Low-level Tweepy wrapper for posting and media (no tweet history).
- `src/personality_engine.py` — Personality-aware tweet generator (AI + local).
- `src/crypto_social_bot.py` — High-level coordinator (rate limiting + tracker).
- `src/tweet_tracker.py` — File-based tracking of last tweet time/text.
- `src/scheduler.py` — Infinite loop scheduler for production.
- `personality/` — Your personal docs used as style/story context.
- `tests/` — Automated test suite.
- `CHANGELOG.md` — Required per your rules, updated on each change set.
- `SECRETS_ROTATION_PLAN.md` — Plan for rotating leaked Twitter/X keys.

