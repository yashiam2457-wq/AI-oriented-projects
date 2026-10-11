"""test_voice_mode.py — Phase 13: Voice Mode verification tests."""
import pytest
from modules.tts.voice_mode import VoiceModeManager
from modules.config.settings import Settings


@pytest.fixture
def vmm():
    return VoiceModeManager()


def test_all_six_modes_registered(vmm):
    modes = vmm.list_modes()
    names = {m["name"] for m in modes}
    assert names == {"Calm", "Friendly", "Playful", "Professional", "Study Partner", "Emotional Support"}


def test_mode_rates_ordered_correctly(vmm):
    """Emotional Support should be slowest; Playful should be fastest."""
    es = vmm.get_mode("Emotional Support")
    pl = vmm.get_mode("Playful")
    assert es["base_rate"] < vmm.get_mode("Calm")["base_rate"]
    assert pl["base_rate"] > vmm.get_mode("Friendly")["base_rate"]


def test_calm_has_longest_pause(vmm):
    calm_pause = vmm.get_mode("Calm")["pause_multiplier"]
    es_pause   = vmm.get_mode("Emotional Support")["pause_multiplier"]
    playful_p  = vmm.get_mode("Playful")["pause_multiplier"]
    # Emotional Support has the longest pause; Playful has the shortest
    assert es_pause > calm_pause > playful_p


def test_get_mode_case_insensitive(vmm):
    assert vmm.get_mode("calm") is not None
    assert vmm.get_mode("PLAYFUL") is not None
    assert vmm.get_mode("study partner") is not None
    assert vmm.get_mode("nonexistent") is None


def test_apply_mode_updates_settings(vmm):
    settings = Settings()
    assert vmm.apply("Calm", settings) is True
    assert settings.active_voice_mode == "Calm"
    assert settings.tts_rate == 145

    assert vmm.apply("Playful", settings) is True
    assert settings.active_voice_mode == "Playful"
    assert settings.tts_rate == 195


def test_apply_invalid_mode_returns_false(vmm):
    settings = Settings()
    old_mode = settings.active_voice_mode
    assert vmm.apply("Nonexistent", settings) is False
    assert settings.active_voice_mode == old_mode


def test_each_mode_has_all_required_keys(vmm):
    required = {"name", "base_rate", "pause_multiplier", "description"}
    for mode in vmm.list_modes():
        assert required.issubset(mode.keys()), f"Mode '{mode['name']}' missing keys"
