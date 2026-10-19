"""Filesystem paths used by the application."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "PDFToAudiobook"


def is_frozen() -> bool:
    """Return whether the app is running from a packaged executable."""
    return bool(getattr(sys, "frozen", False))


def user_data_dir() -> Path:
    """Return a per-user writable directory for settings and diagnostics."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_NAME

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / APP_NAME


def ensure_user_data_dir() -> Path:
    """Create and return the writable app data directory."""
    path = user_data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_output_dir() -> Path:
    """Return the user's Desktop when available, otherwise their home folder."""
    desktop = Path.home() / "Desktop"
    return desktop if desktop.is_dir() else Path.home()


def default_output_path(source_pdf: str | Path) -> Path:
    """Return the proposed Desktop MP3 path for a selected PDF."""
    return default_output_dir() / f"{Path(source_pdf).stem}.mp3"
