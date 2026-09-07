"""Auto highlight clips — cut short clips out of an uploaded match recording,
synced to the ball log via each delivery's wall-clock timestamp.

Flow: the organiser uploads a recording, notes the video-time of the first ball
(the ``anchor``), and we cut a clip around every key moment. No third party; the
files live under ``settings.media_dir`` (a persistent volume in production).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from app.core import clipper
from app.schemas.match import MatchClipDTO
from app.services.match_service import MatchNotFound, MatchService

PRE_S = 4.0     # seconds of run-up before the moment
CLIP_S = 10.0   # total clip length
MAX_CLIPS = 12  # bound the work (ffmpeg re-encodes each one)


class RecordingError(Exception):
    """No recording, no ffmpeg, or nothing to clip."""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class ClipperService:
    def __init__(self, match_service: MatchService) -> None:
        self.matches = match_service

    # ----- storage layout -----
    def _rec_dir(self) -> Path:
        p = clipper.media_root() / "rec"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _clips_dir(self, match_id: str) -> Path:
        p = clipper.media_root() / "clips" / str(match_id)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _find_recording(self, match_id: str) -> Optional[Path]:
        hits = sorted(self._rec_dir().glob(f"{match_id}.*"))
        return hits[0] if hits else None

    def has_recording(self, match_id: str) -> bool:
        return self._find_recording(match_id) is not None

    # ----- upload -----
    def save_recording(self, match_id: str, file_obj, filename: str) -> float:
        """Persist an uploaded recording; return its probed duration (seconds)."""
        self.matches.get_engine(match_id)  # 404 if the match doesn't exist
        for old in self._rec_dir().glob(f"{match_id}.*"):  # one recording per match
            old.unlink(missing_ok=True)
        ext = (Path(filename).suffix or ".mp4").lower()[:6]
        dest = self._rec_dir() / f"{match_id}{ext}"
        with dest.open("wb") as out:
            shutil.copyfileobj(file_obj, out)
        dur = clipper.probe_duration(str(dest))
        if not dur:
            dest.unlink(missing_ok=True)
            raise RecordingError("That file couldn't be read as a video.")
        return dur

    # ----- generate -----
    def generate(self, match_id: str, anchor: float) -> list[MatchClipDTO]:
        """Cut a clip around each key moment. ``anchor`` = the video-time (seconds)
        at which the FIRST ball occurs; everything else is placed by ts delta."""
        if not clipper.available():
            raise RecordingError("Video clipping isn't available on this server (ffmpeg missing).", 503)
        rec = self._find_recording(match_id)
        if rec is None:
            raise RecordingError("Upload a match recording first, then generate clips.")

        engine = self.matches.get_engine(match_id)  # raises MatchNotFound
        first_ball = next((ev.ts for ev in engine.innings1.events if ev.ts), None)
        if first_ball is None:
            raise RecordingError("This match has no timestamped deliveries to sync to.")

        moments = [
            h for h in engine.highlights()
            if h.get("ts") and h["kind"] in ("wicket", "six", "four")
        ]
        if not moments:
            raise RecordingError("No clip-worthy moments (wickets or boundaries) yet.")
        moments.sort(key=lambda h: (-h["importance"], h["ts"]))
        moments = moments[:MAX_CLIPS]
        moments.sort(key=lambda h: h["ts"])  # back to chronological for display

        # keep any bring-your-own link clips; replace previously auto-generated ones
        keep = [c for c in self.matches.repo.get_clips(match_id) if c.get("source") != "auto"]
        for stale in self._clips_dir(match_id).glob("*.mp4"):
            stale.unlink(missing_ok=True)

        next_id = max((int(c["id"]) for c in keep if str(c.get("id", "")).isdigit()), default=0) + 1
        auto: list[dict] = []
        for i, h in enumerate(moments):
            t = anchor + (h["ts"] - first_ball)
            out = self._clips_dir(match_id) / f"{next_id + i}.mp4"
            try:
                clipper.cut(str(rec), start=t - PRE_S, duration=CLIP_S, out=str(out))
            except clipper.ClipError:
                continue  # skip a moment that fell outside the recording
            label = f"{h['title'].title()} · {h['text']}"[:80]
            auto.append({
                "id": str(next_id + i), "url": f"/media/{match_id}/{next_id + i}.mp4",
                "label": label, "source": "auto",
            })
        if not auto:
            raise RecordingError("Couldn't cut any clips — check the first-ball time matches the video.")
        self.matches.repo.set_clips(match_id, keep + auto)
        return [MatchService._clip_dto(c) for c in (keep + auto)]
