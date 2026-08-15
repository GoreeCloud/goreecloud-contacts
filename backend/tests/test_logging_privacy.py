import logging

from app.logging_privacy import QueryStringRedactionFilter, configure_access_log_privacy


def _access_record(request_target: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:50000", "GET", request_target, "1.1", 200),
        exc_info=None,
    )


def test_query_string_is_removed_from_uvicorn_access_record() -> None:
    record = _access_record(
        "/api/carddav/contact?href=%2Fprivate-user%2Fcontacts%2Fsecret.vcf&etag=private-etag"
    )

    assert QueryStringRedactionFilter().filter(record) is True
    assert record.args[2] == "/api/carddav/contact"

    rendered = record.getMessage()
    assert "private-user" not in rendered
    assert "secret.vcf" not in rendered
    assert "private-etag" not in rendered
    assert "?" not in rendered


def test_queryless_request_target_is_preserved() -> None:
    record = _access_record("/api/health/ready")

    QueryStringRedactionFilter().filter(record)

    assert record.args[2] == "/api/health/ready"
    assert record.getMessage().endswith('GET /api/health/ready HTTP/1.1" 200')


def test_access_log_privacy_configuration_is_idempotent() -> None:
    logger = logging.getLogger("uvicorn.access")

    configure_access_log_privacy()
    configure_access_log_privacy()

    filters = [item for item in logger.filters if isinstance(item, QueryStringRedactionFilter)]
    assert len(filters) == 1
