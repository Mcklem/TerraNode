import logging
import sys
from typing import Optional


class IoTFormatter(logging.Formatter):
    """Custom logging formatter that includes node_id and device_id context if available."""

    def format(self, record: logging.LogRecord) -> str:
        node = getattr(record, "node_id", None)
        device = getattr(record, "device_id", None)

        prefix_parts = []
        if node:
            prefix_parts.append(f"node:{node}")
        if device:
            prefix_parts.append(f"device:{device}")

        context = f"[{' '.join(prefix_parts)}] " if prefix_parts else ""

        # Format message
        log_fmt = f"%(asctime)s [%(levelname)s] {context}%(message)s"
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


class ContextAdapter(logging.LoggerAdapter):
    """Adapter that injects node_id and device_id into log records."""

    def __init__(self, logger: logging.Logger, node_id: Optional[str] = None, device_id: Optional[str] = None):
        super().__init__(logger, {"node_id": node_id, "device_id": device_id})

    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def setup_logging(level: int = logging.INFO) -> None:
    """Configure system-wide logging with the custom IoTFormatter."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(IoTFormatter())
    root_logger.addHandler(handler)


def get_logger(name: str, node_id: Optional[str] = None, device_id: Optional[str] = None) -> ContextAdapter:
    """Get a context-aware logger adapter."""
    logger = logging.getLogger(name)
    return ContextAdapter(logger, node_id=node_id, device_id=device_id)
