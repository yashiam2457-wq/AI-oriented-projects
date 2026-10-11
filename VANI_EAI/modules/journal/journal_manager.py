import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from modules.config.settings import Settings

# Common stop-words to skip when extracting key topics
_STOP_WORDS = {
    "i", "me", "my", "myself", "we", "our", "you", "your", "he", "she", "it",
    "they", "them", "what", "which", "who", "this", "that", "these", "those",
    "am", "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should", "may",
    "might", "must", "shall", "can", "need", "dare", "ought", "used",
    "a", "an", "the", "and", "but", "or", "nor", "for", "yet", "so",
    "at", "by", "for", "from", "in", "into", "of", "on", "to", "up",
    "with", "about", "after", "before", "between", "during", "through",
    "not", "no", "just", "also", "too", "very", "really", "feel", "feeling",
    "think", "know", "get", "got", "go", "going", "like", "want", "make",
    "said", "say", "tell", "told", "right", "well", "actually", "kind",
    "little", "lot", "bit", "thing", "things", "way", "time", "day",
    "dont", "cant", "im", "ive", "its", "id", "ill",
}

_SESSION_CLOSING = "Another session with VANI wrapped up. Small conversations, over time, add up."


class JournalManager:
    """Generates and manages session journal entries."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.journal_dir = Path(settings.journal_dir)

    def _ensure_dir(self):
        self.journal_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Topic extraction
    # ------------------------------------------------------------------

    def _extract_topics(self, history: List[Dict[str, str]], top_n: int = 6) -> List[str]:
        """Extracts the most frequent meaningful words from user messages."""
        user_text = " ".join(
            m["content"] for m in history if m.get("role") == "user"
        )
        # Tokenise — letters only, lowercase
        words = re.findall(r"[a-z]{3,}", user_text.lower())
        filtered = [w for w in words if w not in _STOP_WORDS]
        if not filtered:
            return []
        most_common = Counter(filtered).most_common(top_n)
        return [w for w, _ in most_common]

    # ------------------------------------------------------------------
    # Entry generation
    # ------------------------------------------------------------------

    def generate_entry(
        self,
        history: List[Dict[str, str]],
        persona: str,
    ) -> str:
        """Builds a Markdown journal entry from session data."""
        now = datetime.now()
        date_str = now.strftime("%A, %d %B %Y")
        time_str = now.strftime("%H:%M")

        user_turns = [m for m in history if m.get("role") == "user"]
        total_turns = len(user_turns)

        topics = self._extract_topics(history)
        topics_str = ", ".join(f"**{t}**" for t in topics) if topics else "_no strong themes detected_"

        entry = f"""# VANI Journal Entry
**Date:** {date_str}  
**Time:** {time_str}  
**Persona:** {persona}  
**Conversation Turns:** {total_turns}

---

## Key Topics

The conversation touched on: {topics_str}

---

## Note

_{_SESSION_CLOSING}_

---
*Generated automatically by VANI at session end.*
"""
        return entry

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_entry(self, entry_text: str) -> Optional[Path]:
        """Saves a journal entry to the journals directory."""
        if not self.settings.journal_enabled:
            return None
        self._ensure_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.journal_dir / f"journal_{timestamp}.md"
        try:
            path.write_text(entry_text, encoding="utf-8")
            return path
        except Exception as e:
            return None

    def generate_and_save(
        self,
        history: List[Dict[str, str]],
        persona: str,
    ) -> Optional[Path]:
        """Convenience wrapper: generate + save in one call.
        
        Returns the saved file path, or None if disabled or nothing to write.
        """
        if not self.settings.journal_enabled:
            return None
        user_turns = [m for m in history if m.get("role") == "user"]
        if not user_turns:
            return None
        entry = self.generate_entry(history, persona)
        return self.save_entry(entry)

    # ------------------------------------------------------------------
    # Listing & reading
    # ------------------------------------------------------------------

    def _journal_files(self) -> List[Path]:
        if not self.journal_dir.exists():
            return []
        return sorted(self.journal_dir.glob("journal_*.md"), reverse=True)

    def list_entries(self) -> List[Dict]:
        """Returns metadata for all journal entries."""
        results = []
        for f in self._journal_files():
            try:
                text = f.read_text(encoding="utf-8")
                date_match    = re.search(r"\*\*Date:\*\*\s*(.+)", text)
                persona_match = re.search(r"\*\*Persona:\*\*\s*(.+)", text)
                turns_match   = re.search(r"\*\*Conversation Turns:\*\*\s*(\d+)", text)
                results.append({
                    "file":    f.name,
                    "date":    date_match.group(1).strip() if date_match else "Unknown",
                    "persona": persona_match.group(1).strip() if persona_match else "VANI",
                    "turns":   turns_match.group(1).strip() if turns_match else "?",
                })
            except Exception:
                pass
        return results

    def read_entry(self, index: int) -> Optional[str]:
        """Returns the raw markdown of a journal entry (1-based index, newest first)."""
        files = self._journal_files()
        if not files or index < 1 or index > len(files):
            return None
        try:
            return files[index - 1].read_text(encoding="utf-8")
        except Exception:
            return None
