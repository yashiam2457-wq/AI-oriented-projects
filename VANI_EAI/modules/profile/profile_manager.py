"""
profile_manager.py — Phase 10: Personal Profile & Persistent User Notes

Stores the user's name and personal notes in a local JSON file.
The profile is injected into the system prompt so VANI always has
context about the user across sessions.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from modules.config.settings import Settings


class ProfileManager:
    """Manages the user's personal profile and persistent notes."""

    def __init__(self, settings: Settings):
        self.profile_path = Path(settings.profile_path)
        self._data: Dict = {"name": "", "notes": []}
        self.load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self):
        """Loads profile from disk. Silent no-op if file doesn't exist."""
        if self.profile_path.exists():
            try:
                with open(self.profile_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                # Ensure keys exist for older profiles
                self._data.setdefault("name", "")
                self._data.setdefault("notes", [])
            except Exception:
                self._data = {"name": "", "notes": []}

    def save(self):
        """Persists profile to disk."""
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.profile_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Name
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return self._data.get("name", "").strip()

    def set_name(self, name: str):
        """Sets the user's preferred name and saves."""
        self._data["name"] = name.strip()
        self.save()

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    @property
    def notes(self) -> List[Dict]:
        return self._data.get("notes", [])

    def add_note(self, text: str) -> int:
        """Adds a note and returns its new ID."""
        notes = self._data.setdefault("notes", [])
        # Auto-increment ID
        next_id = max((n["id"] for n in notes), default=0) + 1
        notes.append({
            "id": next_id,
            "text": text.strip(),
            "created": datetime.now().strftime("%Y-%m-%d"),
        })
        self.save()
        return next_id

    def delete_note(self, note_id: int) -> bool:
        """Deletes a note by ID. Returns True if found and deleted."""
        notes = self._data.get("notes", [])
        original_len = len(notes)
        self._data["notes"] = [n for n in notes if n["id"] != note_id]
        if len(self._data["notes"]) < original_len:
            self.save()
            return True
        return False

    def list_notes(self) -> List[Dict]:
        """Returns all notes."""
        return list(self._data.get("notes", []))

    # ------------------------------------------------------------------
    # System prompt injection
    # ------------------------------------------------------------------

    def build_context_block(self) -> str:
        """Builds a string block to prepend to the system prompt.

        Returns an empty string if neither name nor notes are set.
        """
        parts = []

        if self.name:
            parts.append(f"The user's preferred name is {self.name}. Address them by name naturally.")

        notes = self.list_notes()
        if notes:
            note_lines = "\n".join(f"  - {n['text']}" for n in notes)
            parts.append(
                f"Things to remember about the user:\n{note_lines}\n"
                "Reference these naturally when relevant — do not list them all at once."
            )

        if not parts:
            return ""

        return "\n\n[User Profile]\n" + "\n\n".join(parts)

    def has_profile(self) -> bool:
        """Returns True if the user has set a name or any notes."""
        return bool(self.name or self.list_notes())
