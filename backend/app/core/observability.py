"""Sentry + structured-JSON logging bootstrap — §6.12.

Two side-effects, both opt-in via config:

  • ``init_sentry()`` — initialises ``sentry_sdk`` with the configured
    DSN. When the DSN is empty (default), this is a no-op so dev
    installs don't need a Sentry project to boot.
  • ``init_structured_logging()`` — replaces uvicorn's default
    formatter with a JSON formatter that prints one log line per
    record with ``timestamp``, ``level``, ``logger``, ``message``,
    and (when set as logging.LogRecord.extra) ``organization_id``,
    ``correlation_id``.

Called from app lifespan in ``app/api/main.py``.

The /health/dependencies endpoint is added separately — it probes
the DB / Redis / MinIO / Resend / Anthropic reachability and returns
a flat dict the operator's monitoring system polls.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from app.core.config import settings


def init_sentry() -> None:
    """No-op when ``settings.sentry_dsn`` is empty."""
    if not getattr(settings, "sentry_dsn", ""):
        return
    try:
        import sentry_sdk
    except Exception:  # pragma: no cover — sentry-sdk optional in dev
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        traces_sample_rate=float(
            getattr(settings, "sentry_traces_sample_rate", 0.0)
        ),
        send_default_pii=False,
    )


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include any extras the caller attached via the
        # `extra={"key": ...}` kwarg.
        for k, v in record.__dict__.items():
            if k in (
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "message",
                "module",
                "msecs",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            ):
                continue
            try:
                json.dumps(v)
                payload[k] = v
            except Exception:
                payload[k] = repr(v)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def init_structured_logging() -> None:
    """Re-attach a single JSON handler to the root logger."""
    if not getattr(settings, "json_logging_enabled", False):
        return
    root = logging.getLogger()
    # Drop any pre-existing handlers so we don't double-print.
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)


__all__ = ["init_sentry", "init_structured_logging"]
