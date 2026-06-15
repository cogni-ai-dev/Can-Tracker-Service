import logging
from json import loads

from app.core.logging import (
    JsonLogFormatter,
    RedactingFilter,
    configure_logging,
    redact_sensitive_data,
    redact_sensitive_text,
)


def test_redact_sensitive_data_masks_matching_keys_and_text_values() -> None:
    redacted = redact_sensitive_data(
        {
            "pan": "ABCDE1234F",
            "nested": {"email": "client@example.com"},
            "message": "PAN ABCDE1234F account 001122334455 belongs to client@example.com",
            "pan_masked": "ABCDE****F",
        }
    )

    assert redacted["pan"] == "[REDACTED]"
    assert redacted["nested"]["email"] == "[REDACTED]"
    assert redacted["message"] == "PAN [REDACTED] account [REDACTED] belongs to [REDACTED]"
    assert redacted["pan_masked"] == "ABCDE****F"


def test_redact_sensitive_text_masks_common_pii_shapes() -> None:
    assert redact_sensitive_text("abcde1234f client@example.com 9876543210") == ("[REDACTED] [REDACTED] [REDACTED]")


def test_redacting_filter_scrubs_log_record_args() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="payload=%s",
        args=({"email": "client@example.com"},),
        exc_info=None,
    )

    assert RedactingFilter().filter(record) is True
    assert record.args == {"email": "[REDACTED]"}


def test_configure_logging_installs_record_factory_redaction() -> None:
    original_factory = logging.getLogRecordFactory()
    try:
        configure_logging("INFO")
        factory = logging.getLogRecordFactory()
        record = factory(
            "child.logger",
            logging.INFO,
            __file__,
            1,
            "PAN %s",
            ("ABCDE1234F",),
            None,
        )

        assert record.args == ("[REDACTED]",)
    finally:
        logging.setLogRecordFactory(original_factory)


def test_json_log_formatter_adds_request_context_and_redacts_values() -> None:
    record = logging.LogRecord(
        name="app.request",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="client email client@example.com",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-json"
    record.method = "GET"
    record.path = "/api/v1/members"
    record.status_code = 200
    record.duration_ms = 12.3
    record.client = "127.0.0.1"

    payload = loads(JsonLogFormatter().format(record))

    assert payload["request_id"] == "req-json"
    assert payload["method"] == "GET"
    assert payload["path"] == "/api/v1/members"
    assert payload["status_code"] == 200
    assert payload["message"] == "client email [REDACTED]"
