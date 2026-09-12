#!/usr/bin/env python3

from monitor.api_urls import status_http_url, status_ws_url


def test_status_urls_use_api_prefix():
    origin = "https://monitor.mzworthington.co.uk"
    assert status_ws_url(origin) == "wss://monitor.mzworthington.co.uk/api/ws"
    assert status_http_url(origin) == "https://monitor.mzworthington.co.uk/api/status"
