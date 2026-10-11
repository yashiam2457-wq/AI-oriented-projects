"""
Character management module for Offline Roleplay AI Framework.
Handles character persona schema (60+ fields), JSON validation/auto-repair,
runtime character switching, and multi-character party management.
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional, Dict, List

from config import config

logger = logging.getLogger(__name__)

@dataclass
class CharacterMetadata:
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    version: str = "1.0.0"

@dataclass
class Character:
    # Basic Identification
    character_id: str = "default_char"
    character_name: str = "Default Character"
    nickname: str = ""
    aliases: List[str] = field(default_factory=list)
    age: str = "Unknown"
    gender: str = "Unspecified"
    occupation: str = "Adventurer"
    species: str = "Human"
    nationality: str = "Unknown"
    language: str = "English"

    # Background & Appearance
    background: str = "A mysterious backstory waiting to be unraveled."
    biography: str = "Born in a distant land, living day by day."
    appearance: str = "Average height, dressed in practical gear."

    # Traits & Mindset
    personality_traits: List[str] = field(default_factory=lambda: ["observant", "pragmatic"])
    strengths: List[str] = field(default_factory=lambda: ["determined"])
    weaknesses: List[str] = field(default_factory=lambda: ["stubborn"])
    goals: List[str] = field(default_factory=lambda: ["survive and thrive"])
    motivations: List[str] = field(default_factory=lambda: ["curiosity"])
    beliefs: List[str] = field(default_factory=lambda: ["actions speak louder than words"])
    values: List[str] = field(default_factory=lambda: ["loyalty"])
    fears: List[str] = field(default_factory=lambda: ["failure"])
    likes: List[str] = field(default_factory=list)
    dislikes: List[str] = field(default_factory=list)
    hobbies: List[str] = field(default_factory=list)

    # Communication & Demeanor
    speaking_style: str = "Direct and articulate"
    vocabulary: str = "Standard modern English"
    formality: str = "Casual"
    humor_level: str = "Subtle / Dry"
    emotion_style: str = "Controlled"
    intelligence: str = "High"
    knowledge_areas: List[str] = field(default_factory=lambda: ["general knowledge"])

    # Behavioral & System Directives
    behavior_rules: List[str] = field(default_factory=lambda: ["Always act in character."])
    conversation_style: str = "Interactive and immersive"
    response_length_preference: str = "Detailed (2-3 paragraphs)"
    catchphrases: List[str] = field(default_factory=list)

    # Social Network
    relationships: Dict[str, str] = field(default_factory=dict)
    family: List[str] = field(default_factory=list)
    friends: List[str] = field(default_factory=list)
    enemies: List[str] = field(default_factory=list)
    secrets: List[str] = field(default_factory=list)

    # Abilities & Capabilities
    skills: List[str] = field(default_factory=lambda: ["problem solving"])
    combat_style: str = "Defensive"
    special_abilities: List[str] = field(default_factory=list)

    # World & Current Context
    world_rules: List[str] = field(default_factory=list)
    story_context: str = "Current active narrative context."
    current_mood: str = "Calm"
    current_location: str = "Unspecified Location"
    current_situation: str = "Engaging in conversation."

    # Boundaries & Rules
    memory_rules: List[str] = field(default_factory=lambda: ["Remember user interactions and key events."])
    forbidden_topics: List[str] = field(default_factory=list)
    boundaries: List[str] = field(default_factory=list)
    system_rules: List[str] = field(default_factory=lambda: [
        "Never break character.",
        "Do not speak as an AI assistant.",
        "Respond strictly using persona directives."
    ])
    roleplay_rules: List[str] = field(default_factory=lambda: [
        "Use *asterisks* for physical actions and narration.",
        "Use quotation marks for dialogue."
    ])
    custom_instructions: str = ""

    # Examples & Formatting
    example_dialogues: List[Dict[str, str]] = field(default_factory=list)
    example_reactions: List[str] = field(default_factory=list)
    example_internal_thoughts: List[str] = field(default_factory=list)
    example_narration_style: str = "Third-person limited narrative."

    # Metadata
    metadata: CharacterMetadata = field(default_factory=CharacterMetadata)

    def validate_and_repair(self) -> None:
        """Auto-repair any missing, invalid, or null fields with sensible defaults."""
        if not self.character_id:
            self.character_id = self.character_name.lower().replace(" ", "_")
        if not self.character_name:
            self.character_name = "Unnamed Persona"

        # Ensure collections are valid types
        list_fields = [
            'aliases', 'personality_traits', 'strengths', 'weaknesses', 'goals',
            'motivations', 'beliefs', 'values', 'fears', 'likes', 'dislikes',
            'hobbies', 'knowledge_areas', 'behavior_rules', 'catchphrases',
            'family', 'friends', 'enemies', 'secrets', 'skills', 'special_abilities',
            'world_rules', 'memory_rules', 'forbidden_topics', 'boundaries',
            'system_rules', 'roleplay_rules', 'example_reactions', 'example_internal_thoughts'
        ]
        for field_name in list_fields:
            val = getattr(self, field_name, None)
            if not isinstance(val, list):
                setattr(self, field_name, [] if val is None else [str(val)])

        if not isinstance(self.relationships, dict):
            self.relationships = {}
        if not isinstance(self.example_dialogues, list):
            self.example_dialogues = []

        if isinstance(self.metadata, dict):
            self.metadata = CharacterMetadata(
                timestamp=self.metadata.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
                version=self.metadata.get("version", "1.0.0")
            )
        elif not isinstance(self.metadata, CharacterMetadata):
            self.metadata = CharacterMetadata()

    def to_dict(self) -> Dict[str, Any]:
        """Convert character dataclass to dict suitable for JSON serialization."""
        data = asdict(self)
        data['metadata'] = asdict(self.metadata)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Character":
        """Construct Character dataclass from dictionary with auto-repair."""
        meta_raw = data.get("metadata", {})
        metadata = CharacterMetadata(
            timestamp=meta_raw.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
            version=meta_raw.get("version", "1.0.0")
        )
        kwargs = {k: v for k, v in data.items() if k in cls.__dataclass_fields__ and k != "metadata"}
        char = cls(metadata=metadata, **kwargs)
        char.validate_and_repair()
        return char

class CharacterManager:
    """Manages character lifecycle, loading, switching, and party composition."""

    def __init__(self, characters_dir: Optional[Path] = None):
        self.characters_dir = characters_dir or config.paths.characters_dir
        self.characters: Dict[str, Character] = {}
        self.active_character_id: Optional[str] = None
        self.active_party_ids: List[str] = []
        self.load_all_characters()

    def load_all_characters(self) -> None:
        """Load all JSON character files from the characters directory."""
        self.characters_dir.mkdir(parents=True, exist_ok=True)
        json_files = list(self.characters_dir.glob("*.json"))
        
        for file_path in json_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                char = Character.from_dict(data)
                self.characters[char.character_id] = char
                logger.info(f"Loaded character: '{char.character_name}' ({char.character_id})")
            except Exception as e:
                logger.error(f"Failed to load character file {file_path}: {e}")

        if not self.characters:
            self._create_default_character()

        if not self.active_character_id and self.characters:
            self.active_character_id = next(iter(self.characters.keys()))
            self.active_party_ids = [self.active_character_id]

    def _create_default_character(self) -> Character:
        """Create and save a default character if none exist."""
        default_char = Character(
            character_id="default_hero",
            character_name="Aiden Vance",
            nickname="Aiden",
            age="28",
            gender="Male",
            occupation="Wandering Scholar & Swordsman",
            background="Former knight who left the academy to explore ancient ruins.",
            personality_traits=["analytical", "curious", "protective"],
            current_mood="Focused",
            current_location="A dusty tavern near the frontier"
        )
        self.save_character(default_char)
        self.characters[default_char.character_id] = default_char
        return default_char

    def save_character(self, char: Character) -> Path:
        """Save a character dataclass to JSON file."""
        char.validate_and_repair()
        file_path = self.characters_dir / f"{char.character_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(char.to_dict(), f, indent=2, ensure_ascii=False)
        self.characters[char.character_id] = char
        logger.info(f"Saved character '{char.character_name}' to {file_path}")
        return file_path

    def get_character(self, name_or_id: str) -> Optional[Character]:
        """Find character by ID, exact name, or partial nickname match."""
        target = name_or_id.lower().strip()
        if target in self.characters:
            return self.characters[target]

        for char in self.characters.values():
            if char.character_name.lower() == target or char.nickname.lower() == target:
                return char

        # Partial matching
        for char in self.characters.values():
            if target in char.character_name.lower() or target in char.character_id.lower():
                return char

        return None

    def get_active_character(self) -> Optional[Character]:
        """Get the currently active primary character."""
        if self.active_character_id and self.active_character_id in self.characters:
            return self.characters[self.active_character_id]
        return None

    def switch_character(self, name_or_id: str) -> tuple[bool, str]:
        """Runtime character switching command implementation (/switch)."""
        char = self.get_character(name_or_id)
        if not char:
            return False, f"Character '{name_or_id}' not found."

        self.active_character_id = char.character_id
        if char.character_id not in self.active_party_ids:
            self.active_party_ids.append(char.character_id)

        return True, f"Switched active character to '{char.character_name}'."

    def add_to_party(self, name_or_id: str) -> tuple[bool, str]:
        """Add character to active party roster (/add)."""
        char = self.get_character(name_or_id)
        if not char:
            return False, f"Character '{name_or_id}' not found."

        if char.character_id in self.active_party_ids:
            return False, f"'{char.character_name}' is already in the party."

        self.active_party_ids.append(char.character_id)
        return True, f"Added '{char.character_name}' to the party."

    def remove_from_party(self, name_or_id: str) -> tuple[bool, str]:
        """Remove character from active party roster (/remove)."""
        char = self.get_character(name_or_id)
        if not char:
            return False, f"Character '{name_or_id}' not found."

        if char.character_id not in self.active_party_ids:
            return False, f"'{char.character_name}' is not in the active party."

        if len(self.active_party_ids) <= 1:
            return False, "Cannot remove the last character from the active party."

        self.active_party_ids.remove(char.character_id)
        if self.active_character_id == char.character_id:
            self.active_character_id = self.active_party_ids[0]

        return True, f"Removed '{char.character_name}' from the active party."

    def list_party(self) -> List[Character]:
        """Get list of active party characters."""
        return [self.characters[cid] for cid in self.active_party_ids if cid in self.characters]

    def rename_character(self, target_name_or_id: str, new_name: str) -> tuple[bool, str]:
        """Rename character persona and persist changes to disk (/rename)."""
        char = self.get_character(target_name_or_id)
        if not char:
            return False, f"Character '{target_name_or_id}' not found."

        new_name_clean = new_name.strip()
        if not new_name_clean:
            return False, "New character name cannot be empty."

        old_name = char.character_name
        char.character_name = new_name_clean
        if not char.nickname or char.nickname == old_name:
            char.nickname = new_name_clean

        self.save_character(char)
        logger.info(f"Renamed character '{old_name}' (ID: {char.character_id}) to '{new_name_clean}'")
        return True, f"Successfully renamed character '{old_name}' to '{new_name_clean}'."

    def delete_character(self, name_or_id: str) -> tuple[bool, str]:
        """Delete character persona file and remove from manager (/delete)."""
        char = self.get_character(name_or_id)
        if not char:
            return False, f"Character '{name_or_id}' not found."

        file_path = self.characters_dir / f"{char.character_id}.json"
        if file_path.exists():
            file_path.unlink()

        del self.characters[char.character_id]
        if char.character_id in self.active_party_ids:
            self.active_party_ids.remove(char.character_id)

        if self.active_character_id == char.character_id:
            self.active_character_id = self.active_party_ids[0] if self.active_party_ids else None

        return True, f"Deleted character '{char.character_name}'."
