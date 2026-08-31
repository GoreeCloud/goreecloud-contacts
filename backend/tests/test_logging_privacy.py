import logging

from fastapi.testclient import TestClient

from app.logging_privacy import QueryStringRedactionFilter, configure_access_log_privacy
from app.main import app


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


def _privacy_filters() -> list[logging.Filter]:
    logger = logging.getLogger("uvicorn.access")
    return [item for item in logger.filters if isinstance(item, QueryStringRedactionFilter)]


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


def test_application_import_installs_access_log_privacy_filter() -> None:
    assert len(_privacy_filters()) == 1


def test_application_lifespan_reapplies_filter_after_logger_reconfiguration() -> None:
    logger = logging.getLogger("uvicorn.access")
    logger.filters = [
        item for item in logger.filters if not isinstance(item, QueryStringRedactionFilter)
    ]
    assert _privacy_filters() == []

    with TestClient(app):
        assert len(_privacy_filters()) == 1

    assert len(_privacy_filters()) == 1


def test_access_log_privacy_configuration_is_idempotent() -> None:
    configure_access_log_privacy()
    configure_access_log_privacy()

    assert len(_privacy_filters()) == 1
