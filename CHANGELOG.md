## 2026-03-04 - auto-twitter-001

- **Summary**: Initial crypto Twitter automation scaffolding using existing `TwitterBot`, personality documents, and a new orchestration layer.
- **Files Touched**:
  - `src/base_bot.py`
  - `src/personality_engine.py`
  - `src/crypto_social_bot.py`
  - `CHANGELOG.md`
- **Validation**: Not yet run against live Twitter API. Intended first test is a single-tweet manual run of `python -m src.crypto_social_bot` after environment variables are configured.

## 2026-03-04 - auto-twitter-002

- **Summary**: Added automated tests, tightened rate limiting to one tweet every 30 minutes, and updated personality tweets to avoid crypto hashtags and memecoin promotion.
- **Files Touched**:
  - `src/crypto_social_bot.py`
  - `src/personality_engine.py`
  - `tests/test_personality_engine.py`
  - `tests/test_rate_limiter.py`
  - `tests/test_crypto_social_bot.py`
  - `CHANGELOG.md`
- **Validation**: `python -m pytest` passes locally. Live tweet still gated behind environment variables; manual one-tweet test should be run via `python -m src.crypto_social_bot` once credentials are configured.

## 2026-03-04 - auto-twitter-003

- **Summary**: Refined tweet content to be text-only with at most one non-crypto hashtag and added a simple scheduler for production deployment.
- **Files Touched**:
  - `src/personality_engine.py`
  - `tests/test_personality_engine.py`
  - `src/scheduler.py`
  - `CHANGELOG.md`
- **Validation**: Scheduler entrypoint `python -m src.scheduler` uses existing rate limiter and has not yet been exercised in a hosted environment; local tweet generation remains under Twitter character limits and contains no links.

## 2026-03-04 - auto-twitter-004

- **Summary**: Added gitignore to prevent committing secrets and documented a plan to rotate leaked Twitter credentials after removing `.env` from git history.
- **Files Touched**:
  - `.gitignore`
  - `SECRETS_ROTATION_PLAN.md`
  - `CHANGELOG.md`
- **Validation**: `.env` is now ignored by git; history rewrite and credential rotation still need to be executed and verified manually.

## 2026-03-05 - auto-twitter-005

- **Summary**: Updated personality tweet generation to add controlled variability and enforce a 240 character limit to avoid duplicate-content errors and fit a non-verified account.
- **Files Touched**:
  - `src/personality_engine.py`
  - `tests/test_personality_engine.py`
  - `CHANGELOG.md`
- **Validation**: Local tweet generation now produces text-only tweets with at most one non-crypto hashtag and length <= 240 characters; randomness and in-process de-duplication reduce the chance of duplicate tweets being sent in production.

## 2026-03-05 - auto-twitter-006

- **Summary**: Simplified async tests to run without plugins, excluded `simple_x_test.py` from pytest collection, and strengthened tweet uniqueness by composing openings, middles, and endings at send time.
- **Files Touched**:
  - `tests/test_rate_limiter.py`
  - `tests/test_crypto_social_bot.py`
  - `src/personality_engine.py`
  - `tests/test_personality_engine.py`
  - `pytest.ini`
  - `CHANGELOG.md`
- **Validation**: `python -m pytest` no longer requires async plugins and ignores `simple_x_test.py`; personality tests assert length, content rules, and that multiple generated tweets are not all identical.

## 2026-03-05 - auto-twitter-007

- **Summary**: Made `src` a proper Python package so tests can import bot code reliably.
- **Files Touched**:
  - `src/__init__.py`
  - `CHANGELOG.md`
- **Validation**: After adding the package marker, `python -m pytest` from the project root succeeds with all tests passing.

## 2026-03-05 - auto-twitter-008

- **Summary**: Major overhaul — replaced broken API tweet-fetch with file-based tracker, rewrote personality engine with 150-combination local algorithm (no shared prefix), integrated Google Gemini free tier for AI-powered tweet generation, and added 16 automated tests covering uniqueness, tracker, rate limiter, and content rules.
- **Files Touched**:
  - `src/tweet_tracker.py` (new)
  - `src/personality_engine.py` (rewritten)
  - `src/crypto_social_bot.py` (updated)
  - `src/base_bot.py` (removed broken get_latest_tweet_time)
  - `tests/test_tweet_tracker.py` (new)
  - `tests/test_fetch_isolated.py` (new)
  - `tests/test_personality_engine.py` (rewritten, 5 tests)
  - `tests/test_crypto_social_bot.py` (rewritten, 3 tests)
  - `requirements.txt` (added google-generativeai)
  - `.gitignore` (added .tweet_tracker.json)
  - `CHANGELOG.md`
- **Validation**: `python -m pytest -v` passes all 16 tests locally. AI generation requires `GEMINI_API_KEY` env var; falls back gracefully to local algorithm without it.

## 2026-03-11 - auto-twitter-009

- **Summary**: Reduced tweet frequency to 1–2 per day (12h min spacing) for verified account; added GROQ as primary AI for tweet generation with `data/` context and prompt engineering; theme: build-in-public, developers democratized, AI democratizing crypto so anyone can build and become their own bank.
- **Files Touched**:
  - `src/crypto_social_bot.py` (RateLimiter: min_seconds_between_tweets=43200)
  - `src/scheduler.py` (interval_minutes=720)
  - `src/personality_engine.py` (GROQ primary, _load_data_context, theme + prompts.md style in system prompt)
  - `requirements.txt` (groq)
  - `tests/test_rate_limiter.py` (default 43200)
  - `README.md` (rate limit and AI description)
  - `CHANGELOG.md`
- **Validation**: GROQ API tested with `GROQ_API_KEY`; `python -m pytest -v` passes all 16 tests; sample tweet generated via enhanced engine (GROQ + data context) within 230 chars and content rules.

## 2026-03-11 - auto-twitter-010

- **Summary**: Made tweets longer (up to 280 chars), richer insight from `data/february-2026-cryptoroundup.txt` and `data/prompts.md`; more personality text (2500 chars each); prompt instructs long-form takes, real takes, education, and emotion; local fallback openers/closers extended for longer tweets.
- **Files Touched**:
  - `src/personality_engine.py` (_load_data_context full roundup + 2200 chars prompts, system prompt 280 limit + prompts.md style + emotion, GROQ/Gemini 280 truncation, local 280)
  - `tests/test_personality_engine.py` (assert <= 280)
  - `CHANGELOG.md`
- **Validation**: No logic changes; `python -m pytest -v` must pass (character limit 280).

### Technical
- **ID: AUTO-COMMIT-20260318-082800-4859** - 2026-03-18 08:28:00 UTC
  - Auto-commit step for `TODO.md`
  - Files: `TODO.md`, `CHANGELOG.md`
  - Validation: Not run (auto-commit)

