#!/usr/bin/env bash
set -euo pipefail

# A deliberately slow, safe auto-committer:
# - Commits ONE file per loop (plus CHANGELOG.md when needed)
# - Avoids common secret/env file patterns
# - Writes a CHANGELOG entry for each commit (per project rules)
#
# Usage:
#   ./auto-commit.sh                # infinite loop
#   ./auto-commit.sh --once         # do at most one commit
#   ./auto-commit.sh --dry-run      # print what would happen
#
# Tuning (seconds):
#   MIN_DELAY=600 MAX_DELAY=3600 ./auto-commit.sh

MIN_DELAY="${MIN_DELAY:-900}"   # 15 minutes
MAX_DELAY="${MAX_DELAY:-3600}"  # 60 minutes

DRY_RUN=false
ONCE=false
if (( $# > 0 )); then
  for arg in "$@"; do
    case "$arg" in
      --dry-run) DRY_RUN=true ;;
      --once) ONCE=true ;;
      *)
        echo "Unknown arg: $arg" >&2
        exit 2
        ;;
    esac
  done
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git not found on PATH" >&2
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not a git repository (run from repo root)." >&2
  exit 1
fi

if (( MIN_DELAY < 5 )) || (( MAX_DELAY < MIN_DELAY )); then
  echo "Invalid MIN_DELAY/MAX_DELAY: MIN_DELAY=$MIN_DELAY MAX_DELAY=$MAX_DELAY" >&2
  exit 2
fi

is_blocked_path() {
  local p="$1"
  case "$p" in
    *.env|*.env.*|.env|.env.*) return 0 ;;
    *secret*|*SECRET*|*token*|*TOKEN*|*key*|*KEY*) return 0 ;;
    *credentials*|*CREDENTIALS*|*pem|*p12) return 0 ;;
  esac
  return 1
}

pick_next_path() {
  # Prefer tracked modifications first; then untracked files.
  local p

  while IFS= read -r p; do
    [[ -z "$p" ]] && continue
    [[ "$p" == "CHANGELOG.md" ]] && continue
    if is_blocked_path "$p"; then
      continue
    fi
    echo "$p"
    return 0
  done < <(git ls-files -m)

  while IFS= read -r p; do
    [[ -z "$p" ]] && continue
    [[ "$p" == "CHANGELOG.md" ]] && continue
    if is_blocked_path "$p"; then
      continue
    fi
    echo "$p"
    return 0
  done < <(git ls-files -o --exclude-standard)

  return 1
}

append_changelog_entry() {
  local changed_path="$1"
  local id ts
  ts="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
  id="AUTO-COMMIT-$(date -u '+%Y%m%d-%H%M%S')-$RANDOM"

  python3 - "$ts" "$id" "$changed_path" <<'PY'
import sys

ts, entry_id, changed_path = sys.argv[1], sys.argv[2], sys.argv[3]
path = "CHANGELOG.md"

entry = (
    "### Technical\n"
    f"- **ID: {entry_id}** - {ts}\n"
    f"  - Auto-commit step for `{changed_path}`\n"
    f"  - Files: `{changed_path}`, `CHANGELOG.md`\n"
    "  - Validation: Not run (auto-commit)\n\n"
)

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

marker = "\n---\n\n## Format Notes\n"
idx = content.rfind(marker)
if idx == -1:
    content = content.rstrip() + "\n\n" + entry
else:
    content = content[:idx].rstrip() + "\n\n" + entry + content[idx:]

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
PY
}

commit_one_step() {
  local p
  if ! p="$(pick_next_path)"; then
    echo "No eligible changes to commit."
    return 1
  fi

  echo "Next file: $p"

  if "$DRY_RUN"; then
    echo "[dry-run] would: append changelog, git add \"$p\" CHANGELOG.md, git commit"
    return 0
  fi

  append_changelog_entry "$p"

  git add -- "$p" CHANGELOG.md

  if git diff --cached --quiet; then
    echo "Nothing staged after add; skipping."
    return 0
  fi

  git commit -m "chore: step commit for $p"
  echo "Committed: $p"
  return 0
}

while true; do
  commit_one_step || true

  if "$ONCE"; then
    exit 0
  fi

  sleep_time=$((RANDOM % (MAX_DELAY - MIN_DELAY + 1) + MIN_DELAY))
  echo "Sleeping for $sleep_time seconds..."
  sleep "$sleep_time"
done