"""
Consolidated Pytest Test Suite for Offline Roleplay AI Framework.
Tests character validation, auto-repair, switching, memory retrieval, context budget, SQLite persistence, and export/import.
"""

import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from config import AppConfig, RoleplayMode, PathsConfig
from character import Character, CharacterManager, CharacterMetadata
from memory import HierarchicalMemoryManager, MemoryType, MemoryEntry, MemoryRetrievalEngine
from engine import LMStudioClient, ContextBudgetManager, PromptBuilder
from session import SessionState, StoryContext, PersistenceEngine, SessionManager

@pytest.fixture
def temp_dir():
    with TemporaryDirectory() as tmp:
        yield Path(tmp)

@pytest.fixture
def custom_config(temp_dir):
    paths = PathsConfig(
        base_dir=temp_dir,
        characters_dir=temp_dir / "characters",
        sessions_dir=temp_dir / "sessions",
        memories_dir=temp_dir / "memories",
        summaries_dir=temp_dir / "summaries",
        chats_dir=temp_dir / "chats",
        db_path=temp_dir / "test_roleplay.db",
        logs_dir=temp_dir / "logs"
    )
    paths.ensure_directories()
    return AppConfig(paths=paths)

# ==================== CHARACTER TESTS ====================

def test_character_validation_and_repair():
    """Verify that incomplete character dicts are auto-repaired with default fallback fields."""
    raw_data = {
        "character_id": "test_hero",
        "character_name": "Test Knight"
        # Missing 58+ other fields
    }
    char = Character.from_dict(raw_data)
    assert char.character_id == "test_hero"
    assert char.character_name == "Test Knight"
    assert isinstance(char.personality_traits, list)
    assert isinstance(char.relationships, dict)
    assert char.metadata.version == "1.0.0"

def test_character_manager_switching(temp_dir):
    """Test character loading, runtime switching, and party roster management."""
    manager = CharacterManager(characters_dir=temp_dir / "characters")
    
    char1 = Character(character_id="hero_1", character_name="Alice The Bold")
    char2 = Character(character_id="hero_2", character_name="Bob The Wise")
    manager.save_character(char1)
    manager.save_character(char2)

    manager.active_party_ids = ["hero_2"]
    manager.active_character_id = "hero_2"

    ok, msg = manager.switch_character("hero_2")
    assert ok is True
    assert manager.active_character_id == "hero_2"
    assert manager.get_active_character().character_name == "Bob The Wise"

    ok, msg = manager.add_to_party("hero_1")
    assert ok is True
    assert "hero_1" in manager.active_party_ids
    assert len(manager.active_party_ids) == 2

    ok, msg = manager.remove_from_party("hero_1")
    assert ok is True
    assert "hero_1" not in manager.active_party_ids

def test_character_manager_renaming(temp_dir):
    """Test character renaming and persistence."""
    manager = CharacterManager(characters_dir=temp_dir / "characters")
    char = Character(character_id="hero_renamable", character_name="Old Name", nickname="Old Name")
    manager.save_character(char)

    # Rename valid character
    ok, msg = manager.rename_character("hero_renamable", "New Glorious Name")
    assert ok is True
    assert "Successfully renamed" in msg
    assert manager.get_character("hero_renamable").character_name == "New Glorious Name"
    assert manager.get_character("hero_renamable").nickname == "New Glorious Name"

    # Reload from disk to verify persistence
    manager_reloaded = CharacterManager(characters_dir=temp_dir / "characters")
    reloaded_char = manager_reloaded.get_character("hero_renamable")
    assert reloaded_char is not None
    assert reloaded_char.character_name == "New Glorious Name"

    # Try renaming non-existent character
    ok_err, msg_err = manager.rename_character("non_existent", "Some Name")
    assert ok_err is False

    # Try empty name
    ok_empty, msg_empty = manager.rename_character("hero_renamable", "   ")
    assert ok_empty is False

def test_story_context_user_name():
    """Verify StoryContext user_name default and custom configuration."""
    default_story = StoryContext(title="Default Story")
    assert default_story.user_name == "Yash"

    custom_story = StoryContext(title="Test Story", user_name="Alex")
    assert custom_story.user_name == "Alex"

# ==================== MEMORY TESTS ====================

def test_hierarchical_memory_and_retrieval():
    """Test memory creation across layers and BM25 offline keyword retrieval."""
    mem_mgr = HierarchicalMemoryManager("test_session")
    
    mem_mgr.add_memory(
        MemoryType.LONG_TERM,
        content="Aiden discovered a magical runic sword in the ruined temple.",
        importance=4.0,
        tags=["magic", "sword", "temple"]
    )
    mem_mgr.add_memory(
        MemoryType.USER,
        content="User prefers stealth tactics over direct confrontation.",
        importance=3.0,
        tags=["stealth", "user"]
    )

    results = mem_mgr.search_memories("Tell me about the magic sword", top_k=1)
    assert len(results) == 1
    assert "runic sword" in results[0].content

# ==================== CONTEXT & ENGINE TESTS ====================

def test_context_budget_trimming():
    """Test that context budget manager correctly fits messages within token limit."""
    sys_msg = {"role": "system", "content": "You are a roleplay character."}
    chat_history = [
        {"role": "user", "content": f"Turn {i} " + "word " * 50}
        for i in range(100)
    ]

    # Truncate to a tight budget of 1500 tokens
    fitted = ContextBudgetManager.fit_messages_in_budget(
        sys_msg, chat_history, max_context_tokens=1500, reserved_response_tokens=500
    )

    assert fitted[0]["role"] == "system"
    assert len(fitted) < len(chat_history)  # Verify history was trimmed from top

def test_prompt_builder():
    """Verify prompt builder includes persona details and system directives."""
    char = Character(
        character_id="elena",
        character_name="Elena Dusk",
        speaking_style="Whispered and secretive",
        personality_traits=["elusive", "shrewd"]
    )
    prompt = PromptBuilder.build_system_prompt(
        active_character=char,
        mode=RoleplayMode.SINGLE_CHARACTER,
        story_info={"title": "Shadow Quest"},
        retrieved_memories=[]
    )

    assert "Elena Dusk" in prompt
    assert "Whispered and secretive" in prompt
    assert "MANDATORY SYSTEM DIRECTIVES" in prompt

# ==================== PERSISTENCE & SESSION TESTS ====================

def test_sqlite_persistence_and_export(temp_dir):
    """Test SQLite database initialization, session saving, chat logging, and JSON export/import."""
    db_path = temp_dir / "test_db.db"
    persistence = PersistenceEngine(db_path=db_path)
    session_mgr = SessionManager(persistence=persistence)

    story = StoryContext(title="The Ancient Crypt", genre="Horror")
    session = session_mgr.create_new_session(
        title="The Ancient Crypt",
        mode=RoleplayMode.SINGLE_CHARACTER,
        story=story,
        active_char_id="default_hero"
    )

    # Save chat messages
    persistence.add_chat_message(session.session_id, "user", "Hello into the darkness.")
    persistence.add_chat_message(session.session_id, "assistant", "A cold draft answers your voice.")

    chats = persistence.get_chat_history(session.session_id)
    assert len(chats) == 2
    assert chats[0]["content"] == "Hello into the darkness."

    # Test JSON Export
    export_file = temp_dir / "export_test.json"
    ok, msg = session_mgr.export_session_to_file(export_file)
    assert ok is True
    assert export_file.exists()

    # Test JSON Import
    ok, msg = session_mgr.import_session_from_file(export_file)
    assert ok is True
    assert session_mgr.active_session.session_title == "The Ancient Crypt"

# ==================== MESSAGE UNDERSTANDING & STORY PROGRESSION TESTS ====================

def test_message_analyzer_actions_dialogue_and_intent():
    """Verify physical action vs dialogue separation, intent classification, and auto-memories."""
    from analyzer import MessageAnalyzer, MessageIntent

    msg_text = "(opens the heavy wooden door cautiously) *draws sword* Is anyone inside?"
    analysis = MessageAnalyzer.analyze_message(msg_text, user_name="Yash", active_char_name="Aiden")

    assert "opens the heavy wooden door cautiously" in analysis.action_parts
    assert "draws sword" in analysis.action_parts
    assert "Is anyone inside?" in analysis.dialogue_parts
    assert analysis.intent in [MessageIntent.QUESTION, MessageIntent.HYBRID]
    assert len(analysis.auto_memories) > 0

def test_story_progression_tracker_and_trust():
    """Test story arc advancement, milestone tracking, and relationship trust score adjustments."""
    from progression import StoryProgressionTracker, StoryProgressionState, StoryArcPhase

    prog_state = StoryProgressionState()
    tracker = StoryProgressionTracker(prog_state)

    assert prog_state.story_arc == StoryArcPhase.SETUP
    assert prog_state.relationship_trust_score == 5.0

    tracker.adjust_trust(2.0)
    assert prog_state.relationship_trust_score == 7.0
    assert "Trusted Ally" in prog_state.relationship_status

    tracker.add_objective("Retrieve the Silver Key")
    assert "Retrieve the Silver Key" in prog_state.active_objectives

    tracker.complete_objective("Retrieve the Silver Key")
    assert "Retrieve the Silver Key" not in prog_state.active_objectives
    assert any("Retrieve the Silver Key" in ms for ms in prog_state.completed_milestones)

    # Advance turns to trigger Rising Action arc
    for _ in range(10):
        tracker.advance_turn("dialogue", "Friendly")

    assert prog_state.total_turns == 10
    assert prog_state.story_arc == StoryArcPhase.RISING_ACTION

def test_prompt_builder_with_analysis_and_progression():
    """Verify prompt builder formats message analysis and story progression context blocks."""
    from analyzer import MessageAnalyzer
    from progression import StoryProgressionState, StoryArcPhase

    char = Character(character_id="hero_test", character_name="Valerie")
    analysis = MessageAnalyzer.analyze_message("(bows respectfully) Thank you for your assistance.", user_name="Yash", active_char_name="Valerie")
    progression = StoryProgressionState(
        story_arc=StoryArcPhase.RISING_ACTION,
        chapter=2,
        total_turns=8,
        relationship_trust_score=7.5,
        relationship_status="Close Confidant"
    )

    prompt = PromptBuilder.build_system_prompt(
        active_character=char,
        mode=RoleplayMode.SINGLE_CHARACTER,
        story_info={"title": "Epic Voyage"},
        retrieved_memories=[],
        message_analysis=analysis,
        story_progression=progression
    )

    assert "STORY PROGRESSION & NARRATIVE ARC" in prompt
    assert "Rising Action" in prompt
    assert "Close Confidant" in prompt
    assert "LATEST MESSAGE UNDERSTANDING & INTENT" in prompt
    assert "bows respectfully" in prompt

def test_session_progression_persistence_and_export(temp_dir):
    """Verify story progression state is saved to SQLite database and export JSON files."""
    from progression import StoryProgressionState, StoryArcPhase

    db_path = temp_dir / "prog_test_db.db"
    persistence = PersistenceEngine(db_path=db_path)
    session_mgr = SessionManager(persistence=persistence)

    story = StoryContext(title="Progression Persistence Story")
    session = session_mgr.create_new_session(
        title="Progression Persistence Story",
        mode=RoleplayMode.SINGLE_CHARACTER,
        story=story,
        active_char_id="default_hero"
    )

    session.progression.story_arc = StoryArcPhase.CLIMAX
    session.progression.relationship_trust_score = 8.5
    session.progression.completed_milestones.append("Slayed dragon")

    session_mgr.save_current_session()

    # Load session and verify progression restoration
    new_session_mgr = SessionManager(persistence=persistence)
    ok, msg = new_session_mgr.load_session(session.session_id)
    assert ok is True
    assert new_session_mgr.active_session.progression.story_arc == StoryArcPhase.CLIMAX
    assert new_session_mgr.active_session.progression.relationship_trust_score == 8.5
    assert "Slayed dragon" in new_session_mgr.active_session.progression.completed_milestones

def test_situational_adaptability():
    """Verify that user turn cues dynamically evaluate situational danger, mode, and scene directives."""
    from analyzer import MessageAnalyzer
    from progression import StoryProgressionTracker

    tracker = StoryProgressionTracker()

    # Combat trigger
    msg_combat = MessageAnalyzer.analyze_message("(draws sword and strikes the enemy) Stand behind me!")
    adapt_combat = tracker.evaluate_situational_adaptation(msg_combat)
    assert adapt_combat.situation_type == "Combat / Tactical"
    assert adapt_combat.danger_level in ["Moderate", "High"]
    assert "Tense" in adapt_combat.dynamic_mood

    # Stealth trigger
    msg_stealth = MessageAnalyzer.analyze_message("(whispers silently in the shadows) Keep quiet.")
    adapt_stealth = tracker.evaluate_situational_adaptation(msg_stealth)
    assert adapt_stealth.situation_type == "Stealth / Covert"
    assert adapt_stealth.dynamic_speaking_style == "Whispered, Hushed, Subdued"

def test_story_progression_behavior_modification():
    """Verify trust score changes and milestone completions modify story-evolved behaviors."""
    from progression import StoryProgressionTracker, StoryArcPhase

    tracker = StoryProgressionTracker()
    assert tracker.state.evolved_behaviors.trust_unlocked_traits == []

    # High trust evolution
    tracker.adjust_trust(4.0)  # Trust score 9.0
    assert "unshakably loyal" in tracker.state.evolved_behaviors.trust_unlocked_traits

    # Milestone addition
    tracker.add_milestone("Rescued captive villager")
    assert any("Rescued captive villager" in directive for directive in tracker.state.evolved_behaviors.milestone_acquired_behaviors)

def test_core_behavior_retention_for_new_story(temp_dir):
    """Verify that starting a new story resets story-evolved behaviors back to core character defaults."""
    from character import CharacterManager, Character
    from session import SessionManager, PersistenceEngine, StoryContext
    from progression import StoryArcPhase, StoryProgressionTracker

    char_dir = temp_dir / "characters"
    char_mgr = CharacterManager(characters_dir=char_dir)
    base_char = Character(
        character_id="hero_core",
        character_name="Kaelen",
        personality_traits=["analytical", "cautious"],
        behavior_rules=["Always protect allies."]
    )
    char_mgr.save_character(base_char)

    db_path = temp_dir / "stories_db.db"
    persistence = PersistenceEngine(db_path=db_path)
    session_mgr = SessionManager(persistence=persistence)

    # Story 1: Evolve behaviors
    story1 = StoryContext(title="Story 1 - Epic War")
    session1 = session_mgr.create_new_session("Story 1", RoleplayMode.SINGLE_CHARACTER, story1, "hero_core")
    tracker1 = StoryProgressionTracker(session1.progression)
    tracker1.adjust_trust(4.0)  # High trust score
    session1.progression.story_arc = StoryArcPhase.CLIMAX
    tracker1.add_milestone("Defeated Shadow Lord")
    session_mgr.save_current_session()

    assert "unshakably loyal" in session1.progression.evolved_behaviors.trust_unlocked_traits

    # Story 2: Start a brand NEW story with the same character
    story2 = StoryContext(title="Story 2 - Fresh Beginning")
    session2 = session_mgr.create_new_session("Story 2", RoleplayMode.SINGLE_CHARACTER, story2, "hero_core")

    # Verify Story 2 has pristine, reset progression state
    assert session2.progression.relationship_trust_score == 5.0
    assert session2.progression.story_arc == StoryArcPhase.SETUP
    assert session2.progression.evolved_behaviors.trust_unlocked_traits == []
    assert session2.progression.completed_milestones == []

    # Verify the base character definition on disk remained pristine and unmodified
    reloaded_char = char_mgr.get_character("hero_core")
    assert reloaded_char.personality_traits == ["analytical", "cautious"]
    assert reloaded_char.behavior_rules == ["Always protect allies."]

