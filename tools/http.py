from __future__ import annotations

import certifi
import requests


def run_http_request(url: str) -> str:
    try:
        r = requests.get(url, timeout=10, verify=certifi.where())
        return r.text[:2000]
    except Exception as e:
        return f"ERROR: {str(e)}"
