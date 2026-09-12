#!/usr/bin/env python3

from urllib.parse import urljoin, urlparse, urlunparse


def status_http_url(origin: str) -> str:
    return urljoin(origin.rstrip("/") + "/", "api/status")


def status_ws_url(origin: str) -> str:
    parsed = urlparse(origin)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse(parsed._replace(scheme=scheme, path="/api/ws", query="", fragment=""))
