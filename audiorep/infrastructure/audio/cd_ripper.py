"""
CDRipper — Implementación de ICDRipper usando VLC sout transcoding.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import vlc

from audiorep.core.utils import ensure_dir, safe_filename
from audiorep.domain.cd_disc import CDDisc

logger = logging.getLogger(__name__)

_VLC_FORMATS = {
    "flac": "flac",
    "mp3":  "mp3",
    "ogg":  "vorbis",
    "wav":  "s16l",
}

_EXTENSIONS = {
    "flac": ".flac",
    "mp3":  ".mp3",
    "ogg":  ".ogg",
    "wav":  ".wav",
}


class CDRipper:
    """Extrae pistas de CD a archivos de audio vía libVLC. Implementa ICDRipper."""

    def rip_track(
        self,
        disc: CDDisc,
        track_number: int,
        output_dir: str,
        format: str = "flac",
    ) -> None:
        ensure_dir(output_dir)
        ext = _EXTENSIONS.get(format, ".flac")
        vlc_fmt = _VLC_FORMATS.get(format, "flac")

        track = next((t for t in disc.tracks if t.number == track_number), None)
        title = track.title if track and track.title else f"Track {track_number:02d}"
        filename = safe_filename(f"{track_number:02d} - {title}") + ext
        output_path = str(Path(output_dir) / filename)

        drive = disc.drive_path or ""
        mrl = f"cdda://{drive}@{track_number}"

        instance = vlc.Instance()
        media = instance.media_new(mrl)
        media.add_option(
            f":sout=#transcode{{acodec={vlc_fmt},ab=320,channels=2}}"
            f":std{{access=file,mux={vlc_fmt},dst={output_path}}}"
        )
        media.add_option(":no-sout-rtp-sap")
        media.add_option(":no-sout-standard-sap")
        media.add_option(":sout-keep")

        player = instance.media_player_new()
        player.set_media(media)
        player.play()

        import time
        while player.get_state() not in (vlc.State.Ended, vlc.State.Error, vlc.State.Stopped):
            time.sleep(0.5)

        player.stop()
        instance.release()
        logger.info("CDRipper: ripeada pista %d → %s", track_number, output_path)

    def rip_all(
        self,
        disc: CDDisc,
        output_dir: str,
        format: str = "flac",
    ) -> None:
        for track in disc.tracks:
            self.rip_track(disc, track.number, output_dir, format)
