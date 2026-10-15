import logging
import re
import sys
from contextvars import ContextVar
import structlog

# Context variable for request correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    correlation_id_var.set(correlation_id)


def add_correlation_id(logger, method_name, event_dict):
    corr_id = get_correlation_id()
    if corr_id:
        event_dict["correlation_id"] = corr_id
    return event_dict


_SECRET_QUERY = re.compile(r"([?&](?:token|access_token|refresh_token|ticket|code)=)[^&\s'\"]+")


class RedactSecretsFilter(logging.Filter):
    """Mask credentials in logged URLs, e.g. uvicorn's line for ``/api/ws/...?token=<jwt>``."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = _SECRET_QUERY.sub(lambda m: m.group(1) + "[REDACTED]", message)
        if redacted != message:
            record.msg, record.args = redacted, None
        return True


def setup_logging(log_level: str = "INFO") -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )
    for name in ("uvicorn.access", "uvicorn.error", "uvicorn"):
        target = logging.getLogger(name)
        if not any(isinstance(f, RedactSecretsFilter) for f in target.filters):
            target.addFilter(RedactSecretsFilter())

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            add_correlation_id,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger("examsentinel")
