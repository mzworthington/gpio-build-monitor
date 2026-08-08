#!/usr/bin/env python3

import logging
from typing import TypedDict

from aiohttp import web

from monitor.service.refresh_signal import RefreshSignal
from monitor.webhooks.events import RefreshDecision, decide_circleci, decide_github
from monitor.webhooks.signatures import (
    verify_circleci_signature,
    verify_github_signature,
)


class WebhookSecrets(TypedDict):
    github: str | None
    circleci: str | None


REFRESH_SIGNAL_KEY = web.AppKey("refresh_signal", RefreshSignal)
WEBHOOK_SECRETS_KEY = web.AppKey("webhook_secrets", WebhookSecrets)


def create_app(signal: RefreshSignal, secrets: WebhookSecrets) -> web.Application:
    """Build the webhook HTTP app. Does not start listening."""
    app = web.Application()
    app[REFRESH_SIGNAL_KEY] = signal
    app[WEBHOOK_SECRETS_KEY] = secrets
    app.router.add_get("/health", _health)
    app.router.add_post("/webhooks/github", _github_webhook)
    app.router.add_post("/webhooks/circleci", _circleci_webhook)
    return app


async def start_server(
    signal: RefreshSignal,
    secrets: WebhookSecrets,
    host: str,
    port: int,
) -> web.AppRunner:
    app = create_app(signal, secrets)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()
    logging.info("Webhook server listening on http://%s:%s", host, port)
    return runner


async def _health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def _github_webhook(request: web.Request) -> web.Response:
    secrets = request.app[WEBHOOK_SECRETS_KEY]
    secret = secrets.get("github")
    if not secret:
        return web.Response(status=503, text="GitHub webhooks are not configured")

    body = await request.read()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_github_signature(body, secret, signature):
        logging.warning("Rejected GitHub webhook: invalid signature")
        return web.Response(status=403, text="invalid signature")

    event_name = request.headers.get("X-GitHub-Event")
    decision = decide_github(event_name)
    return _respond(request, decision, f"github:{event_name or 'unknown'}")


async def _circleci_webhook(request: web.Request) -> web.Response:
    secrets = request.app[WEBHOOK_SECRETS_KEY]
    secret = secrets.get("circleci")
    if not secret:
        return web.Response(status=503, text="CircleCI webhooks are not configured")

    body = await request.read()
    signature = request.headers.get("circleci-signature")
    if not verify_circleci_signature(body, secret, signature):
        logging.warning("Rejected CircleCI webhook: invalid signature")
        return web.Response(status=403, text="invalid signature")

    event_name = request.headers.get("circleci-event-type")
    decision = decide_circleci(event_name)
    return _respond(request, decision, f"circleci:{event_name or 'unknown'}")


def _respond(
    request: web.Request,
    decision: RefreshDecision,
    reason: str,
) -> web.Response:
    if decision is RefreshDecision.REFRESH:
        signal = request.app[REFRESH_SIGNAL_KEY]
        signal.notify(reason)
        return web.json_response({"status": "accepted", "action": "refresh"})
    if decision is RefreshDecision.ACK:
        return web.json_response({"status": "accepted", "action": "ack"})
    logging.debug("Ignoring webhook event %s", reason)
    return web.json_response({"status": "ignored", "action": "none"})
