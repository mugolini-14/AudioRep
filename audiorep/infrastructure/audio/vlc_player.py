"""
VLCPlayer — Implementación de IAudioPlayer usando python-vlc (libVLC).

Incorpora análisis de audio en tiempo real para el VU meter:
  - libvlc_audio_set_callbacks intercepta el PCM decodificado.
  - _SDAudioBridge reproduce el PCM hacia sounddevice en un thread escritor.
  - _RMSAnalyzer calcula los niveles RMS en un thread separado, sin bloquear
    el thread de audio de VLC.
  - Los niveles RMS (L/R) se escriben en audiorep.core.audio_levels.

Si sounddevice no puede abrirse (conflicto de dispositivo, no instalado, etc.)
el player cae de vuelta al modo estándar de VLC sin análisis de niveles.
"""
from __future__ import annotations

import array as _pyarray
import ctypes
import logging
import math
import os
import queue
import sys
import threading

import vlc

from audiorep.core import audio_levels
from audiorep.domain.track import Track, TrackSource

logger = logging.getLogger(__name__)

# ── Constantes del formato PCM ─────────────────────────────────────────── #
_SAMPLE_RATE      = 44100
_CHANNELS         = 2
_BYTES_PER_SAMPLE = 2          # int16  →  S16N
_MAX_QUEUE        = 200        # frames máximos en cola antes de descartar


# ── Tipos ctypes para los callbacks de audio de libvlc ────────────────── #
_VLCAudioPlayCb   = ctypes.CFUNCTYPE(
    None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_int64
)
_VLCAudioPauseCb  = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int64)
_VLCAudioResumeCb = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int64)
_VLCAudioFlushCb  = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int64)
_VLCAudioDrainCb  = ctypes.CFUNCTYPE(None, ctypes.c_void_p)


def _find_vlc_plugins() -> None:
    """En bundle PyInstaller, apunta VLC_PLUGIN_PATH al directorio de plugins."""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS  # type: ignore[attr-defined]
        plugins_dir = os.path.join(base, "plugins")
        if os.path.isdir(plugins_dir):
            os.environ.setdefault("VLC_PLUGIN_PATH", plugins_dir)


_find_vlc_plugins()


# ── Puente sounddevice ─────────────────────────────────────────────────── #

class _SDAudioBridge:
    """
    Lee PCM del callback de VLC y lo escribe en un RawOutputStream de sounddevice.

    Corre un thread escritor dedicado para evitar bloquear el thread de VLC.
    """

    def __init__(self) -> None:
        import sounddevice as sd   # importación tardía → graceful degradation

        self._queue: queue.Queue[bytes] = queue.Queue(maxsize=_MAX_QUEUE)
        self._stop  = threading.Event()
        self._underrun_count = 0

        self._stream = sd.RawOutputStream(
            samplerate=_SAMPLE_RATE,
            channels=_CHANNELS,
            dtype="int16",
        )
        self._stream.start()

        self._thread = threading.Thread(
            target=self._writer, daemon=True, name="sd-audio-bridge"
        )
        self._thread.start()
        logger.debug("SDAudioBridge iniciado.")

    # ── API pública ────────────────────────────────────────────────── #

    def push(self, pcm: bytes) -> None:
        """Encola PCM para reproducción. Si la cola está llena descarta el frame más antiguo."""
        try:
            self._queue.put_nowait(pcm)
        except queue.Full:
            self._underrun_count += 1
            if self._underrun_count % 10 == 1:
                logger.warning(
                    "SDAudioBridge: cola llena, frame descartado (underruns acumulados: %d)",
                    self._underrun_count,
                )
            try:
                self._queue.get_nowait()   # descartar el más antiguo
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(pcm)
            except queue.Full:
                pass

    def flush(self) -> None:
        """Vacía la cola (llamado al buscar o detener)."""
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._underrun_count = 0

    def close(self) -> None:
        self._stop.set()
        self._queue.put(b"")   # desbloquear el thread escritor
        try:
            self._stream.stop()
            self._stream.close()
        except Exception:
            pass

    # ── Interno ────────────────────────────────────────────────────── #

    def _writer(self) -> None:
        while not self._stop.is_set():
            try:
                chunk = self._queue.get(timeout=0.1)
                if chunk and not self._stop.is_set():
                    try:
                        self._stream.write(chunk)
                    except Exception as exc:
                        logger.debug("SDAudioBridge write: %s", exc)
            except queue.Empty:
                pass


# ── Cálculo de niveles RMS ─────────────────────────────────────────── #

def _compute_levels(buf: bytes) -> None:
    """
    Calcula el RMS de los canales L/R desde PCM S16N y actualiza audio_levels.

    Submuestrea para no exceder ~128 frames por cálculo.
    Debe llamarse siempre desde un hilo que no sea el thread de audio de VLC.
    """
    a = _pyarray.array("h", buf)   # int16, nativo
    n = len(a) // _CHANNELS
    if n == 0:
        return
    step = max(1, n // 128) * _CHANNELS
    l_sum = r_sum = 0.0
    k = 0
    for i in range(0, len(a) - _CHANNELS + 1, step):
        l = a[i]     / 32768.0
        r = a[i + 1] / 32768.0
        l_sum += l * l
        r_sum += r * r
        k += 1
    if k:
        audio_levels.update(math.sqrt(l_sum / k), math.sqrt(r_sum / k))


# ── Analizador RMS asíncrono ───────────────────────────────────────── #

_MAX_ANALYZER_QUEUE = 50   # frames de análisis en cola; descartar si supera

class _RMSAnalyzer:
    """
    Hilo dedicado de análisis RMS.

    El callback PCM de VLC encola frames PCM crudos aquí en lugar de calcular
    directamente. El worker consume la cola y llama _compute_levels() sin
    bloquear el thread de audio de VLC.
    """

    def __init__(self) -> None:
        self._queue: queue.Queue[bytes | None] = queue.Queue(maxsize=_MAX_ANALYZER_QUEUE)
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._worker, daemon=True, name="rms-analyzer"
        )
        self._thread.start()
        logger.debug("RMSAnalyzer iniciado.")

    def push(self, buf: bytes) -> None:
        """Encola un frame PCM para análisis. Descarta silenciosamente si la cola está llena."""
        try:
            self._queue.put_nowait(buf)
        except queue.Full:
            pass   # pérdida de precisión del VU meter, sin consecuencias de audio

    def flush(self) -> None:
        """Vacía la cola pendiente (llamado en seek/stop)."""
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def close(self) -> None:
        self._stop.set()
        try:
            self._queue.put_nowait(None)   # desbloquear el worker
        except queue.Full:
            pass

    def _worker(self) -> None:
        while not self._stop.is_set():
            try:
                buf = self._queue.get(timeout=0.1)
                if buf is None:
                    break
                _compute_levels(buf)
            except queue.Empty:
                pass


# ── VLCPlayer ─────────────────────────────────────────────────────────── #

class VLCPlayer:
    """
    Reproductor de audio basado en libVLC.

    Implementa IAudioPlayer.
    """

    def __init__(self) -> None:
        self._instance = vlc.Instance("--no-video", "--quiet")
        self._player: vlc.MediaPlayer = self._instance.media_player_new()
        self._bridge: _SDAudioBridge | None = None
        self._analyzer: _RMSAnalyzer | None = None
        self._current_eq: object = None   # evita que el GC libere el puntero del EQ

        self._setup_audio_analysis()
        logger.debug("VLCPlayer inicializado (análisis=%s).", self._bridge is not None)

    # ------------------------------------------------------------------
    # Configuración del análisis de audio
    # ------------------------------------------------------------------

    def _setup_audio_analysis(self) -> None:
        """
        Intenta configurar callbacks de audio + sounddevice.

        Si falla (sounddevice no instalado, dispositivo ocupado, etc.),
        VLC continúa con su salida de audio estándar y el VU meter usa
        el modo de animación de respaldo.
        """
        try:
            bridge = _SDAudioBridge()
            analyzer = _RMSAnalyzer()
            self._bridge = bridge
            self._analyzer = analyzer

            # Closures que capturan el puente y el analyzer; evitan GC de los ctypes obj.
            def _play(data, samples, count, pts):  # type: ignore[misc]
                if not samples or not count:
                    return
                n_bytes = int(count) * _CHANNELS * _BYTES_PER_SAMPLE
                buf = ctypes.string_at(samples, n_bytes)
                bridge.push(buf)
                analyzer.push(buf)   # RMS calculado en el hilo del analyzer, no aquí

            def _flush(data, pts):  # type: ignore[misc]
                bridge.flush()
                analyzer.flush()
                audio_levels.reset()

            # Guardar referencias para impedir que el GC destruya los wrappers
            self._vlc_play_cb   = _VLCAudioPlayCb(_play)
            self._vlc_pause_cb  = _VLCAudioPauseCb(lambda d, p: None)
            self._vlc_resume_cb = _VLCAudioResumeCb(lambda d, p: None)
            self._vlc_flush_cb  = _VLCAudioFlushCb(_flush)
            self._vlc_drain_cb  = _VLCAudioDrainCb(lambda d: None)

            self._player.audio_set_format("S16N", _SAMPLE_RATE, _CHANNELS)
            self._player.audio_set_callbacks(
                self._vlc_play_cb,
                self._vlc_pause_cb,
                self._vlc_resume_cb,
                self._vlc_flush_cb,
                self._vlc_drain_cb,
                None,
            )

        except Exception as exc:
            logger.warning("Análisis de audio no disponible: %s", exc)
            self._bridge = None
            self._analyzer = None

    # ------------------------------------------------------------------
    # IAudioPlayer
    # ------------------------------------------------------------------

    def play(self, track: Track) -> None:
        """Reproduce un archivo de audio local o una pista de CD (CDDA)."""
        if not track.file_path:
            logger.warning("VLCPlayer.play: track sin file_path")
            return
        media = self._instance.media_new(track.file_path)
        if track.source == TrackSource.CD and track.track_number:
            media.add_option(f":cdda-track={track.track_number}")
            logger.debug(
                "VLCPlayer: play CD pista %d desde '%s'",
                track.track_number, track.file_path,
            )
        else:
            logger.debug("VLCPlayer: play '%s'", track.file_path)
        self._player.set_media(media)
        self._player.play()

    def play_url(self, url: str) -> None:
        """Reproduce un stream de URL (radio, HTTP, M3U, etc.)."""
        media = self._instance.media_new(url)
        self._player.set_media(media)
        self._player.play()
        logger.debug("VLCPlayer: play_url '%s'", url)

    def pause(self) -> None:
        self._player.pause()

    def resume(self) -> None:
        if self._player.get_state() == vlc.State.Paused:
            self._player.pause()   # VLC toggle

    def stop(self) -> None:
        if self._bridge:
            self._bridge.flush()
        if self._analyzer:
            self._analyzer.flush()
        audio_levels.reset()
        self._player.stop()

    def seek(self, position_ms: int) -> None:
        if self._bridge:
            self._bridge.flush()
        if self._analyzer:
            self._analyzer.flush()
        audio_levels.reset()
        duration = self.get_duration_ms()
        if duration > 0:
            self._player.set_position(position_ms / duration)

    def get_position_ms(self) -> int:
        return max(0, self._player.get_time())

    def get_duration_ms(self) -> int:
        return max(0, self._player.get_length())

    def set_volume(self, volume: int) -> None:
        self._player.audio_set_volume(max(0, min(100, volume)))

    def get_volume(self) -> int:
        return self._player.audio_get_volume()

    @property
    def is_playing(self) -> bool:
        return self._player.is_playing() == 1

    @property
    def is_paused(self) -> bool:
        return self._player.get_state() == vlc.State.Paused

    # ------------------------------------------------------------------
    # Ecualizador (API nativa libVLC)
    # ------------------------------------------------------------------

    def apply_equalizer(self, preamp: float, bands: list[float]) -> None:
        """Aplica el ecualizador en tiempo real. bands: lista de 10 valores en dB (-20 a +20)."""
        eq = vlc.libvlc_audio_equalizer_new()
        vlc.libvlc_audio_equalizer_set_preamp(eq, max(-20.0, min(20.0, preamp)))
        for i, amp in enumerate(bands[:10]):
            vlc.libvlc_audio_equalizer_set_amp_at_index(eq, max(-20.0, min(20.0, amp)), i)
        vlc.libvlc_media_player_set_equalizer(self._player, eq)
        # Mantener referencia para que el GC no libere el puntero mientras VLC lo usa.
        self._current_eq = eq
        logger.debug("VLCPlayer: EQ aplicado (preamp=%.1f)", preamp)

    def disable_equalizer(self) -> None:
        """Desactiva el ecualizador."""
        vlc.libvlc_media_player_set_equalizer(self._player, None)
        self._current_eq = None
        logger.debug("VLCPlayer: EQ desactivado.")

    @staticmethod
    def get_eq_preset_count() -> int:
        return vlc.libvlc_audio_equalizer_get_preset_count()

    @staticmethod
    def get_eq_preset_name(index: int) -> str:
        raw = vlc.libvlc_audio_equalizer_get_preset_name(index)
        return raw.decode() if isinstance(raw, bytes) else str(raw)

    @staticmethod
    def get_eq_preset_bands(index: int) -> tuple[float, list[float]]:
        """Retorna (preamp, [10 bandas]) para el preset VLC con el índice dado."""
        eq = vlc.libvlc_audio_equalizer_new_from_preset(index)
        preamp = vlc.libvlc_audio_equalizer_get_preamp(eq)
        bands  = [vlc.libvlc_audio_equalizer_get_amp_at_index(eq, i) for i in range(10)]
        vlc.libvlc_audio_equalizer_release(eq)
        return float(preamp), [float(b) for b in bands]
