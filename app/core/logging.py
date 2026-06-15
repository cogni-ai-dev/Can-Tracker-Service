import contextvars
import json
import logging
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone

from app.core.pii import AUDIT_REDACTED_FIELDS, SENSITIVE_PII_FIELDS

REDACTED_VALUE = "[REDACTED]"
REQUEST_ID_CONTEXT: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id",
    default=None,
)
SENSITIVE_KEY_FRAGMENTS = (
    SENSITIVE_PII_FIELDS
    | AUDIT_REDACTED_FIELDS
    | {
        "accno",
        "account_number",
        "token",
        "secret",
    }
)
EMAIL_TEXT_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PAN_TEXT_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)
LONG_DIGIT_PATTERN = re.compile(r"\b\d{9,18}\b")


def is_sensitive_key(key: object) -> bool:
    normalized = str(key).lower()
    if normalized.endswith("_masked"):
        return False
    return any(fragment in normalized for fragment in SENSITIVE_KEY_FRAGMENTS)


def redact_sensitive_text(value: str) -> str:
    redacted = EMAIL_TEXT_PATTERN.sub(REDACTED_VALUE, value)
    redacted = PAN_TEXT_PATTERN.sub(REDACTED_VALUE, redacted)
    return LONG_DIGIT_PATTERN.sub(REDACTED_VALUE, redacted)


def redact_sensitive_data(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            key: REDACTED_VALUE if is_sensitive_key(key) else redact_sensitive_data(item) for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(redact_sensitive_data(item) for item in value)
    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    if isinstance(value, str):
        return redact_sensitive_text(value)
    return value


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_text(record.msg)
        else:
            record.msg = redact_sensitive_data(record.msg)

        if isinstance(record.args, Mapping):
            record.args = redact_sensitive_data(record.args)
        elif isinstance(record.args, Sequence) and not isinstance(record.args, str):
            record.args = tuple(redact_sensitive_data(arg) for arg in record.args)
        return True


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = getattr(record, "request_id", None) or get_current_request_id()
        if request_id:
            payload["request_id"] = request_id

        for attr in ("method", "path", "status_code", "duration_ms", "client"):
            value = getattr(record, attr, None)
            if value is not None:
                payload[attr] = value

        if record.exc_info:
            payload["exception"] = redact_sensitive_text(self.formatException(record.exc_info))

        return json.dumps(redact_sensitive_data(payload), separators=(",", ":"), default=str)


def get_current_request_id() -> str | None:
    return REQUEST_ID_CONTEXT.get()


def install_redacting_log_record_factory() -> None:
    original_factory = logging.getLogRecordFactory()
    if getattr(original_factory, "_can_tracker_redacting", False):
        return

    def redacting_record_factory(*args, **kwargs):
        record = original_factory(*args, **kwargs)
        RedactingFilter().filter(record)
        return record

    redacting_record_factory._can_tracker_redacting = True
    logging.setLogRecordFactory(redacting_record_factory)


def configure_logging(log_level: str = "INFO", *, json_logs: bool = False) -> None:
    install_redacting_log_record_factory()
    formatter: logging.Formatter
    if json_logs:
        formatter = JsonLogFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        handlers=[handler],
        force=True,
    )
