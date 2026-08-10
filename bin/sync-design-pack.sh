#!/usr/bin/env bash
# Rasterize design-pack SVGs into monitor/web (requires librsvg: brew install librsvg).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DP="$ROOT/design-pack"
WEB="$ROOT/monitor/web"

command -v rsvg-convert >/dev/null || {
  echo "✗ rsvg-convert not found. Install with: brew install librsvg" >&2
  exit 1
}

mkdir -p "$WEB"

cp "$DP/favicon.svg" "$WEB/favicon.svg"
cp "$DP/mark.svg" "$WEB/logo.svg"

rsvg-convert -w 32 -h 32 "$DP/favicon.svg" -o "$WEB/favicon-32.png"
rsvg-convert -w 180 -h 180 "$DP/mark-square.svg" -o "$WEB/apple-touch-icon.png"
rsvg-convert -w 512 -h 512 "$DP/mark.svg" -o "$WEB/logo.png"
rsvg-convert -w 192 -h 192 "$DP/mark-square.svg" -o "$WEB/icon-192.png"
rsvg-convert -w 512 -h 512 "$DP/mark-square.svg" -o "$WEB/icon-512.png"
rsvg-convert -w 1200 -h 630 "$DP/social-share.svg" -o "$WEB/social-share.png"

# Preview copies beside sources
rsvg-convert -w 64 -h 64 "$DP/favicon.svg" -o "$DP/favicon.png"
rsvg-convert -w 512 -h 512 "$DP/mark.svg" -o "$DP/mark.png"
rsvg-convert -w 512 -h 512 "$DP/mark-square.svg" -o "$DP/mark-square.png"
rsvg-convert -w 1200 -h 630 "$DP/social-share.svg" -o "$DP/social-share.png"

echo "✓ Synced design-pack → monitor/web"
