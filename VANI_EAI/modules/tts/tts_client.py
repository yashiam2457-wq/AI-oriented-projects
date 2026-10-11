"""
tts_client.py — Text-to-Speech using Kokoro ONNX (neural, human-like voice).

Kokoro synthesises audio to a numpy array, played via sounddevice in a background
thread. Falls back to pyttsx3 if Kokoro is not installed.
"""
import logging
import queue
import re
import threading
from typing import Optional

from modules.config.settings import Settings


class TTSClient:
    """Offline Text-to-Speech client — Kokoro ONNX primary, pyttsx3 fallback."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._queue: queue.Queue = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._kokoro = None      # Kokoro model instance
        self._use_kokoro = True  # Flipped to False if Kokoro unavailable
        self.logger = logging.getLogger("VANI.TTS")
        if not self.logger.handlers:
            self.logger.addHandler(logging.NullHandler())

    # ------------------------------------------------------------------
    # Startup / shutdown
    # ------------------------------------------------------------------

    def start(self):
        """Starts the background speech thread if TTS is enabled."""
        if self.settings.tts_enabled and not self._running:
            self._running = True
            self._thread = threading.Thread(
                target=self._run_loop, name="VANI_TTS_Thread", daemon=True
            )
            self._thread.start()

    def close(self):
        """Shuts down the background thread cleanly."""
        self.stop_speaking()
        if self._running:
            self._running = False
            self._queue.put(None)  # Sentinel
            if self._thread:
                self._thread.join(timeout=2.0)

    # ------------------------------------------------------------------
    # Kokoro initialisation
    # ------------------------------------------------------------------

    def _init_kokoro(self):
        """Loads the Kokoro ONNX model. Called once inside the background thread."""
        try:
            from kokoro_onnx import Kokoro
            self._kokoro = Kokoro("kokoro-v1.9.onnx", "voices-v1.0.bin")
            self.logger.info("Kokoro TTS model loaded successfully.")
        except ImportError:
            self.logger.warning(
                "kokoro-onnx not installed. Falling back to pyttsx3. "
                "Run: pip install kokoro-onnx soundfile"
            )
            self._use_kokoro = False
        except Exception as e:
            self.logger.warning(f"Kokoro init failed ({e}). Falling back to pyttsx3.")
            self._use_kokoro = False

    # ------------------------------------------------------------------
    # Background loop
    # ------------------------------------------------------------------

    def _run_loop(self):
        """Main loop: initialise engine, then process speech queue."""
        # Try Kokoro first
        self._init_kokoro()

        # Initialise pyttsx3 as fallback if needed
        pyttsx3_engine = None
        if not self._use_kokoro:
            try:
                import pyttsx3
                pyttsx3_engine = pyttsx3.init()
                pyttsx3_engine.setProperty("rate", 175)
                pyttsx3_engine.setProperty("volume", 1.0)
            except Exception as e:
                self.logger.error(f"pyttsx3 fallback also failed: {e}")
                self._running = False
                return

        while self._running:
            try:
                item = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if item is None:  # Shutdown sentinel
                self._queue.task_done()
                break

            text = item
            if not text or not text.strip():
                self._queue.task_done()
                continue

            if self.settings.tts_enabled:
                try:
                    if self._use_kokoro and self._kokoro is not None:
                        self._speak_kokoro(text)
                    elif pyttsx3_engine:
                        pyttsx3_engine.say(text)
                        pyttsx3_engine.runAndWait()
                except Exception as e:
                    self.logger.error(f"TTS speech error: {e}")

            self._queue.task_done()

        self._running = False

    # ------------------------------------------------------------------
    # Kokoro speech synthesis
    # ------------------------------------------------------------------

    def _speak_kokoro(self, text: str):
        """Synthesises text with Kokoro and plays it via sounddevice."""
        import sounddevice as sd
        try:
            samples, sample_rate = self._kokoro.create(
                text,
                voice=self.settings.kokoro_voice,
                speed=self.settings.kokoro_speed,
                lang="en-us",
            )
            # Play synchronously on the TTS thread
            sd.play(samples, sample_rate)
            sd.wait()
        except Exception as e:
            self.logger.error(f"Kokoro synthesis error: {e}")

    # ------------------------------------------------------------------
    # Text cleaning
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_for_speech(text: str) -> str:
        """Strips markdown and expands common abbreviations for natural TTS output."""
        # Remove markdown links: [text](url) → text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        # Remove code blocks
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        text = text.replace("`", "")
        # Strip bold/italic markers
        text = re.sub(r"[*_]{1,3}", "", text)
        # Strip headers
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        # Strip bullet markers
        text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
        # Common abbreviations
        replacements = [
            (r"\be\.g\.\b", "for example"),
            (r"\bi\.e\.\b", "that is"),
            (r"\betc\.\b",  "and so on"),
        ]
        for pat, rep in replacements:
            text = re.sub(pat, rep, text, flags=re.IGNORECASE)
        return text.strip()

    # ------------------------------------------------------------------
    # Public speech interface
    # ------------------------------------------------------------------

    def speak(self, text: str):
        """Queues text for speech output."""
        if not self.settings.tts_enabled or not text:
            return
        if not self._running:
            self.start()
        cleaned = self._clean_for_speech(text)
        if cleaned:
            self._queue.put(cleaned)

    def stop_speaking(self):
        """Drains the speech queue and stops current playback."""
        # Drain queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break
        # Stop sounddevice playback
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
