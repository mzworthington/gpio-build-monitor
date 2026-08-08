#!/usr/bin/env bash
# Thin product-repo shim — runs the canonical bootstrap from edge-dns.
# Logic: https://github.com/mzworthington/edge-dns/blob/main/scripts/setup-cloudflare-hosting.sh
#
# Prefer BWS (no .env):
#   export BWS_ACCESS_TOKEN=... BWS_PROJECT_ID=...
#   # plus DOMAIN / PAGES_HOSTNAMES / PAGES_PROJECT_NAME / PULUMI_STACK (or .env)
#   bin/setup-cloudflare-hosting.sh
#
# Pin tooling: EDGE_DNS_REF=<sha> bin/setup-cloudflare-hosting.sh
set -euo pipefail

EDGE_DNS_REF="${EDGE_DNS_REF:-main}"
SCRIPT_URL="https://raw.githubusercontent.com/mzworthington/edge-dns/${EDGE_DNS_REF}/scripts/setup-cloudflare-hosting.sh"

export PRODUCT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PRODUCT_ROOT"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
curl -fsSL "$SCRIPT_URL" -o "${tmpdir}/setup-cloudflare-hosting.sh"
bash "${tmpdir}/setup-cloudflare-hosting.sh" "$@"
