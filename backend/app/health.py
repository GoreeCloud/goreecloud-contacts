from __future__ import annotations

import httpx


_CARDDAV_PROPFIND_BODY = """<?xml version="1.0" encoding="utf-8" ?>
<d:propfind xmlns:d="DAV:">
  <d:prop><d:current-user-principal /></d:prop>
</d:propfind>
"""


async def carddav_transport_ready(
    base_url: str,
    timeout_seconds: float,
) -> bool:
    """Check CardDAV transport/WebDAV availability without supplying user credentials.

    HTTP 401/403 is accepted because a private CardDAV server may correctly require
    authentication before answering PROPFIND. Successful WebDAV/redirect responses are
    also accepted. Transport/TLS failures, 404/405 endpoint mismatch, and 5xx responses
    are treated as not ready.
    """

    target = base_url.strip()
    if not target:
        return False

    timeout = max(0.5, min(timeout_seconds, 5.0))
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            response = await client.request(
                "PROPFIND",
                target,
                headers={
                    "Depth": "0",
                    "Content-Type": "application/xml; charset=utf-8",
                },
                content=_CARDDAV_PROPFIND_BODY,
            )
    except httpx.HTTPError:
        return False

    if response.status_code in {401, 403}:
        return True
    return 200 <= response.status_code < 400
