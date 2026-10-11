import json
import os
from pathlib import Path
from pydantic import BaseModel, Field, field_validator

class Settings(BaseModel):
    llm_mode: str = Field(default="server", description="LLM mode: 'server' or 'local'")
    local_model_path: str = Field(default="models/mistral-7b-instruct-v0.2.Q4_0.gguf")
    server_base_url: str = Field(default="http://localhost:1234/v1")
    server_api_key: str = Field(default="lm-studio")
    model_name: str = Field(default="mistral-7b-instruct")
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=512)
    n_ctx: int = Field(default=4096)
    n_gpu_layers: int = Field(default=-1)

    # TTS — Kokoro neural voice (pyttsx3 as fallback)
    tts_enabled: bool = Field(default=True)
    kokoro_voice: str = Field(default="af_heart", description="Kokoro voice ID (e.g. af_heart, am_adam, bf_emma)")
    kokoro_speed: float = Field(default=1.0, description="Kokoro speech speed multiplier (0.5–2.0)")

    # STT — faster-whisper
    voice_input_enabled: bool = Field(default=False)
    whisper_model: str = Field(default="base", description="Whisper model size: 'tiny' (fastest) or 'base' (recommended)")
    whisper_language: str = Field(default="en", description="Whisper language code (e.g. 'en')")

    @field_validator("whisper_model")
    @classmethod
    def _validate_whisper_model(cls, v: str) -> str:
        allowed = {"tiny", "base"}
        if v not in allowed:
            print(f"[Settings] whisper_model '{v}' is not supported. Falling back to 'base'. Allowed: {allowed}")
            return "base"
        return v
    stt_silence_threshold: float = Field(default=300.0, description="RMS amplitude below which audio is treated as silence")
    stt_silence_duration: float = Field(default=1.5, description="Seconds of silence before recording stops")

    # Memory
    memory_enabled: bool = Field(default=True)
    memory_sessions_dir: str = Field(default="sessions")
    memory_max_turns: int = Field(default=30)

    # Persona (single, fixed)
    active_persona: str = Field(default="VANI")

    # Journal
    journal_enabled: bool = Field(default=True)
    journal_dir: str = Field(default="journals")

    # Profile
    profile_path: str = Field(default="user_profile.json")

    # System prompt (set from persona on startup)
    system_prompt: str = Field(default="You are VANI, a close friend of the user. Talk naturally and honestly.")

def load_settings(config_path: Path = Path("config.json")) -> Settings:
    """Loads configuration settings from config.json, falling back to defaults if not found."""
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Settings(**data)
        except Exception as e:
            print(f"Warning: Failed to load config file: {e}. Using default settings.")
    return Settings()
