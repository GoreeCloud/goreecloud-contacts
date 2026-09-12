"""Privacy controls for normal application-server access logging.

CardDAV resource hrefs and ETags are currently carried in a small number of API query
parameters. Uvicorn's normal access log includes the request target, so those values would be
recorded unless the query component is removed before formatting.

This module deliberately changes only the access-log representation. It does not mutate the
ASGI request, disable operational status logging, or claim control over reverse-proxy logs.
Caddy and any future runtime logging layer remain separate production acceptance gates.
"""

from __future__ import annotations

import logging
from typing import Any


UVICORN_ACCESS_LOGGER = "uvicorn.access"


class QueryStringRedactionFilter(logging.Filter):
    """Remove the query component from Uvicorn's formatted request-target argument."""

    def filter(self, record: logging.LogRecord) -> bool:
        args: Any = record.args
        if not isinstance(args, tuple) or len(args) < 3:
            return True

        request_target = args[2]
        if not isinstance(request_target, str) or "?" not in request_target:
            return True

        sanitized = list(args)
        sanitized[2] = request_target.partition("?")[0]
        record.args = tuple(sanitized)
        return True


def configure_access_log_privacy() -> None:
    """Install the Uvicorn query-string filter once for the current process."""

    logger = logging.getLogger(UVICORN_ACCESS_LOGGER)
    if any(isinstance(item, QueryStringRedactionFilter) for item in logger.filters):
        return
    logger.addFilter(QueryStringRedactionFilter())
