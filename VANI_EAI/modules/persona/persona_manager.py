import json
from pathlib import Path
from typing import Dict, Optional

# Persona is loaded from the JSON file next to this module
_PERSONAS_FILE = Path(__file__).parent / "personas.json"


class PersonaManager:
    """Manages VANI's single personality profile — loading and applying."""

    def __init__(self):
        self._persona: Dict = self._load_persona()

    def _load_persona(self) -> Dict:
        try:
            with open(_PERSONAS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Accept both a list (backwards compat) or a single dict
            if isinstance(data, list) and data:
                return data[0]
            if isinstance(data, dict):
                return data
        except Exception as e:
            print(f"[PersonaManager] Warning: could not load personas.json: {e}")
        # Minimal fallback
        return {
            "name": "VANI",
            "description": "Warm, candid AI friend",
            "system_prompt": (
                "You are VANI, a close friend of the user. Talk naturally and honestly, "
                "the way a real person would. No scripted phrases, no therapist-speak."
            ),
            "tts_speed": 1.0,
            "tts_voice": "af_heart",
        }

    @property
    def name(self) -> str:
        return self._persona.get("name", "VANI")

    def get(self) -> Dict:
        """Returns the single persona dict."""
        return self._persona

    def apply(self, settings) -> None:
        """Applies the persona's system_prompt and TTS settings to the Settings object."""
        settings.active_persona = self._persona.get("name", "VANI")
        settings.system_prompt = self._persona.get("system_prompt", settings.system_prompt)
        settings.kokoro_voice = self._persona.get("tts_voice", settings.kokoro_voice)
        settings.kokoro_speed = float(self._persona.get("tts_speed", settings.kokoro_speed))
