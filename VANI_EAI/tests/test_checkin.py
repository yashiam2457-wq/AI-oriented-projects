import json
import pytest
from pathlib import Path
from modules.config.settings import Settings
from modules.checkin.checkin_manager import CheckinManager, _detect_mood

def _make_settings(tmp_path):
    return Settings(
        checkin_enabled=True,
        checkin_dir=str(tmp_path / "checkins")
    )

def test_detect_mood_from_keywords():
    assert _detect_mood("I am feeling great today!") == "Joy"
    assert _detect_mood("I feel extremely stressed out.") == "Anxiety"
    assert _detect_mood("I am really sad and down.") == "Sadness"
    assert _detect_mood("This is making me angry and frustrated.") == "Anger"
    assert _detect_mood("It was okay, nothing special.") == "Neutral"
    assert _detect_mood("Random text without keywords") == "Neutral"

def test_save_and_list_checkins(tmp_path):
    settings = _make_settings(tmp_path)
    cm = CheckinManager(settings)

    checkin_data = {
        "timestamp": "2025-01-01T12:00:00",
        "date": "2025-01-01",
        "mood": "Joy",
        "answers": {
            "step_1": "I feel happy",
            "step_2": "Nothing much",
            "step_3": "Friendship",
            "step_4": ""
        },
        "reflection": "That warmth you're carrying right now is real."
    }

    cm.save_checkin(checkin_data)

    checkins = cm.list_checkins()
    assert len(checkins) == 1
    assert checkins[0]["mood"] == "Joy"
    assert checkins[0]["date"] == "2025-01-01"
    assert checkins[0]["feeling"] == "I feel happy"

def test_read_checkin_by_index(tmp_path):
    settings = _make_settings(tmp_path)
    cm = CheckinManager(settings)

    checkin_data = {
        "timestamp": "2025-01-01T12:00:00",
        "date": "2025-01-01",
        "mood": "Sadness",
        "answers": {"step_1": "low", "step_2": "", "step_3": "", "step_4": ""},
        "reflection": "Reflection test."
    }
    cm.save_checkin(checkin_data)

    retrieved = cm.read_checkin(1)
    assert retrieved is not None
    assert retrieved["mood"] == "Sadness"
    assert retrieved["answers"]["step_1"] == "low"

def test_read_checkin_invalid_index(tmp_path):
    settings = _make_settings(tmp_path)
    cm = CheckinManager(settings)
    assert cm.read_checkin(99) is None
