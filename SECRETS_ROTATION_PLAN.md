## Twitter / X API Secrets Rotation Plan

- **Problem**: `.env` with live Twitter / X credentials was committed and pushed to GitHub.
- **Immediate Mitigation**:
  - `.gitignore` now excludes `.env` so future commits will not include it.
  - Git history will be rewritten to remove `.env` from all commits, followed by a force-push to GitHub.
- **Required Rotation Steps (to be done soon)**:
  1. In the X developer dashboard, for the paid app used by this bot:
     - Regenerate the **Consumer Key** and **Consumer Secret**.
     - Regenerate the **Access Token** and **Access Token Secret** with *Read and write* permissions.
  2. Update the new values **locally only** in:
     - The shell environment when running the bot.
     - The Railway project variables for production.
  3. Never commit `.env` or any raw secrets again; configuration must flow through environment variables in local shells and deployment platforms.
- **Notes**:
  - Old leaked keys should be treated as compromised even after history rewrite.
  - After rotation, verify locally with `python simple_x_test.py` and then `python -m src.crypto_social_bot`.

