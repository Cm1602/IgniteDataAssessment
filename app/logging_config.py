"""Logging set up as JSON, with the request id attached to every line.

Log aggregators want structured lines, not prose. Writing JSON straight out
means no regex parsing on the way in.

The request id lives in a ContextVar rather than being passed around as an
argument. Each request sets it once, and anything that logs during that request
picks it up, however deep in the call stack it is.

It is stamped onto the record when the record is created, not when it is
formatted. Formatting can happen later, on another thread, or not at all, by
which point the context has moved on. Stamping at creation means the id belongs
to the event rather than to the rendering of it.
"""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

current_request_id: ContextVar[str | None] = ContextVar("current_request_id", default=None)

# Everything the standard library already puts on a LogRecord. Anything else was
# added by us or by a caller using extra=, so it is worth putting in the output.
_STANDARD_RECORD_FIELDS = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__.keys()
) | {"message", "asctime", "taskName"}

_record_factory_installed = False


def install_request_id_on_records() -> None:
    """Make every log record carry the current request id.

    Wrapping the record factory is the standard way to add context to records
    without threading it through every logging call. Guarded so that calling
    configure_logging more than once does not stack wrappers on top of each
    other.
    """
    global _record_factory_installed
    if _record_factory_installed:
        return

    previous_factory = logging.getLogRecordFactory()

    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = previous_factory(*args, **kwargs)
        record.request_id = current_request_id.get()
        return record

    logging.setLogRecordFactory(factory)
    _record_factory_installed = True


class JsonFormatter(logging.Formatter):
    """Render a log record as a single line of JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_FIELDS and value is not None:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Send logs to stdout as JSON.

    Replaces existing handlers so uvicorn's own formatting does not end up
    interleaved with ours.
    """
    install_request_id_on_records()

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # uvicorn installs its own handlers. Clearing them makes its lines come
    # through the formatter above rather than alongside it.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
