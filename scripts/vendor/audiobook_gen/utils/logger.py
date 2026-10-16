"""
Logger centralizado de AudioBookGen.

Proporciona logging consistente a archivo y consola.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


_INITIALIZED = False


def setup_logger(
    log_file: str = "audiobook_gen.log",
    debug: bool = False,
) -> logging.Logger:
    """Configura y devuelve el logger raíz de la aplicación."""
    global _INITIALIZED

    logger = logging.getLogger("audiobook_gen")

    if _INITIALIZED:
        return logger

    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler de consola
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if debug else logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # Handler de archivo
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (OSError, PermissionError):
        logger.warning("Could not create log file: %s", log_file)

    _INITIALIZED = True
    return logger


def get_logger(name: str) -> logging.Logger:
    """Obtiene un sub-logger del sistema."""
    return logging.getLogger(f"audiobook_gen.{name}")
