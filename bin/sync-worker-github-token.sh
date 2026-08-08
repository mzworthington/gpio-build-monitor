#!/usr/bin/env bash
# Fetch GITHUB_TOKEN from Bitwarden Secrets Manager and upload it to the Worker.
#
# Prerequisites:
#   - bws on PATH, BWS_ACCESS_TOKEN set
#   - BWS_PROJECT_ID set (or pass --project-id)
#
# Usage:
#   export BWS_ACCESS_TOKEN=... BWS_PROJECT_ID=...
#   bin/sync-worker-github-token.sh
#   bin/sync-worker-github-token.sh --project-id <uuid>
#   bin/sync-worker-github-token.sh --dry-run
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SECRET_KEY="${SECRET_KEY:-GITHUB_TOKEN}"
WORKER_NAME="${WORKER_NAME:-gpio-build-monitor}"
DRY_RUN=0
PROJECT_ID="${BWS_PROJECT_ID:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --project-id)
      PROJECT_ID="${2:-}"
      [[ -n "$PROJECT_ID" ]] || { echo "error: --project-id needs a value" >&2; exit 1; }
      shift 2
      ;;
    -h|--help)
      sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

command -v bws >/dev/null || { echo "error: bws not on PATH" >&2; exit 1; }
command -v pnpm >/dev/null || { echo "error: pnpm not on PATH" >&2; exit 1; }
[[ -n "${BWS_ACCESS_TOKEN:-}" ]] || { echo "error: set BWS_ACCESS_TOKEN" >&2; exit 1; }
[[ -n "$PROJECT_ID" ]] || {
  echo "error: set BWS_PROJECT_ID or pass --project-id" >&2
  echo "hint: bws project list" >&2
  exit 1
}

echo "→ Reading ${SECRET_KEY} from BWS project ${PROJECT_ID}"
export SECRET_KEY
TOKEN="$(
  bws secret list "$PROJECT_ID" -o json \
    | python3 -c '
import json, os, sys
key = os.environ["SECRET_KEY"]
secrets = json.load(sys.stdin)
matches = [s for s in secrets if s.get("key") == key]
if not matches:
    sys.stderr.write(f"error: no secret named {key} in project\n")
    sys.exit(2)
value = matches[0].get("value") or ""
if not value.strip():
    sys.stderr.write(f"error: {key} is empty in BWS\n")
    sys.exit(3)
sys.stdout.write(value)
'
)"

echo "✓ Got ${SECRET_KEY} (length ${#TOKEN})"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "(dry-run - not uploading to Cloudflare)"
  exit 0
fi

echo "→ Uploading to Worker ${WORKER_NAME}"
printf '%s' "$TOKEN" | (cd worker && pnpm exec wrangler secret put GITHUB_TOKEN --name "$WORKER_NAME")
echo "✓ GITHUB_TOKEN set on Worker ${WORKER_NAME}"
echo "Reload https://monitor.mzworthington.co.uk"
