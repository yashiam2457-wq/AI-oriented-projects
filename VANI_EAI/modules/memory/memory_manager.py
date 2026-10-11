import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from modules.config.settings import Settings

logger = logging.getLogger("VANI.Memory")
if not logger.handlers:
    logger.addHandler(logging.NullHandler())


class MemoryManager:
    """Manages persistent conversation sessions across VANI runs."""

    SUMMARY_PREFIX = "[Past context summary] "

    def __init__(self, settings: Settings):
        self.settings = settings
        self.sessions_dir = Path(settings.memory_sessions_dir)
        self.current_session_file: Optional[Path] = None

    def _ensure_dir(self):
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_files(self) -> List[Path]:
        """Returns session JSON files sorted newest-first."""
        if not self.sessions_dir.exists():
            return []
        return sorted(self.sessions_dir.glob("session_*.json"), reverse=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_recent_context(self) -> List[Dict[str, str]]:
        """Loads the most recent saved session turns into context.

        Returns a list of messages (excluding any prior system messages) that
        can be prepended to the active history after the new system prompt.
        """
        if not self.settings.memory_enabled:
            return []

        files = self._session_files()
        if not files:
            return []

        latest = files[0]
        try:
            with open(latest, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Strip system messages from saved history; we have a fresh one
            turns = [m for m in data.get("history", []) if m.get("role") != "system"]
            logger.info(f"Loaded {len(turns)} turns from {latest.name}")
            return turns
        except Exception as e:
            logger.warning(f"Failed to load session {latest}: {e}")
            return []

    def list_sessions(self) -> List[Dict]:
        """Returns metadata for all saved sessions."""
        result = []
        for f in self._session_files():
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                turns = len([m for m in data.get("history", []) if m.get("role") != "system"])
                result.append({
                    "file": f.name,
                    "timestamp": data.get("timestamp", "unknown"),
                    "persona": data.get("persona", "VANI"),
                    "turns": turns,
                })
            except Exception:
                pass
        return result

    def load_session_by_index(self, index: int) -> List[Dict[str, str]]:
        """Loads a specific session by its listing index (1-based)."""
        files = self._session_files()
        if not files or index < 1 or index > len(files):
            return []
        try:
            with open(files[index - 1], "r", encoding="utf-8") as f:
                data = json.load(f)
            return [m for m in data.get("history", []) if m.get("role") != "system"]
        except Exception as e:
            logger.warning(f"Failed to load session index {index}: {e}")
            return []

    def compress_history(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Trims history to memory_max_turns, replacing oldest turns with a brief summary.

        The summary is injected as a user→assistant exchange so the LLM stays
        within context limits without losing all continuity.
        """
        max_turns = self.settings.memory_max_turns
        # Count only user+assistant pairs (exclude system)
        conversation = [m for m in history if m["role"] != "system"]
        if len(conversation) <= max_turns:
            return history

        # Keep system message(s) + only the last max_turns conversation turns
        system_msgs = [m for m in history if m["role"] == "system"]
        recent = conversation[-max_turns:]

        # Build a plain-text summary of what was dropped
        dropped = conversation[:-max_turns]
        summary_lines = []
        for msg in dropped:
            prefix = "User" if msg["role"] == "user" else "VANI"
            snippet = msg["content"][:120].replace("\n", " ")
            summary_lines.append(f"{prefix}: {snippet}...")

        summary_text = (
            self.SUMMARY_PREFIX
            + f"Earlier in this conversation ({len(dropped)} turns compressed): "
            + " | ".join(summary_lines)
        )

        injected = [{"role": "user", "content": summary_text},
                    {"role": "assistant", "content": "Understood. I'll keep that context in mind."}]

        return system_msgs + injected + recent

    def save_session(self, history: List[Dict[str, str]], persona: str = "VANI"):
        """Saves the current session history to a timestamped JSON file."""
        if not self.settings.memory_enabled:
            return
        if not any(m["role"] != "system" for m in history):
            return  # Nothing to save — no actual conversation

        self._ensure_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_file = self.sessions_dir / f"session_{timestamp}.json"
        try:
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "persona": persona,
                    "history": history,
                }, f, indent=2, ensure_ascii=False)
            logger.info(f"Session saved to {session_file.name}")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
