import pytest
from modules.config.settings import Settings
from modules.persona.persona_manager import PersonaManager


def test_persona_list_has_four_entries():
    pm = PersonaManager()
    assert len(pm.list_personas()) == 4


def test_persona_names():
    pm = PersonaManager()
    names = pm.names
    assert "VANI" in names
    assert "Aria" in names
    assert "Sage" in names
    assert "Nova" in names


def test_get_persona_case_insensitive():
    pm = PersonaManager()
    assert pm.get("vani") is not None
    assert pm.get("ARIA") is not None
    assert pm.get("unknown") is None


def test_apply_persona_updates_settings():
    pm = PersonaManager()
    settings = Settings()

    result = pm.apply("Aria", settings)
    assert result is True
    assert settings.active_persona == "Aria"
    assert "motivational" in settings.system_prompt.lower() or "coach" in settings.system_prompt.lower()
    assert settings.tts_rate == 195


def test_apply_invalid_persona_returns_false():
    pm = PersonaManager()
    settings = Settings()
    original_prompt = settings.system_prompt

    result = pm.apply("Gandalf", settings)
    assert result is False
    assert settings.system_prompt == original_prompt  # unchanged


def test_apply_sage_slows_tts():
    pm = PersonaManager()
    settings = Settings()
    pm.apply("Sage", settings)
    assert settings.tts_rate < 170  # Sage is slower than default


def test_apply_nova_increases_tts():
    pm = PersonaManager()
    settings = Settings()
    pm.apply("Nova", settings)
    assert settings.tts_rate > 190  # Nova is faster than default
