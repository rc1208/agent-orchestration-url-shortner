import json
import logging
import re
from datetime import UTC, datetime
from typing import Any


SENSITIVE_KEYS = {"api_key", "apikey", "authorization", "password", "secret", "token"}
INLINE_SECRET = re.compile(
    r"(?i)(api[_-]?key|authorization|password|secret|token)(\s*[=:]\s*)([^\s,;]+)"
)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if str(key).lower() in SENSITIVE_KEYS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return INLINE_SECRET.sub(r"\1\2[REDACTED]", value[:4_000])
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", "application_log"),
            "message": redact(record.getMessage())[:1_000],
            "correlation_id": getattr(record, "correlation_id", None),
            "run_id": getattr(record, "run_id", None),
            "node": getattr(record, "node", None),
            "details": redact(getattr(record, "details", {})),
        }
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging(level: int = logging.INFO) -> None:
    logger = logging.getLogger("agentic_url_shortener")
    if not any(getattr(handler, "_agentic_json", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        handler._agentic_json = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


def log_event(logger: logging.Logger, event: str, *, run_id: str | None = None,
              correlation_id: str | None = None, node: str | None = None,
              level: int = logging.INFO, details: dict[str, Any] | None = None) -> None:
    logger.log(level, event, extra={
        "event": event,
        "run_id": run_id,
        "correlation_id": correlation_id or run_id,
        "node": node,
        "details": details or {},
    })
