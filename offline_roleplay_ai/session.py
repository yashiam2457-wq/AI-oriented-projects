"""
Session Management and SQLite Persistence Module for Offline Roleplay AI Framework.
Handles database schemas, persistent chat histories, episodic memories, export/import, and searching.
"""

import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import config, RoleplayMode
from memory import MemoryEntry, MemoryType, HierarchicalMemoryManager
from progression import StoryProgressionState

logger = logging.getLogger(__name__)

@dataclass
class StoryContext:
    title: str = "Untitled Story"
    genre: str = "Fantasy / Adventure"
    theme: str = "Exploration & Survival"
    world: str = "Custom Roleplay Realm"
    setting: str = "A bustling border kingdom"
    time_period: str = "Medieval Fantasy"
    scenario: str = "The journey begins."
    goal: str = "Uncover hidden secrets."
    starting_event: str = "Meeting at the local tavern."
    main_character_id: str = "default_hero"
    side_character_ids: List[str] = field(default_factory=list)
    user_name: str = "Yash"

@dataclass
class SessionState:
    session_id: str
    session_title: str
    mode: RoleplayMode = RoleplayMode.SINGLE_CHARACTER
    active_character_id: str = "default_hero"
    party_ids: List[str] = field(default_factory=lambda: ["default_hero"])
    story: StoryContext = field(default_factory=StoryContext)
    story_summary: str = ""
    progression: StoryProgressionState = field(default_factory=StoryProgressionState)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

class PersistenceEngine:
    """SQLite Database persistence manager for sessions, messages, and memories."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.paths.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create database tables if they do not exist and ensure columns exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    session_title TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    active_character_id TEXT NOT NULL,
                    party_ids_json TEXT NOT NULL,
                    story_json TEXT NOT NULL,
                    story_summary TEXT DEFAULT '',
                    story_progression_json TEXT DEFAULT '{}',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            # Check for column existence for legacy DBs
            cursor.execute("PRAGMA table_info(sessions)")
            cols = [row["name"] for row in cursor.fetchall()]
            if "story_progression_json" not in cols:
                cursor.execute("ALTER TABLE sessions ADD COLUMN story_progression_json TEXT DEFAULT '{}'")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    character_id TEXT,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    character_id TEXT,
                    subject TEXT,
                    importance REAL DEFAULT 1.0,
                    tags_json TEXT,
                    timestamp REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    def save_session_state(self, state: SessionState) -> None:
        """Persist or update session metadata in SQLite."""
        state.updated_at = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (
                    session_id, session_title, mode, active_character_id,
                    party_ids_json, story_json, story_summary, story_progression_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    session_title = excluded.session_title,
                    mode = excluded.mode,
                    active_character_id = excluded.active_character_id,
                    party_ids_json = excluded.party_ids_json,
                    story_json = excluded.story_json,
                    story_summary = excluded.story_summary,
                    story_progression_json = excluded.story_progression_json,
                    updated_at = excluded.updated_at
            """, (
                state.session_id,
                state.session_title,
                state.mode.value,
                state.active_character_id,
                json.dumps(state.party_ids),
                json.dumps(state.story.__dict__),
                state.story_summary,
                json.dumps(state.progression.to_dict()),
                state.created_at,
                state.updated_at
            ))
            conn.commit()

    def load_session_state(self, session_id: str) -> Optional[SessionState]:
        """Load session state from SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                return None

            party_ids = json.loads(row["party_ids_json"]) if row["party_ids_json"] else []
            story_dict = json.loads(row["story_json"]) if row["story_json"] else {}
            story = StoryContext(**story_dict)

            prog_raw = row["story_progression_json"] if "story_progression_json" in row.keys() and row["story_progression_json"] else "{}"
            prog_dict = json.loads(prog_raw) if isinstance(prog_raw, str) else {}
            progression = StoryProgressionState.from_dict(prog_dict)

            return SessionState(
                session_id=row["session_id"],
                session_title=row["session_title"],
                mode=RoleplayMode(row["mode"]),
                active_character_id=row["active_character_id"],
                party_ids=party_ids,
                story=story,
                story_summary=row["story_summary"],
                progression=progression,
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all available session summaries."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id, session_title, mode, active_character_id, updated_at FROM sessions ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def delete_session(self, session_id: str) -> bool:
        """Delete session and all linked chat logs & memories."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount > 0

    def add_chat_message(self, session_id: str, role: str, content: str, character_id: Optional[str] = None) -> int:
        """Insert a single chat message into database history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_messages (session_id, role, character_id, content, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, role, character_id, content, time.time()))
            conn.commit()
            return cursor.lastrowid

    def get_chat_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch chat history for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id ASC"
            if limit:
                query = f"SELECT * FROM (SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id DESC LIMIT {limit}) ORDER BY id ASC"
            cursor.execute(query, (session_id,))
            return [dict(row) for row in cursor.fetchall()]

    def save_memories(self, session_id: str, memories: List[MemoryEntry]) -> None:
        """Persist memory entries in SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for mem in memories:
                cursor.execute("""
                    INSERT INTO memories (
                        memory_id, session_id, memory_type, content,
                        character_id, subject, importance, tags_json, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(memory_id) DO UPDATE SET
                        content = excluded.content,
                        importance = excluded.importance,
                        tags_json = excluded.tags_json,
                        timestamp = excluded.timestamp
                """, (
                    mem.memory_id,
                    session_id,
                    mem.memory_type.value,
                    mem.content,
                    mem.character_id,
                    mem.subject,
                    mem.importance,
                    json.dumps(mem.tags),
                    mem.timestamp
                ))
            conn.commit()

    def load_memories(self, session_id: str) -> List[MemoryEntry]:
        """Load all memory entries for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memories WHERE session_id = ?", (session_id,))
            entries = []
            for row in cursor.fetchall():
                data = dict(row)
                data["tags"] = json.loads(data["tags_json"]) if data["tags_json"] else []
                entries.append(MemoryEntry.from_dict(data))
            return entries

    def search_messages_and_memories(self, query: str, session_id: str) -> Dict[str, List[Any]]:
        """Search across messages, summaries, and memories for a specific session (/search)."""
        pattern = f"%{query}%"
        results: Dict[str, List[Any]] = {"messages": [], "memories": []}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM chat_messages 
                WHERE session_id = ? AND content LIKE ? 
                ORDER BY timestamp DESC LIMIT 10
            """, (session_id, pattern))
            results["messages"] = [dict(r) for r in cursor.fetchall()]

            cursor.execute("""
                SELECT * FROM memories 
                WHERE session_id = ? AND (content LIKE ? OR subject LIKE ?) 
                ORDER BY importance DESC LIMIT 10
            """, (session_id, pattern, pattern))
            results["memories"] = [dict(r) for r in cursor.fetchall()]

        return results

class SessionManager:
    """Manages active session state, switching, exporting, and auto-saving."""

    def __init__(self, persistence: Optional[PersistenceEngine] = None):
        self.persistence = persistence or PersistenceEngine()
        self.active_session: Optional[SessionState] = None
        self.memory_manager: Optional[HierarchicalMemoryManager] = None

    def create_new_session(self, title: str, mode: RoleplayMode, story: StoryContext, active_char_id: str) -> SessionState:
        """Initialize a new roleplay session."""
        session_id = f"session_{int(time.time())}"
        session = SessionState(
            session_id=session_id,
            session_title=title,
            mode=mode,
            active_character_id=active_char_id,
            party_ids=[active_char_id],
            story=story
        )
        self.active_session = session
        self.memory_manager = HierarchicalMemoryManager(session_id)
        self.persistence.save_session_state(session)
        logger.info(f"Created new session: {title} ({session_id})")
        return session

    def load_session(self, session_id: str) -> tuple[bool, str]:
        """Load session and restore memory manager state."""
        session = self.persistence.load_session_state(session_id)
        if not session:
            return False, f"Session '{session_id}' not found."

        self.active_session = session
        self.memory_manager = HierarchicalMemoryManager(session_id)
        mems = self.persistence.load_memories(session_id)
        self.memory_manager.load_memory_list(mems)
        return True, f"Loaded session '{session.session_title}'."

    def save_current_session(self) -> tuple[bool, str]:
        """Persist current session state and memories."""
        if not self.active_session or not self.memory_manager:
            return False, "No active session to save."

        self.persistence.save_session_state(self.active_session)
        all_mems = []
        for mem_list in self.memory_manager.memories.values():
            all_mems.extend(mem_list)
        self.persistence.save_memories(self.active_session.session_id, all_mems)
        return True, f"Saved session '{self.active_session.session_title}' successfully."

    def export_session_to_file(self, export_path: Path) -> tuple[bool, str]:
        """Export session, chat history, and memories to JSON file (/export)."""
        if not self.active_session:
            return False, "No active session to export."

        chats = self.persistence.get_chat_history(self.active_session.session_id)
        mems = [m.to_dict() for m_list in self.memory_manager.memories.values() for m in m_list]

        export_data = {
            "session": {
                "session_id": self.active_session.session_id,
                "session_title": self.active_session.session_title,
                "mode": self.active_session.mode.value,
                "active_character_id": self.active_session.active_character_id,
                "party_ids": self.active_session.party_ids,
                "story": self.active_session.story.__dict__,
                "story_summary": self.active_session.story_summary,
                "story_progression": self.active_session.progression.to_dict(),
                "created_at": self.active_session.created_at,
                "updated_at": self.active_session.updated_at
            },
            "chat_history": chats,
            "memories": mems
        }

        try:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            return True, f"Session exported to {export_path}"
        except Exception as e:
            return False, f"Failed to export session: {e}"

    def import_session_from_file(self, import_path: Path) -> tuple[bool, str]:
        """Import a session from a JSON export file (/import)."""
        if not import_path.exists():
            return False, f"Export file {import_path} does not exist."

        try:
            with open(import_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            s_raw = data["session"]
            story = StoryContext(**s_raw["story"])
            prog_dict = s_raw.get("story_progression", {})
            progression = StoryProgressionState.from_dict(prog_dict)

            session = SessionState(
                session_id=s_raw["session_id"],
                session_title=s_raw["session_title"],
                mode=RoleplayMode(s_raw["mode"]),
                active_character_id=s_raw["active_character_id"],
                party_ids=s_raw["party_ids"],
                story=story,
                story_summary=s_raw.get("story_summary", ""),
                progression=progression,
                created_at=s_raw.get("created_at", time.time()),
                updated_at=s_raw.get("updated_at", time.time())
            )

            self.persistence.save_session_state(session)
            
            # Import chat history
            for chat in data.get("chat_history", []):
                self.persistence.add_chat_message(
                    session.session_id, chat["role"], chat["content"], chat.get("character_id")
                )

            # Import memories
            m_entries = [MemoryEntry.from_dict(m) for m in data.get("memories", [])]
            self.persistence.save_memories(session.session_id, m_entries)

            self.active_session = session
            self.memory_manager = HierarchicalMemoryManager(session.session_id)
            self.memory_manager.load_memory_list(m_entries)

            return True, f"Imported session '{session.session_title}' successfully."
        except Exception as e:
            return False, f"Failed to import session: {e}"
