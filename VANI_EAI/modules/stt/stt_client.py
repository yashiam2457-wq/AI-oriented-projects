"""
stt_client.py — Speech-to-Text using whisper.cpp via pywhispercpp.

whisper.cpp is the C++ implementation of OpenAI Whisper — zero Python torch
dependency, runs on CPU via GGML, same tiny/base model quality as the original.

Records microphone audio via sounddevice with amplitude-based silence detection,
then transcribes locally using the downloaded GGML model file.
"""
import queue
import tempfile
import threading
import time
import wave
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
from rich.console import Console
from rich.live import Live
from rich.text import Text

from modules.config.settings import Settings


class STTClient:
    """Offline Speech-to-Text client using whisper.cpp (pywhispercpp) + sounddevice."""

    SAMPLE_RATE     = 16000   # whisper.cpp requires 16 kHz mono
    BLOCK_SIZE      = 1024    # Audio callback chunk size in samples
    MAX_RECORD_SECS = 60      # Hard cap to prevent infinite recording

    def __init__(self, settings: Settings):
        self.settings = settings
        self.console = Console()
        self._model = None
        self._model_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------

    def _ensure_model(self):
        """Lazily loads the whisper.cpp model on first call (auto-downloads GGML file)."""
        if self._model is not None:
            return
        with self._model_lock:
            if self._model is not None:
                return
            try:
                from pywhispercpp.model import Model
                model_size = self.settings.whisper_model  # 'tiny' or 'base'
                size_label = "~75 MB" if model_size == "tiny" else "~145 MB"
                self.console.print(
                    f"[dim cyan]Loading Whisper '{model_size}' model via whisper.cpp "
                    f"({size_label}, first-time download may take a moment)…[/dim cyan]"
                )
                # Model auto-downloads to ~/.cache/pywhispercpp/models/ on first use
                # No torch, no CUDA — pure C++ inference
                self._model = Model(model_size, print_realtime=False, print_progress=False)
                self.console.print(f"[dim green]✓ Whisper '{model_size}' (whisper.cpp) ready.[/dim green]")
            except ImportError:
                raise RuntimeError(
                    "pywhispercpp is not installed. Run: pip install pywhispercpp"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to load whisper.cpp model '{self.settings.whisper_model}': {e}")

    # ------------------------------------------------------------------
    # Live microphone UI
    # ------------------------------------------------------------------

    def _make_ui(self, rms: float, speech_started: bool = False, finished: bool = False) -> Text:
        """Generates a live Rich text panel showing volume bar and recording status."""
        bars = min(10, int(rms / (self.settings.stt_silence_threshold * 0.8)))
        vol_bar = "█" * bars + "░" * (10 - bars)

        ui = Text()
        if finished:
            ui.append("🎤 [Done — transcribing…] ", style="bold green")
        elif speech_started:
            ui.append("🎤 [Recording speech] ", style="bold green")
            ui.append(f"Vol: [{vol_bar}]  ", style="green")
            ui.append("Listening…", style="italic green")
        else:
            ui.append("🎤 [Listening] ", style="bold cyan")
            ui.append(f"Vol: [{vol_bar}]  ", style="cyan")
            ui.append("Speak now…", style="italic dim white")
        return ui

    # ------------------------------------------------------------------
    # Audio recording with speech & silence detection
    # ------------------------------------------------------------------

    def _record_audio(self) -> Optional[np.ndarray]:
        """
        Waits for speech to start (up to initial_timeout), then records until
        silence (> stt_silence_duration secs) or MAX_RECORD_SECS.
        Returns a float32 mono array at 16 kHz, or None if no speech detected.
        """
        audio_q: queue.Queue = queue.Queue()

        def callback(indata, frames, time_info, status):
            audio_q.put(indata.copy())

        frames_collected = []
        speech_started = False
        silence_start: Optional[float] = None
        start_time = time.monotonic()
        initial_timeout = 7.0  # Seconds allowed for user to begin speaking

        silence_dur  = self.settings.stt_silence_duration
        silence_rms  = self.settings.stt_silence_threshold
        max_frames   = self.MAX_RECORD_SECS * self.SAMPLE_RATE
        total_frames = 0

        with sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=self.BLOCK_SIZE,
            callback=callback,
        ):
            with Live(
                self._make_ui(0.0, speech_started=False),
                console=self.console,
                refresh_per_second=10,
            ) as live:
                while True:
                    try:
                        block = audio_q.get(timeout=0.2)
                    except queue.Empty:
                        continue

                    frames_collected.append(block)
                    total_frames += len(block)

                    # RMS amplitude scaled to match stt_silence_threshold range
                    rms = float(np.sqrt(np.mean(block ** 2)) * 32768)

                    # Update live UI
                    live.update(self._make_ui(rms, speech_started=speech_started))

                    # Speech & Silence State Machine
                    if not speech_started:
                        if rms >= silence_rms:
                            speech_started = True
                            silence_start = None
                        elif (time.monotonic() - start_time) >= initial_timeout:
                            # User didn't speak within 7 seconds
                            live.update(self._make_ui(rms, speech_started=False, finished=True))
                            break
                    else:
                        if rms < silence_rms:
                            if silence_start is None:
                                silence_start = time.monotonic()
                            elif (time.monotonic() - silence_start) >= silence_dur:
                                live.update(self._make_ui(rms, speech_started=True, finished=True))
                                break
                        else:
                            silence_start = None  # Speech ongoing

                    if total_frames >= max_frames:
                        break

        if not speech_started or not frames_collected:
            return None
        return np.concatenate(frames_collected, axis=0).flatten()

    # ------------------------------------------------------------------
    # Save to WAV for whisper.cpp
    # ------------------------------------------------------------------

    def _save_wav(self, audio: np.ndarray) -> str:
        """Saves float32 audio array to a temporary 16-bit WAV file. Returns file path."""
        pcm = (audio * 32767).clip(-32768, 32767).astype(np.int16)
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)       # 16-bit
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(pcm.tobytes())
        return tmp.name

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def listen(self) -> str:
        """
        Records microphone input and transcribes with whisper.cpp on CPU.
        Returns the transcribed string, or empty string on silence/error.
        """
        try:
            self._ensure_model()
        except RuntimeError as e:
            self.console.print(f"[red]{e}[/red]")
            return ""

        try:
            audio = self._record_audio()
        except Exception as e:
            self.console.print(f"[red]Microphone error: {e}[/red]")
            return ""

        if audio is None or len(audio) == 0:
            return ""

        # Save to WAV and transcribe
        wav_path = None
        try:
            wav_path = self._save_wav(audio)
            segments = self._model.transcribe(wav_path)
            text = " ".join(seg.text for seg in segments).strip()
            if text:
                self.console.print(f'[dim]🎤 Whisper: "{text}"[/dim]')
            return text
        except Exception as e:
            self.console.print(f"[red]Transcription error: {e}[/red]")
            return ""
        finally:
            if wav_path:
                try:
                    Path(wav_path).unlink(missing_ok=True)
                except Exception:
                    pass
