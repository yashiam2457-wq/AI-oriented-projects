import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from modules.config.settings import Settings
from modules.memory.memory_manager import MemoryManager


def _make_settings(tmp_path):
    return Settings(
        memory_enabled=True,
        memory_sessions_dir=str(tmp_path / "sessions"),
        memory_max_turns=6,
    )


def _sample_history():
    return [
        {"role": "system", "content": "System prompt."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
        {"role": "assistant", "content": "I'm doing well, thanks."},
    ]


def test_save_and_load_session(tmp_path):
    settings = _make_settings(tmp_path)
    mm = MemoryManager(settings)
    history = _sample_history()

    mm.save_session(history, persona="VANI")

    sessions = mm.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["persona"] == "VANI"
    assert sessions[0]["turns"] == 4  # excluding system message


def test_load_recent_context_excludes_system(tmp_path):
    settings = _make_settings(tmp_path)
    mm = MemoryManager(settings)
    mm.save_session(_sample_history(), persona="VANI")

    context = mm.load_recent_context()
    assert all(m["role"] != "system" for m in context)
    assert len(context) == 4


def test_load_by_index(tmp_path):
    settings = _make_settings(tmp_path)
    mm = MemoryManager(settings)
    mm.save_session(_sample_history(), persona="VANI")

    turns = mm.load_session_by_index(1)
    assert len(turns) == 4
    assert turns[0]["role"] == "user"


def test_load_invalid_index_returns_empty(tmp_path):
    settings = _make_settings(tmp_path)
    mm = MemoryManager(settings)
    assert mm.load_session_by_index(99) == []


def test_compress_history_trims_old_turns(tmp_path):
    settings = _make_settings(tmp_path)
    mm = MemoryManager(settings)

    # Build a history exceeding max_turns (6)
    history = [{"role": "system", "content": "Sys"}]
    for i in range(10):
        history.append({"role": "user", "content": f"Message {i}"})
        history.append({"role": "assistant", "content": f"Reply {i}"})

    compressed = mm.compress_history(history)

    conversation_turns = [m for m in compressed if m["role"] != "system"]
    # Should have: 2 injected summary msgs + last 6 turns
    assert len(conversation_turns) == 8  # 2 summary + 6 recent

    # First injected message should contain summary prefix
    assert MemoryManager.SUMMARY_PREFIX in conversation_turns[0]["content"]


def test_memory_disabled_returns_empty(tmp_path):
    settings = _make_settings(tmp_path)
    settings.memory_enabled = False
    mm = MemoryManager(settings)
    assert mm.load_recent_context() == []

    # save should silently no-op
    mm.save_session(_sample_history())
    assert mm.list_sessions() == []
