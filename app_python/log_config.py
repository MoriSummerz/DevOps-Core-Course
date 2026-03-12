import logging
import sys

from pythonjsonlogger.json import JsonFormatter


def setup_json_logging():
    """Configure JSON structured logging for all loggers."""
    formatter = JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Reduce noise from uvicorn access logs (we log requests ourselves)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
