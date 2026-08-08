#!/usr/bin/env python3

import logging
from collections.abc import Sequence
from functools import partial

from aiohttp import web

from monitor.service.refresh_signal import RefreshSignal
from monitor.webhooks.constants import RefreshDecision, WebhookProvider, WebhookSecrets
from monitor.webhooks.providers import get_all

REFRESH_SIGNAL_KEY = web.AppKey("refresh_signal", RefreshSignal)
WEBHOOK_SECRETS_KEY = web.AppKey("webhook_secrets", WebhookSecrets)


def create_app(
    signal: RefreshSignal,
    secrets: WebhookSecrets,
    providers: Sequence[WebhookProvider] | None = None,
) -> web.Application:
    """Build the webhook HTTP app. Does not start listening."""
    app = web.Application()
    app[REFRESH_SIGNAL_KEY] = signal
    app[WEBHOOK_SECRETS_KEY] = secrets
    app.router.add_get("/health", _health)
    for provider in providers if providers is not None else get_all():
        app.router.add_post(provider.path, partial(_webhook, provider=provider))
    return app


async def start_server(
    signal: RefreshSignal,
    secrets: WebhookSecrets,
    host: str,
    port: int,
    providers: Sequence[WebhookProvider] | None = None,
) -> web.AppRunner:
    app = create_app(signal, secrets, providers=providers)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()
    logging.info("Webhook server listening on http://%s:%s", host, port)
    return runner


async def _health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def _webhook(request: web.Request, *, provider: WebhookProvider) -> web.Response:
    secrets = request.app[WEBHOOK_SECRETS_KEY]
    secret = secrets.get(provider.name)
    if not secret:
        return web.Response(
            status=503,
            text=f"{provider.display_name} webhooks are not configured",
        )

    body = await request.read()
    if not provider.verify_signature(body, secret, provider.signature_value(request)):
        logging.warning("Rejected %s webhook: invalid signature", provider.display_name)
        return web.Response(status=403, text="invalid signature")

    event_name = provider.event_name(request)
    decision = provider.decide(event_name)
    return _respond(request, decision, f"{provider.name}:{event_name or 'unknown'}")


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
