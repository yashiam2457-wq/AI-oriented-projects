"""
checkin_manager.py — Phase 9: Daily Check-in Mode

Guides the user through a structured 5-step wellbeing check-in and
saves the result to a timestamped JSON file.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from modules.config.settings import Settings

_MOOD_KEYWORDS = {
    "great":   "Joy",
    "good":    "Joy",
    "happy":   "Joy",
    "excited": "Joy",
    "calm":    "Joy",
    "fine":    "Neutral",
    "okay":    "Neutral",
    "ok":      "Neutral",
    "neutral": "Neutral",
    "meh":     "Neutral",
    "tired":   "Sadness",
    "sad":     "Sadness",
    "low":     "Sadness",
    "down":    "Sadness",
    "lonely":  "Sadness",
    "depressed": "Sadness",
    "anxious": "Anxiety",
    "worried": "Anxiety",
    "stressed": "Anxiety",
    "nervous": "Anxiety",
    "scared":  "Anxiety",
    "angry":   "Anger",
    "mad":     "Anger",
    "annoyed": "Anger",
    "frustrated": "Anger",
}

_REFLECTIONS = {
    "Joy": (
        "That warmth you're carrying right now is real and worth savouring. "
        "Let it be a gentle anchor throughout your day."
    ),
    "Neutral": (
        "A steady state is valuable. Not every day needs to sparkle — "
        "groundedness has its own quiet strength."
    ),
    "Sadness": (
        "It takes honesty to name sadness. You're not broken — you're feeling, and that matters. "
        "Be gentle with yourself today."
    ),
    "Anxiety": (
        "Anxiety often means something matters to you. "
        "Take three slow breaths before your next step — you don't have to solve everything at once."
    ),
    "Anger": (
        "Anger is a signal. Let yourself feel it without acting from it. "
        "What underneath it might need attention?"
    ),
}


def _detect_mood(text: str) -> str:
    """Detects mood from free-text answer using keyword matching."""
    lower = text.lower()
    for word, mood in _MOOD_KEYWORDS.items():
        if word in lower:
            return mood
    return "Neutral"


class CheckinManager:
    """Manages daily guided check-in sessions."""

    STEPS = [
        ("How are you feeling today?",
         "Take a moment — what word or phrase describes your state right now?"),
        ("What's one thing on your mind right now?",
         "It can be anything — a worry, a plan, a thought that keeps returning."),
        ("What's one thing you're grateful for today?",
         "It doesn't have to be big. Even the smallest things count."),
        ("Is there anything you'd like to let go of?",
         "Something you've been carrying that you're ready to release. (Press Enter to skip)"),
    ]

    def __init__(self, settings: Settings):
        self.settings = settings
        self.checkin_dir = Path(settings.checkin_dir)

    def _ensure_dir(self):
        self.checkin_dir.mkdir(parents=True, exist_ok=True)

    def run_checkin(self, console: Console, mood_tracker=None) -> Optional[Dict]:
        """Runs the interactive 5-step check-in. Returns the saved data dict."""
        if not self.settings.checkin_enabled:
            console.print("[yellow]Check-in is disabled in settings.[/yellow]")
            return None

        console.print(
            Panel(
                Text(
                    "Daily Check-in\n\n"
                    "Take a few moments just for yourself.\n"
                    "There are no right or wrong answers here.",
                    style="italic white",
                ),
                title="[bold magenta]✨ VANI Check-in[/bold magenta]",
                border_style="magenta",
                expand=False,
            )
        )

        answers = {}
        detected_mood = "Neutral"

        for i, (question, hint) in enumerate(self.STEPS, 1):
            console.print(f"\n[bold cyan]Step {i}/4[/bold cyan]  [yellow]{question}[/yellow]")
            console.print(f"[dim italic]{hint}[/dim italic]")

            default = "" if i == 4 else None  # Step 4 is skippable
            if default is not None:
                answer = Prompt.ask("[green]Your answer (Enter to skip)[/green]", default="").strip()
            else:
                answer = Prompt.ask("[green]Your answer[/green]").strip()

            answers[f"step_{i}"] = answer

            # Detect mood from step 1 answer
            if i == 1 and answer:
                detected_mood = _detect_mood(answer)
                if mood_tracker:
                    mood_tracker.history.append(detected_mood)

        # Generate VANI reflection
        reflection = _REFLECTIONS.get(detected_mood, _REFLECTIONS["Neutral"])

        console.print(
            Panel(
                Text(f"💬 {reflection}", style="italic magenta"),
                title=f"[bold green]VANI's Reflection — Mood: {detected_mood}[/bold green]",
                border_style="green",
                expand=False,
            )
        )

        data = {
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "mood": detected_mood,
            "answers": answers,
            "reflection": reflection,
        }

        self.save_checkin(data)
        return data

    def save_checkin(self, data: Dict):
        """Saves a check-in to the checkins directory."""
        self._ensure_dir()
        date_str = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        path = self.checkin_dir / f"checkin_{date_str}.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            pass

    def _checkin_files(self) -> List[Path]:
        if not self.checkin_dir.exists():
            return []
        return sorted(self.checkin_dir.glob("checkin_*.json"), reverse=True)

    def list_checkins(self) -> List[Dict]:
        """Returns metadata for all saved check-ins."""
        results = []
        for f in self._checkin_files():
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                results.append({
                    "file": f.name,
                    "date": data.get("date", "Unknown"),
                    "mood": data.get("mood", "Unknown"),
                    "feeling": data.get("answers", {}).get("step_1", ""),
                })
            except Exception:
                pass
        return results

    def read_checkin(self, index: int) -> Optional[Dict]:
        """Returns check-in data at the given 1-based index (newest first)."""
        files = self._checkin_files()
        if not files or index < 1 or index > len(files):
            return None
        try:
            with open(files[index - 1], "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
