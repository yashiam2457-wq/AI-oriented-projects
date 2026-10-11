from typing import List, Dict, Optional

class VoiceModeManager:
    """Manages VANI TTS voice modes: Calm, Friendly, Playful, Professional, Study Partner, Emotional Support."""

    def __init__(self):
        # 6 distinct voice mode profiles
        self.modes = {
            "Calm": {
                "name": "Calm",
                "base_rate": 145,
                "pause_multiplier": 1.3,
                "description": "Soft, unhurried, peaceful and soothing speech pacing",
            },
            "Friendly": {
                "name": "Friendly",
                "base_rate": 175,
                "pause_multiplier": 1.0,
                "description": "Standard warm, natural, and friendly conversational tone",
            },
            "Playful": {
                "name": "Playful",
                "base_rate": 195,
                "pause_multiplier": 0.8,
                "description": "Faster, high-energy cadence with brief, active pauses",
            },
            "Professional": {
                "name": "Professional",
                "base_rate": 185,
                "pause_multiplier": 0.95,
                "description": "Crisp, clean, direct and structured vocal spacing",
            },
            "Study Partner": {
                "name": "Study Partner",
                "base_rate": 180,
                "pause_multiplier": 1.05,
                "description": "Focused, steady, encouraging and active paced guiding",
            },
            "Emotional Support": {
                "name": "Emotional Support",
                "base_rate": 135,
                "pause_multiplier": 1.45,
                "description": "Slow, deeply warm, empathetic pacing with comforting breathing breaks",
            },
        }

    def list_modes(self) -> List[Dict]:
        """Returns details of all registered voice modes."""
        return list(self.modes.values())

    def get_mode(self, name: str) -> Optional[Dict]:
        """Fetches voice mode settings case-insensitively by name."""
        for m_name, mode in self.modes.items():
            if m_name.lower() == name.strip().lower():
                return mode
        return None

    def apply(self, name: str, settings) -> bool:
        """Applies a voice mode to settings by name. Returns success status."""
        mode = self.get_mode(name)
        if not mode:
            return False
        settings.active_voice_mode = mode["name"]
        # Set default base rate based on voice mode settings
        settings.tts_rate = mode["base_rate"]
        return True
