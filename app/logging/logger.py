"""
Structured JSON logger with correlation ID support.
Each request carries a correlation_id propagated through context vars.
"""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import json

# ─── Correlation ID context variable ─────────────────────────────────────────
_correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def set_correlation_id(cid: str) -> None:
    _correlation_id_var.set(cid)


def get_correlation_id() -> str:
    cid = _correlation_id_var.get("")
    if not cid:
        cid = str(uuid.uuid4())
        set_correlation_id(cid)
    return cid


# ─── JSON Formatter ───────────────────────────────────────────────────────────

class JsonFormatter(logging.Formatter):
    """Emit logs as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }
        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)
        # Carry any extra kwargs added via logger.info("msg", extra={...})
        for key, val in record.__dict__.items():
            if key not in {
                "msg", "args", "levelname", "levelno", "pathname", "filename",
                "module", "exc_info", "exc_text", "stack_info", "lineno",
                "funcName", "created", "msecs", "relativeCreated", "thread",
                "threadName", "processName", "process", "name", "message",
                "taskName",
            }:
                log_data[key] = val
        return json.dumps(log_data, ensure_ascii=False, default=str)


# ─── Logger factory ───────────────────────────────────────────────────────────

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # Already configured

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False
    return logger


# ─── Default application logger ───────────────────────────────────────────────
from app.config import get_settings as _get_settings

_settings = _get_settings()
logger = setup_logger("ai_person", _settings.log_level)
