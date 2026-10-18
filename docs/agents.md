# Agents (MCP)

CI status for agents, from the same StatusHub snapshot the status page, desk
lights, menu bar, and e-ink panel already follow. StatusHub polls GitHub
Actions and CircleCI. Agents call the hub.

Live server: `https://monitor.mzworthington.co.uk/mcp`

`/api/mcp` is the same server. The status page is public, and these tools
return that same glance. No login.

## Connect

Add a remote MCP server. This repo's [`.mcp.json`](../.mcp.json) already
registers it as `build-monitor`.

```json
{
  "mcpServers": {
    "build-monitor": {
      "url": "https://monitor.mzworthington.co.uk/mcp"
    }
  }
}
```

Cursor, Claude, and any client that speaks Streamable HTTP MCP can use that
URL. The Worker answers each call from the current snapshot. There is no MCP
session to keep open.

## Tools

Each result includes `retry_after_seconds`. Wait that long before calling
again. It matches the hub's own cadence.

| Tool | Arguments | Returns |
|------|-----------|---------|
| `get_build_status` | none | Aggregate status, whether anything is running, `last_checked_at`, and one row per repo (status, workflow count, open PRs, security count) |
| `get_repo_status` | `repo` as `owner/name` | Workflows with status and URL, open pull requests, security findings |
| `list_attention` | none | Failed workflows, in-progress workflows, open pull requests, and security findings, each with a URL |

An unknown `repo` returns an error and the list of repos this monitor watches.

## HTTP glance

`GET /api/status?view=agent` is the same document as `get_build_status`.
Add `&repo=owner/name` for one repo.

```shell
curl -sS 'https://monitor.mzworthington.co.uk/api/status?view=agent'
```

`Retry-After` on that response is the same wait as `retry_after_seconds`.

Local Python hub (`bin/serve`):

```shell
curl -sS 'http://127.0.0.1:8080/api/status?view=agent'
```

The MCP server runs on the Worker. For a local Worker:

```shell
cd monitor/device/web && pnpm install && pnpm dev:worker
```

Point the client at the URL Wrangler prints, path `/mcp`.

If `PYTHON_API_ORIGIN` is set, the tools read that origin's `/api/status`.
Production leaves it empty, so StatusHub is the hub.

## Scope

The tools return status, repo and workflow names, counts, and URLs. API
tokens, `MONITOR_CONFIG`, webhook secrets, `POST /api/refresh`, and push
subscriptions stay on the operator side of the Worker.
