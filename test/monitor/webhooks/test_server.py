#!/usr/bin/env python3

import hashlib
import hmac

import pytest
from aiohttp.test_utils import TestClient, TestServer

from monitor.service.refresh_signal import RefreshSignal
from monitor.webhooks.server import create_app


def _github_signature(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _circleci_signature(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"v1={digest}"


@pytest.fixture
async def webhook_client():
    signal = RefreshSignal()
    app = create_app(
        signal,
        {"github": "gh-secret", "circleci": "cci-secret"},
    )
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    yield client, signal
    await client.close()


@pytest.mark.asyncio
async def test_health(webhook_client):
    client, _ = webhook_client
    response = await client.get("/health")
    assert response.status == 200
    assert await response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_github_workflow_run_notifies(webhook_client):
    client, signal = webhook_client
    body = b'{"action":"completed"}'
    response = await client.post(
        "/webhooks/github",
        data=body,
        headers={
            "X-Hub-Signature-256": _github_signature(body, "gh-secret"),
            "X-GitHub-Event": "workflow_run",
            "Content-Type": "application/json",
        },
    )
    assert response.status == 200
    payload = await response.json()
    assert payload["action"] == "refresh"
    assert await signal.wait(timeout=0.01) is True


@pytest.mark.asyncio
async def test_github_ping_acks_without_refresh(webhook_client):
    client, signal = webhook_client
    body = b'{"zen":"keep it logically awesome"}'
    response = await client.post(
        "/webhooks/github",
        data=body,
        headers={
            "X-Hub-Signature-256": _github_signature(body, "gh-secret"),
            "X-GitHub-Event": "ping",
            "Content-Type": "application/json",
        },
    )
    assert response.status == 200
    assert (await response.json())["action"] == "ack"
    assert await signal.wait(timeout=0.01) is False


@pytest.mark.asyncio
async def test_github_rejects_bad_signature(webhook_client):
    client, signal = webhook_client
    response = await client.post(
        "/webhooks/github",
        data=b"{}",
        headers={
            "X-Hub-Signature-256": "sha256=deadbeef",
            "X-GitHub-Event": "workflow_run",
        },
    )
    assert response.status == 403
    assert await signal.wait(timeout=0.01) is False


@pytest.mark.asyncio
async def test_circleci_workflow_completed_notifies(webhook_client):
    client, signal = webhook_client
    body = b'{"type":"workflow-completed"}'
    response = await client.post(
        "/webhooks/circleci",
        data=body,
        headers={
            "circleci-signature": _circleci_signature(body, "cci-secret"),
            "circleci-event-type": "workflow-completed",
            "Content-Type": "application/json",
        },
    )
    assert response.status == 200
    assert (await response.json())["action"] == "refresh"
    assert await signal.wait(timeout=0.01) is True


@pytest.mark.asyncio
async def test_missing_secret_returns_503():
    signal = RefreshSignal()
    app = create_app(signal, {"github": None, "circleci": None})
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    try:
        response = await client.post("/webhooks/github", data=b"{}")
        assert response.status == 503
    finally:
        await client.close()
