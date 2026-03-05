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


