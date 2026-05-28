"""Cloud-friendly logging: stdout only (platforms capture logs automatically)."""
import logging
import sys

_INITIALIZED = False


def _setup_root_logger():
    global _INITIALIZED
    if _INITIALIZED:
        return
    _INITIALIZED = True

    from core.config import Config
    config = Config()

    root = logging.getLogger("aria")
    root.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))
    root.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)


def get_logger(name: str) -> logging.Logger:
    _setup_root_logger()
    return logging.getLogger(f"aria.{name}")
