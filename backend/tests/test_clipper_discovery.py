"""ffmpeg binary discovery — so a manually-downloaded ffmpeg is found without
editing PATH (config dir, a project-bundled copy, or a common extract folder).

These run even when ffmpeg isn't installed (they use a fake binary file)."""

from __future__ import annotations

from app.core import clipper


def test_discover_prefers_config_dir(tmp_path, monkeypatch):
    """CRICNETRA_FFMPEG_DIR pointing at the folder wins over everything else."""
    exe = tmp_path / ("ffmpeg" + clipper._EXE)
    exe.write_bytes(b"stub")
    monkeypatch.setattr(clipper.settings, "ffmpeg_dir", str(tmp_path))
    assert clipper._discover("ffmpeg") == str(exe)


def test_discover_finds_bundled_or_extracted_ffmpeg(tmp_path, monkeypatch):
    """With no config dir, not on PATH, and no winget install, a copy in one of the
    candidate folders (project-bundled or a common extract dir) is still found."""
    exe = tmp_path / ("ffmpeg" + clipper._EXE)
    exe.write_bytes(b"stub")
    monkeypatch.setattr(clipper.settings, "ffmpeg_dir", None)
    monkeypatch.setattr(clipper.shutil, "which", lambda name: None)
    monkeypatch.setattr(clipper.glob, "glob", lambda *a, **k: [])  # no winget hit
    monkeypatch.setattr(clipper, "_candidate_dirs", lambda: [str(tmp_path)])
    assert clipper._discover("ffmpeg") == str(exe)


def test_discover_returns_none_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(clipper.settings, "ffmpeg_dir", None)
    monkeypatch.setattr(clipper.shutil, "which", lambda name: None)
    monkeypatch.setattr(clipper.glob, "glob", lambda *a, **k: [])
    monkeypatch.setattr(clipper, "_candidate_dirs", lambda: [str(tmp_path)])  # empty dir
    assert clipper._discover("ffmpeg") is None


def test_candidate_dirs_includes_a_project_bundle_path():
    """You can drop ffmpeg into <project>/ffmpeg/bin and it travels in the zip."""
    joined = " ".join(clipper._candidate_dirs()).replace("\\", "/")
    assert "/ffmpeg/bin" in joined
