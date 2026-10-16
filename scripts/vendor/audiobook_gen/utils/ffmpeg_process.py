"""Windows process handling for FFmpeg helpers."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


_FFMPEG_EXECUTABLES = {
    "ffmpeg",
    "ffmpeg.exe",
    "ffprobe",
    "ffprobe.exe",
    "avconv",
    "avconv.exe",
}


def _command_name(command: Any) -> str:
    if isinstance(command, (list, tuple)):
        if not command:
            return ""
        command = command[0]

    if command is None:
        return ""

    return Path(str(command).strip('"')).name.lower()


def _is_ffmpeg_command(command: Any) -> bool:
    return _command_name(command) in _FFMPEG_EXECUTABLES


class _PydubSubprocessProxy:
    def __init__(self, module: Any, popen: Any) -> None:
        self._module = module
        self.Popen = popen

    def __getattr__(self, name: str) -> Any:
        return getattr(self._module, name)


def install_hidden_ffmpeg_processes() -> None:
    """Hide FFmpeg/FFprobe console windows spawned by pydub on Windows."""
    if os.name != "nt" or not hasattr(subprocess, "STARTUPINFO"):
        return

    try:
        import pydub.audio_segment as pydub_audio_segment
        import pydub.utils as pydub_utils
    except Exception:
        return

    current_popen = pydub_utils.Popen
    if getattr(current_popen, "_audiobookgen_hides_ffmpeg_windows", False):
        return

    original_popen = subprocess.Popen

    def hidden_ffmpeg_popen(*popenargs: Any, **kwargs: Any) -> subprocess.Popen:
        command = popenargs[0] if popenargs else kwargs.get("args")
        if _is_ffmpeg_command(command):
            kwargs = dict(kwargs)
            startupinfo = kwargs.get("startupinfo") or subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            kwargs["startupinfo"] = startupinfo
            kwargs["creationflags"] = kwargs.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW

        return original_popen(*popenargs, **kwargs)

    hidden_ffmpeg_popen._audiobookgen_hides_ffmpeg_windows = True  # type: ignore[attr-defined]
    hidden_ffmpeg_popen._audiobookgen_original_popen = original_popen  # type: ignore[attr-defined]

    pydub_utils.Popen = hidden_ffmpeg_popen
    pydub_audio_segment.subprocess = _PydubSubprocessProxy(
        subprocess,
        hidden_ffmpeg_popen,
    )
