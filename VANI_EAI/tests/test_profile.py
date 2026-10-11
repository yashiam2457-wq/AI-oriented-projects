import pytest
from pathlib import Path
from modules.config.settings import Settings
from modules.profile.profile_manager import ProfileManager

def _make_settings(tmp_path):
    return Settings(
        profile_path=str(tmp_path / "user_profile.json")
    )

def test_profile_empty_on_init(tmp_path):
    settings = _make_settings(tmp_path)
    pm = ProfileManager(settings)
    assert pm.name == ""
    assert pm.notes == []
    assert pm.has_profile() is False
    assert pm.build_context_block() == ""

def test_set_and_load_preferred_name(tmp_path):
    settings = _make_settings(tmp_path)
    pm = ProfileManager(settings)
    
    pm.set_name("Taylor")
    assert pm.name == "Taylor"
    assert pm.has_profile() is True
    
    # Reload and check persistence
    pm_reload = ProfileManager(settings)
    assert pm_reload.name == "Taylor"

def test_notes_crud_operations(tmp_path):
    settings = _make_settings(tmp_path)
    pm = ProfileManager(settings)
    
    note_id_1 = pm.add_note("I need to study math.")
    note_id_2 = pm.add_note("I prefer drinking decaf tea.")
    
    assert note_id_1 == 1
    assert note_id_2 == 2
    assert len(pm.notes) == 2
    
    # Verify load notes persistence
    pm_reload = ProfileManager(settings)
    assert len(pm_reload.notes) == 2
    assert pm_reload.notes[0]["text"] == "I need to study math."
    
    # Test delete note
    assert pm.delete_note(1) is True
    assert len(pm.notes) == 1
    assert pm.notes[0]["id"] == 2
    
    # Delete non-existent note
    assert pm.delete_note(99) is False

def test_build_context_block(tmp_path):
    settings = _make_settings(tmp_path)
    pm = ProfileManager(settings)
    
    pm.set_name("Sam")
    pm.add_note("I dislike bright lighting.")
    
    block = pm.build_context_block()
    assert "[User Profile]" in block
    assert "Sam" in block
    assert "dislike bright lighting" in block
