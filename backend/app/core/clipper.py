"""ffmpeg-backed video clipping — the engine behind auto-generated highlight clips.

Given a source recording + a list of moments (with a wall-clock timestamp), we cut
a short clip around each. ffmpeg is located via config → PATH → the Windows winget
install; if it isn't found, ``available()`` is False and callers degrade gracefully
(auto-clipping is simply offered only where the server has ffmpeg).
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from app.core.config import settings

_EXE = ".exe" if os.name == "nt" else ""

# backend/app/core/clipper.py → backend (parents[2]) → project root (parents[3])
_BACKEND = Path(__file__).resolve().parents[2]
_ROOT = Path(__file__).resolve().parents[3]


def _candidate_dirs() -> list[str]:
    """Extra folders to check for a *manually downloaded* ffmpeg — no winget/PATH
    needed. Covers a copy bundled inside the project (which then travels in a zip),
    plus the usual spots people extract ffmpeg to on Windows."""
    dirs: list[str] = []
    # bundled with the project: drop ffmpeg's bin into any of these and it's found,
    # and it moves with the project when you zip it to another machine.
    for base in (_ROOT, _BACKEND):
        dirs += [
            str(base / "ffmpeg" / "bin"), str(base / "ffmpeg"),
            str(base / "vendor" / "ffmpeg" / "bin"), str(base / "bin"),
        ]
        dirs += glob.glob(str(base / "ffmpeg*" / "bin"))  # e.g. ffmpeg-8.2.1-full_build/bin
    if os.name == "nt":  # common manual-extract locations
        local = os.environ.get("LOCALAPPDATA", "")
        for root in ("C:\\ffmpeg", "C:\\Program Files\\ffmpeg",
                     "C:\\Program Files (x86)\\ffmpeg", os.path.join(local, "ffmpeg") if local else ""):
            if root:
                dirs += [os.path.join(root, "bin"), root]
        for pat in ("C:\\ffmpeg*\\bin", "C:\\Program Files\\ffmpeg*\\bin"):
            dirs += glob.glob(pat)
    return dirs


def _discover(name: str) -> Optional[str]:
    exe = f"{name}{_EXE}"
    # 1. explicit config directory (CRICNETRA_FFMPEG_DIR)
    d = settings.ffmpeg_dir
    if d:
        p = Path(d) / exe
        if p.exists():
            return str(p)
    # 2. on PATH
    found = shutil.which(name)
    if found:
        return found
    # 3. Windows winget install (Gyan.FFmpeg) — the dev-machine case
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", "")
        pattern = os.path.join(base, "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg*", "*", "bin", exe)
        for hit in glob.glob(pattern):
            return hit
    # 4. a manually-downloaded ffmpeg (project-bundled or a common extract folder)
    for cand in _candidate_dirs():
        p = Path(cand) / exe
        if p.exists():
            return str(p)
    return None


FFMPEG = _discover("ffmpeg")
FFPROBE = _discover("ffprobe")


class ClipError(Exception):
    """ffmpeg was unavailable or a cut failed."""


def available() -> bool:
    """True when this server can cut clips (ffmpeg found)."""
    return bool(FFMPEG)


def media_root() -> Path:
    root = Path(settings.media_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def probe_duration(src: str) -> Optional[float]:
    """Duration of a video in seconds, or None if it can't be read."""
    if not FFPROBE:
        return None
    try:
        r = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", src],
            capture_output=True, text=True, timeout=30,
        )
        return float(r.stdout.strip())
    except (ValueError, subprocess.SubprocessError):
        return None


def cut(src: str, start: float, duration: float, out: str) -> bool:
    """Cut ``duration`` seconds from ``src`` beginning at ``start`` into ``out``.

    Re-encodes (H.264/AAC, +faststart) so the cut is frame-accurate and the clip
    plays inline anywhere — worth the CPU for short highlight clips. Returns True
    on a non-empty output file.
    """
    if not FFMPEG:
        raise ClipError("ffmpeg is not available on this server")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG, "-y",
        "-ss", f"{max(0.0, start):.3f}", "-i", src, "-t", f"{max(0.1, duration):.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-movflags", "+faststart", out,
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=180, check=True)
    except subprocess.CalledProcessError as e:  # pragma: no cover - ffmpeg stderr
        raise ClipError(f"ffmpeg cut failed: {e.stderr.decode('utf-8', 'ignore')[-300:]}") from e
    except subprocess.SubprocessError as e:
        raise ClipError(f"ffmpeg error: {e}") from e
    return os.path.exists(out) and os.path.getsize(out) > 0
