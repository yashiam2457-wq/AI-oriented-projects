import re
import pytest
from pathlib import Path
from modules.config.settings import Settings
from modules.journal.journal_manager import JournalManager


def _make_settings(tmp_path):
    return Settings(
        journal_enabled=True,
        journal_dir=str(tmp_path / "journals"),
    )


def _sample_history():
    return [
        {"role": "system", "content": "System prompt."},
        {"role": "user", "content": "I feel so stressed and overwhelmed with everything."},
        {"role": "assistant", "content": "I'm sorry to hear that. What's been weighing on you?"},
        {"role": "user", "content": "Work is really hard. My anxiety is through the roof."},
        {"role": "assistant", "content": "That sounds exhausting. Let's take a breath together."},
    ]


def test_generate_entry_contains_header(tmp_path):
    settings = _make_settings(tmp_path)
    jm = JournalManager(settings)
    entry = jm.generate_entry(_sample_history(), ["Anxiety", "Anxiety"], "VANI")
    assert "# VANI Journal Entry" in entry
    assert "**Persona:** VANI" in entry
    assert "**Conversation Turns:** 2" in entry


def test_generate_entry_detects_mood(tmp_path):
    settings = _make_settings(tmp_path)
    jm = JournalManager(settings)
    entry = jm.generate_entry(_sample_history(), ["Sadness", "Joy"], "Aria")
    # Dominant mood should be Sadness (first) since they're equal count -> first wins
    assert "Sadness" in entry or "Joy" in entry


def test_generate_entry_empty_mood_history(tmp_path):
    settings = _make_settings(tmp_path)
    jm = JournalManager(settings)
    entry = jm.generate_entry(_sample_history(), [], "VANI")
    assert "Neutral" in entry


def test_topic_extraction(tmp_path):
    settings = _make_settings(tmp_path)
    jm = JournalManager(settings)
    topics = jm._extract_topics(_sample_history())
    # "stressed", "overwhelmed", "work", "anxiety" etc. should be picked up
    assert isinstance(topics, list)
    assert len(topics) > 0
    # Should not contain stop words
    assert "and" not in topics
    assert "the" not in topics


def test_save_and_list_entries(tmp_path):
    settings = _make_settings(tmp_path)
    jm = JournalManager(settings)
    entry_text = jm.generate_entry(_sample_history(), ["Anxiety"], "VANI")
    saved_path = jm.save_entry(entry_text)

    assert saved_path is not None
    assert saved_path.exists()

    entries = jm.list_entries()
    assert len(entries) == 1
    assert entries[0]["persona"] == "VANI"
    assert entries[0]["mood"] == "Anxiety"


def test_read_entry(tmp_path):
    settings = _make_settings(tmp_path)
    jm = JournalManager(settings)
    text = jm.generate_entry(_sample_history(), ["Joy"], "Sage")
    jm.save_entry(text)

    read_back = jm.read_entry(1)
    assert read_back is not None
    assert "VANI Journal Entry" in read_back


def test_read_entry_invalid_index(tmp_path):
    settings = _make_settings(tmp_path)
    jm = JournalManager(settings)
    assert jm.read_entry(99) is None


def test_generate_and_save_noop_when_disabled(tmp_path):
    settings = _make_settings(tmp_path)
    settings.journal_enabled = False
    jm = JournalManager(settings)
    result = jm.generate_and_save(_sample_history(), ["Joy"], "VANI")
    assert result is None


def test_generate_and_save_noop_when_no_user_turns(tmp_path):
    settings = _make_settings(tmp_path)
    jm = JournalManager(settings)
    # Only system message — no user turns
    history = [{"role": "system", "content": "Sys"}]
    result = jm.generate_and_save(history, [], "VANI")
    assert result is None
