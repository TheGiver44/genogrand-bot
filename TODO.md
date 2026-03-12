## TODO / Next Steps

These are the remaining high-level items for this bot.

### AI and Content

- **Enable AI-powered tweets in production**
  - [ ] Create a Google Gemini API key from AI Studio.
  - [ ] Add `GEMINI_API_KEY` to Railway service environment.
  - [ ] Monitor a few live tweets to ensure the AI respects:
    - No links or URLs.
    - No shill / memecoin / ticker language.
    - At most one emotional hashtag.
  - [ ] Adjust prompts or add more guardrails if anything slips through.

- **Future content upgrades**
  - [ ] Add multiple “modes” of tweets (deep rant, short punchy take, quiet reflective line) and let the scheduler rotate between them.
  - [ ] Use `projects-list.md` more directly to occasionally reference themes (not links) from your past work.

### Secrets and Keys

- **Regenerate Twitter/X API keys (post-leak hardening)**
  - [ ] In X Developer Portal, for the paid app:
    - [ ] Regenerate Consumer Key and Secret.
    - [ ] Regenerate Access Token and Access Token Secret (Read + write).
  - [ ] Update:
    - [ ] Local shell environment variables.
    - [ ] Railway environment variables.
  - [ ] Verify:
    - [ ] `python simple_x_test.py` works locally.
    - [ ] `python -m src.crypto_social_bot` posts a single tweet successfully.

### Bot Behavior & UX

- **Auto-reply / conversational agent (future)**
  - [ ] Design how replies should behave (who to reply to, what tone, what triggers).
  - [ ] Implement a reply engine that:
    - [ ] Reads recent mentions.
    - [ ] Uses the same personality engine (and AI, if enabled) for responses.
    - [ ] Respects strict rate limits and avoids spammy behavior.
  - [ ] Add tests around reply selection, content rules, and rate limiting.

- **Scheduling and observability**
  - [ ] Add lightweight logging/metrics for:
    - [ ] When a tweet is attempted.
    - [ ] Whether it succeeded or failed (with reason).
  - [ ] Optionally expose a simple “health check” endpoint or log message Railway can use.

### Maintenance

- **Dependencies and runtime**
  - [ ] Upgrade Python to 3.10+ when convenient (Google libs warn about 3.9 EOL).
  - [ ] Migrate from `google-generativeai` to `google.genai` when you’re ready, per the deprecation warning.
  - [ ] Keep `CHANGELOG.md` and this `TODO.md` updated as you iterate.



### NEW 
add support for GROQ_API_KEY, OPENAI_API_KEY, AND GEMINI_API_KEY I've added them to my .env
