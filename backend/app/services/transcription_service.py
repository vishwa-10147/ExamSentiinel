"""Interview speech-to-text with faster-whisper (CPU, int8).

Optional dependency (``requirements-ai.txt``). The model is downloaded on first
use (``WHISPER_MODEL_SIZE``: tiny | base | small …, default ``base``) and loaded
once per process. Audio arrives as short standalone WebM/Opus clips recorded in
the candidate's browser; PyAV (bundled with faster-whisper) decodes them, so no
system ffmpeg is required.
"""

import io
import os
import re
import threading
from typing import Any

from app.core.logging import logger


class TranscriptionUnavailable(RuntimeError):
    pass


class TranscriptionService:
    def __init__(self) -> None:
        self.model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
        self._model = None
        self._error: str | None = None
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            return False
        return self._error is None

    def _get_model(self):
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is None:
                if self._error:
                    raise TranscriptionUnavailable(self._error)
                try:
                    from faster_whisper import WhisperModel

                    self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                    logger.info("transcription.model_loaded", size=self.model_size)
                except ImportError as exc:
                    raise TranscriptionUnavailable("faster-whisper is not installed (requirements-ai.txt)") from exc
                except Exception as exc:  # download failure, corrupt cache …
                    logger.error("transcription.model_load_failed", error=str(exc))
                    raise TranscriptionUnavailable(f"Speech model could not be loaded: {exc}") from exc
        return self._model

    @staticmethod
    def _decode(audio: bytes):
        """Any container/codec PyAV knows (WebM/Opus, WAV, Ogg, MP4) -> 16 kHz mono float32.

        Done here rather than by faster-whisper's own decoder, which passes
        arguments newer PyAV releases removed.
        """
        import av
        import numpy as np

        chunks = []
        with av.open(io.BytesIO(audio), mode="r") as container:
            resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
            for frame in container.decode(audio=0):
                for out in resampler.resample(frame):
                    chunks.append(out.to_ndarray().reshape(-1))
            for out in resampler.resample(None):  # flush
                chunks.append(out.to_ndarray().reshape(-1))
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks).astype(np.float32) / 32768.0

    def transcribe(self, audio: bytes, language: str | None = None) -> dict[str, Any]:
        """Transcribe one standalone audio clip. CPU-bound: call via asyncio.to_thread."""
        model = self._get_model()
        try:
            samples = self._decode(audio)
        except Exception as exc:
            raise ValueError(f"Audio could not be decoded: {exc}") from exc
        if samples.size < 1600:  # under 0.1 s
            return {"language": language, "segments": []}
        try:
            with self._lock:  # one inference at a time per process keeps CPU use predictable
                segments, info = model.transcribe(
                    samples,
                    language=language,
                    vad_filter=True,  # skip silence instead of hallucinating text
                    beam_size=1,
                )
                result = [
                    {"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
                    for s in segments
                    if s.text.strip()
                ]
        except Exception as exc:
            raise ValueError(f"Audio could not be decoded: {exc}") from exc
        return {"language": info.language, "segments": result}


def topic_coverage(topics: list[str], segments: list[dict]) -> dict[str, bool]:
    """Which interviewer-defined topics were mentioned (whole-word, case-insensitive)."""
    text = " ".join(s.get("text", "") for s in segments).lower()
    return {
        topic: bool(re.search(r"(?<![a-z0-9])" + re.escape(topic.lower()) + r"(?![a-z0-9])", text))
        for topic in topics
    }


transcription_service = TranscriptionService()
