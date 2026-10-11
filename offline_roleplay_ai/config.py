"""
Configuration settings for Offline Roleplay AI Framework.
Handles LM Studio settings, paths, memory limits, and roleplay modes.
"""

import os
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field

BASE_DIR = Path(__file__).resolve().parent

class RoleplayMode(str, Enum):
    SINGLE_CHARACTER = "single_character"
    MULTI_CHARACTER = "multi_character"
    NARRATOR_ONLY = "narrator_only"
    CHARACTER_NARRATOR = "character_narrator"
    INTERACTIVE_STORY = "interactive_story"
    SANDBOX = "sandbox"

class StartupMode(str, Enum):
    AUTO_SCENE = "auto_scene"
    USER_FIRST = "user_first"

@dataclass
class LMStudioConfig:
    api_base_url: str = field(default_factory=lambda: os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1"))
    model_name: str = field(default_factory=lambda: os.getenv("LM_STUDIO_MODEL", "mistral-7b-instruct"))
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    max_tokens: int = 1024
    context_window_size: int = 8192
    timeout_seconds: int = 120
    stop_sequences: list[str] = field(default_factory=lambda: ["\nUser:", "\nHuman:", "<|im_end|>"])

@dataclass
class MemoryConfig:
    max_working_memory_items: int = 10
    max_recent_chat_turns: int = 20
    summary_trigger_tokens: int = 4000
    max_retrieved_memories: int = 5
    similarity_threshold: float = 0.35

@dataclass
class PathsConfig:
    base_dir: Path = BASE_DIR
    characters_dir: Path = BASE_DIR / "characters"
    sessions_dir: Path = BASE_DIR / "sessions"
    memories_dir: Path = BASE_DIR / "memories"
    summaries_dir: Path = BASE_DIR / "memories" / "summaries"
    chats_dir: Path = BASE_DIR / "memories" / "chats"
    db_path: Path = BASE_DIR / "memories" / "roleplay_data.db"
    logs_dir: Path = BASE_DIR / "logs"

    def ensure_directories(self) -> None:
        """Create all required directories if they do not exist."""
        for path in [
            self.characters_dir,
            self.sessions_dir,
            self.memories_dir,
            self.summaries_dir,
            self.chats_dir,
            self.db_path.parent,
            self.logs_dir
        ]:
            path.mkdir(parents=True, exist_ok=True)

@dataclass
class AppConfig:
    lm_studio: LMStudioConfig = field(default_factory=LMStudioConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)

    def __post_init__(self):
        self.paths.ensure_directories()

config = AppConfig()
