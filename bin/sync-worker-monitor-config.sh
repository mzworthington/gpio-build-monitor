#!/usr/bin/env bash
# Build MONITOR_CONFIG JSON from monitor/integrations.yaml and upload to the Worker.
# Usage (from repo root):
#   bin/sync-worker-monitor-config.sh
#   bin/sync-worker-monitor-config.sh --dry-run
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

CONF="${CONF_FILE:-monitor/integrations.yaml}"
[[ -f "$CONF" ]] || {
  echo "Missing $CONF — copy monitor/integrations.example.yaml" >&2
  exit 1
}

command -v python3 >/dev/null || {
  echo "Missing python3" >&2
  exit 1
}

PYTHON=python3
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

OUT="$("$PYTHON" - "$CONF" <<'PY'
import json, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML required (pip install pyyaml / use project .venv)\n")
    sys.exit(1)

path = Path(sys.argv[1])
raw = yaml.safe_load(path.read_text()) or {}
integrations = []
for item in raw.get("integrations") or []:
    if not isinstance(item, dict):
        continue
    kind = str(item.get("type", "")).upper()
    username = str(item.get("username") or "").strip()
    repo = str(item.get("repo") or "").strip()
    if not kind or not username or not repo:
        continue
    # Skip template placeholders
    if username.startswith("your-") or repo.startswith("your-"):
        continue
    entry = {"type": kind, "username": username, "repo": repo}
    if kind == "GITHUB":
        branch = item.get("branch")
        if branch:
            entry["branch"] = branch
        patterns = item.get("excluded_workflow_patterns") or []
        if patterns:
            entry["excluded_workflow_patterns"] = list(patterns)
        excluded = item.get("excluded_workflows") or []
        if excluded:
            entry["excluded_workflows"] = list(excluded)
    elif kind == "CIRCLECI":
        excluded = item.get("excluded_workflows") or []
        if excluded:
            entry["excluded_workflows"] = list(excluded)
    else:
        continue
    integrations.append(entry)

poll = raw.get("poll_in_seconds", 30)
try:
    poll = int(poll)
except (TypeError, ValueError):
    poll = 30
if poll <= 0:
    poll = 30

print(json.dumps({"poll_in_seconds": poll, "integrations": integrations}, indent=2))
PY
)"

echo "$OUT"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "(dry-run — not uploading)" >&2
  exit 0
fi

if [[ "$(echo "$OUT" | "$PYTHON" -c 'import json,sys; print(len(json.load(sys.stdin).get("integrations") or []))')" == "0" ]]; then
  echo "No integrations to upload (empty list is OK — Worker will show Idle)." >&2
fi

printf '%s' "$OUT" | (cd worker && pnpm exec wrangler secret put MONITOR_CONFIG --name gpio-build-monitor)
echo "✓ MONITOR_CONFIG updated on Worker gpio-build-monitor"
