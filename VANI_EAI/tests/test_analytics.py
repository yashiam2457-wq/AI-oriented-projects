import json
import pytest
from pathlib import Path
from datetime import datetime
from modules.config.settings import Settings
from modules.analytics.analytics import AnalyticsDashboard
from rich.panel import Panel


def _make_settings(tmp_path):
    return Settings(
        memory_sessions_dir=str(tmp_path / "sessions"),
        journal_dir=str(tmp_path / "journals"),
    )


def _write_session(sessions_dir: Path, persona: str, turns: int, timestamp: str):
    sessions_dir.mkdir(parents=True, exist_ok=True)
    history = [{"role": "system", "content": "Sys"}]
    for i in range(turns):
        history.append({"role": "user", "content": f"user message {i}"})
        history.append({"role": "assistant", "content": f"assistant reply {i}"})
    fname = sessions_dir / f"session_{timestamp}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}T12:00:00",
            "persona": persona,
            "history": history,
        }, f)


def _write_journal(journals_dir: Path, dominant_mood: str, timestamp: str):
    journals_dir.mkdir(parents=True, exist_ok=True)
    text = f"""# VANI Journal Entry
**Date:** Monday, 01 January 2025  
**Persona:** VANI  
**Conversation Turns:** 3

---

## Emotional Arc

Dominant mood: **{dominant_mood}**

---
"""
    (journals_dir / f"journal_{timestamp}.md").write_text(text, encoding="utf-8")


def test_dashboard_no_data(tmp_path):
    settings = _make_settings(tmp_path)
    dash = AnalyticsDashboard(settings)
    panel = dash.render_dashboard()
    assert isinstance(panel, Panel)


def test_dashboard_with_sessions(tmp_path):
    settings = _make_settings(tmp_path)
    sessions_dir = tmp_path / "sessions"

    _write_session(sessions_dir, "VANI", 5, "20250101_120000")
    _write_session(sessions_dir, "Aria", 3, "20250102_130000")
    _write_session(sessions_dir, "VANI", 8, "20250103_140000")

    dash = AnalyticsDashboard(settings)
    metrics = dash._compute_metrics(dash._load_sessions())

    assert metrics["total_sessions"] == 3
    assert metrics["total_turns"] == 16  # 5+3+8
    assert metrics["longest_session"] == 8
    assert metrics["persona_counts"]["VANI"] == 2
    assert metrics["persona_counts"]["Aria"] == 1


def test_dashboard_with_journals_mood(tmp_path):
    settings = _make_settings(tmp_path)
    journals_dir = tmp_path / "journals"

    _write_journal(journals_dir, "Joy", "20250101_120000")
    _write_journal(journals_dir, "Anxiety", "20250102_120000")
    _write_journal(journals_dir, "Joy", "20250103_120000")

    dash = AnalyticsDashboard(settings)
    mood_counter, recent_moods = dash._compute_mood_from_journals()

    assert mood_counter["Joy"] == 2
    assert mood_counter["Anxiety"] == 1
    assert "Joy" in recent_moods


def test_bar_chart_helper():
    bar = AnalyticsDashboard._bar(5, 10, width=10)
    assert len(bar) == 10
    assert bar.count("█") == 5
    assert bar.count("░") == 5


def test_bar_chart_zero_max():
    bar = AnalyticsDashboard._bar(0, 0, width=10)
    assert bar == "░" * 10


def test_render_dashboard_returns_panel(tmp_path):
    settings = _make_settings(tmp_path)
    sessions_dir = tmp_path / "sessions"
    journals_dir = tmp_path / "journals"

    _write_session(sessions_dir, "VANI", 4, "20250101_090000")
    _write_journal(journals_dir, "Neutral", "20250101_090100")

    dash = AnalyticsDashboard(settings)
    panel = dash.render_dashboard()
    assert isinstance(panel, Panel)
