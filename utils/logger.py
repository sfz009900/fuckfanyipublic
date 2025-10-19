import logging
import os


def get_logger(name: str) -> logging.Logger:
    """Create a module-level logger with sane defaults.

    - Reads level from env var `OCR_LOG_LEVEL` (default INFO)
    - Logs to stdout with concise format
    """
    level_name = os.getenv("OCR_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger(name)
    if logger.handlers:
        # Already configured
        logger.setLevel(level)
        return logger

    handler = logging.StreamHandler()
    fmt = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    handler.setFormatter(logging.Formatter(fmt))

    logger.addHandler(handler)
    logger.setLevel(level)
    return logger

