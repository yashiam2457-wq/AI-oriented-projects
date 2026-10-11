import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from modules.config.settings import Settings

_MOOD_COLORS = {
    "Joy":     "green",
    "Anxiety": "yellow",
    "Sadness": "magenta",
    "Anger":   "red",
    "Neutral": "blue",
}

_STOP_WORDS = {
    "i", "me", "my", "myself", "we", "our", "you", "your", "he", "she", "it",
    "they", "them", "what", "which", "who", "this", "that", "these", "those",
    "am", "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should", "may",
    "might", "must", "shall", "can", "need", "a", "an", "the", "and", "but",
    "or", "nor", "for", "yet", "so", "at", "by", "from", "in", "of", "on",
    "to", "with", "not", "no", "just", "also", "too", "very", "really",
    "feel", "feeling", "think", "know", "get", "go", "like", "want", "make",
    "said", "say", "right", "well", "actually", "dont", "cant", "im", "ive",
    "its", "id", "ill", "little", "lot", "bit", "thing", "things", "way",
    "time", "day", "okay", "yes", "yeah", "nope", "okay",
}


class AnalyticsDashboard:
    """Computes and renders lifetime analytics from saved session and journal files."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.sessions_dir = Path(settings.memory_sessions_dir)
        self.journals_dir = Path(settings.journal_dir)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_sessions(self) -> List[Dict]:
        if not self.sessions_dir.exists():
            return []
        sessions = []
        for f in sorted(self.sessions_dir.glob("session_*.json")):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                sessions.append(data)
            except Exception:
                pass
        return sessions

    # ------------------------------------------------------------------
    # Metric computation
    # ------------------------------------------------------------------

    def _compute_metrics(self, sessions: List[Dict]) -> Dict:
        total_sessions = len(sessions)
        total_turns = 0
        all_moods: List[str] = []
        persona_counts: Counter = Counter()
        day_counts: Counter = Counter()
        all_user_words: List[str] = []
        longest_session = 0
        longest_session_date = "N/A"

        for s in sessions:
            history = s.get("history", [])
            persona = s.get("persona", "VANI")
            timestamp_str = s.get("timestamp", "")

            # Count only user+assistant turns (not system)
            conversation = [m for m in history if m.get("role") != "system"]
            turn_count = len([m for m in conversation if m.get("role") == "user"])
            total_turns += turn_count

            if turn_count > longest_session:
                longest_session = turn_count
                longest_session_date = timestamp_str[:10] if timestamp_str else "N/A"

            # Persona
            persona_counts[persona] += 1

            # Day of week
            try:
                dt = datetime.fromisoformat(timestamp_str)
                day_counts[dt.strftime("%A")] += 1
            except Exception:
                pass

            # User words for topic extraction
            for m in history:
                if m.get("role") == "user":
                    words = re.findall(r"[a-z]{3,}", m["content"].lower())
                    all_user_words.extend(w for w in words if w not in _STOP_WORDS)

        # Top topics
        top_topics = [w for w, _ in Counter(all_user_words).most_common(10)]

        return {
            "total_sessions": total_sessions,
            "total_turns": total_turns,
            "all_moods": all_moods,
            "persona_counts": dict(persona_counts),
            "day_counts": dict(day_counts),
            "top_topics": top_topics,
            "longest_session": longest_session,
            "longest_session_date": longest_session_date,
        }

    def _compute_mood_from_journals(self) -> Tuple[Counter, List[str]]:
        """Reads mood data from journal files since sessions don't store mood directly."""
        mood_counter: Counter = Counter()
        recent_moods: List[str] = []

        if not self.journals_dir.exists():
            return mood_counter, recent_moods

        for f in sorted(self.journals_dir.glob("journal_*.md"), reverse=True):
            try:
                text = f.read_text(encoding="utf-8")
                match = re.search(r"Dominant mood:\s*\*\*(.+?)\*\*", text)
                if match:
                    mood = match.group(1).strip()
                    mood_counter[mood] += 1
                    if len(recent_moods) < 8:
                        recent_moods.insert(0, mood)
            except Exception:
                pass

        return mood_counter, recent_moods

    # ------------------------------------------------------------------
    # ASCII bar chart helper
    # ------------------------------------------------------------------

    @staticmethod
    def _bar(value: int, max_val: int, width: int = 20) -> str:
        if max_val == 0:
            return "░" * width
        filled = int(width * value / max_val)
        return "█" * filled + "░" * (width - filled)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render_dashboard(self) -> Panel:
        """Builds and returns a rich Panel with the full analytics dashboard."""
        sessions = self._load_sessions()
        mood_counter, recent_moods = self._compute_mood_from_journals()
        metrics = self._compute_metrics(sessions)

        # ── Header ──────────────────────────────────────────────────────
        header = Text()
        header.append("VANI Lifetime Analytics\n", style="bold magenta")
        header.append(
            f"  {metrics['total_sessions']} sessions  •  "
            f"{metrics['total_turns']} total turns  •  "
            f"Longest session: {metrics['longest_session']} turns ({metrics['longest_session_date']})\n",
            style="cyan",
        )

        # ── Mood distribution table ──────────────────────────────────────
        mood_table = Table(title="Mood Distribution", show_header=True,
                           header_style="bold yellow", box=None, padding=(0, 1))
        mood_table.add_column("Mood", style="bold", no_wrap=True)
        mood_table.add_column("Bar", no_wrap=True)
        mood_table.add_column("Count", justify="right")

        total_mood = sum(mood_counter.values()) or 1
        max_mood = max(mood_counter.values(), default=1)
        for mood in ["Joy", "Anxiety", "Sadness", "Anger", "Neutral"]:
            count = mood_counter.get(mood, 0)
            color = _MOOD_COLORS.get(mood, "white")
            bar = self._bar(count, max_mood)
            mood_table.add_row(
                Text(mood, style=f"bold {color}"),
                Text(bar, style=color),
                f"{count}  ({int(100*count/total_mood)}%)",
            )

        # ── Mood trend ───────────────────────────────────────────────────
        trend_text = Text("\nRecent Mood Trend: ", style="bold white")
        for i, mood in enumerate(recent_moods):
            color = _MOOD_COLORS.get(mood, "white")
            trend_text.append(mood, style=f"bold {color}")
            if i < len(recent_moods) - 1:
                trend_text.append(" → ", style="dim white")

        # ── Persona usage ────────────────────────────────────────────────
        persona_table = Table(title="Persona Usage", show_header=True,
                              header_style="bold cyan", box=None, padding=(0, 1))
        persona_table.add_column("Persona", style="bold cyan")
        persona_table.add_column("Bar", no_wrap=True)
        persona_table.add_column("Sessions", justify="right")
        max_persona = max(metrics["persona_counts"].values(), default=1)
        for name, count in sorted(metrics["persona_counts"].items(),
                                   key=lambda x: x[1], reverse=True):
            bar = self._bar(count, max_persona)
            persona_table.add_row(name, Text(bar, style="cyan"), str(count))

        # ── Day of week ──────────────────────────────────────────────────
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                     "Friday", "Saturday", "Sunday"]
        day_table = Table(title="Most Active Days", show_header=True,
                          header_style="bold green", box=None, padding=(0, 1))
        day_table.add_column("Day", style="bold green")
        day_table.add_column("Bar", no_wrap=True)
        day_table.add_column("Sessions", justify="right")
        max_day = max(metrics["day_counts"].values(), default=1)
        for day in day_order:
            count = metrics["day_counts"].get(day, 0)
            if count > 0:
                bar = self._bar(count, max_day)
                day_table.add_row(day, Text(bar, style="green"), str(count))

        # ── Top topics ───────────────────────────────────────────────────
        topics_text = Text("\nFavourite Topics: ", style="bold white")
        if metrics["top_topics"]:
            for i, topic in enumerate(metrics["top_topics"]):
                topics_text.append(f"#{topic}", style="bold magenta")
                if i < len(metrics["top_topics"]) - 1:
                    topics_text.append("  ", style="white")
        else:
            topics_text.append("No data yet.", style="dim white")

        # ── No data guard ────────────────────────────────────────────────
        if metrics["total_sessions"] == 0:
            return Panel(
                Text("No session data found yet. Start a conversation and come back!", style="italic white"),
                title="[bold magenta]VANI Analytics[/bold magenta]",
                border_style="magenta",
            )

        group = Group(
            header,
            mood_table,
            trend_text,
            Text(""),
            persona_table,
            Text(""),
            day_table,
            topics_text,
        )

        return Panel(
            group,
            title="[bold magenta]📊 VANI Lifetime Analytics[/bold magenta]",
            border_style="magenta",
            expand=False,
        )
