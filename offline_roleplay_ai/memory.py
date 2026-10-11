"""
Hierarchical Memory Framework and Retrieval Engine for Offline Roleplay AI.
Supports Working, Recent, Long-Term, Story, Character, Relationship, Event, User, and World memory layers.
Implements local keyword & BM25-style memory retrieval for offline operation.
"""

import math
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional

class MemoryType(str, Enum):
    WORKING = "working"
    RECENT = "recent"
    LONG_TERM = "long_term"
    STORY = "story"
    CHARACTER = "character"
    RELATIONSHIP = "relationship"
    EVENT = "event"
    USER = "user"
    WORLD = "world"

@dataclass
class MemoryEntry:
    memory_id: str
    session_id: str
    memory_type: MemoryType
    content: str
    character_id: Optional[str] = None
    subject: str = "general"
    importance: float = 1.0  # 1.0 (normal) to 5.0 (vital)
    tags: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "session_id": self.session_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "character_id": self.character_id,
            "subject": self.subject,
            "importance": self.importance,
            "tags": self.tags,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        return cls(
            memory_id=data["memory_id"],
            session_id=data["session_id"],
            memory_type=MemoryType(data.get("memory_type", MemoryType.LONG_TERM.value)),
            content=data["content"],
            character_id=data.get("character_id"),
            subject=data.get("subject", "general"),
            importance=float(data.get("importance", 1.0)),
            tags=data.get("tags", []),
            timestamp=float(data.get("timestamp", time.time()))
        )

class MemoryRetrievalEngine:
    """Offline keyword / BM25 memory ranker to find contextually relevant memories."""

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple lower-case word tokenizer."""
        return [w.lower() for w in re.findall(r'\b\w+\b', text) if len(w) > 2]

    @classmethod
    def rank_memories(
        cls,
        query: str,
        memories: List[MemoryEntry],
        top_k: int = 5,
        min_score: float = 0.1
    ) -> List[MemoryEntry]:
        """Rank memories based on Term Frequency, Importance, and Recency."""
        query_tokens = set(cls._tokenize(query))
        if not query_tokens or not memories:
            return sorted(memories, key=lambda m: m.importance, reverse=True)[:top_k]

        scored_memories = []
        current_time = time.time()

        for mem in memories:
            mem_tokens = cls._tokenize(mem.content)
            if not mem_tokens:
                continue

            # Term Overlap Score
            match_count = sum(1 for token in query_tokens if token in mem_tokens)
            tf_score = match_count / (len(query_tokens) + math.log(len(mem_tokens) + 1))

            # Tag Match Bonus
            tag_bonus = sum(0.5 for tag in mem.tags if tag.lower() in query_tokens)

            # Recency Decay Score (decay over 7 days)
            age_hours = (current_time - mem.timestamp) / 3600.0
            recency_score = 1.0 / (1.0 + (age_hours / 168.0))

            # Final Score Calculation
            final_score = (tf_score * 2.0 + tag_bonus) * mem.importance * (0.8 + 0.2 * recency_score)

            if final_score >= min_score or match_count > 0:
                scored_memories.append((final_score, mem))

        # Sort descending by score
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [mem for score, mem in scored_memories[:top_k]]

class HierarchicalMemoryManager:
    """Manages memory lifecycle across all 9 hierarchical layers."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.memories: Dict[MemoryType, List[MemoryEntry]] = {m_type: [] for m_type in MemoryType}

    def add_memory(
        self,
        memory_type: MemoryType,
        content: str,
        character_id: Optional[str] = None,
        subject: str = "general",
        importance: float = 1.0,
        tags: Optional[List[str]] = None
    ) -> MemoryEntry:
        """Create and store a memory entry in the appropriate memory layer."""
        mem_id = f"mem_{int(time.time() * 1000)}_{len(self.memories[memory_type])}"
        entry = MemoryEntry(
            memory_id=mem_id,
            session_id=self.session_id,
            memory_type=memory_type,
            content=content,
            character_id=character_id,
            subject=subject,
            importance=importance,
            tags=tags or []
        )
        self.memories[memory_type].append(entry)
        return entry

    def get_memories_by_type(self, memory_type: MemoryType, character_id: Optional[str] = None) -> List[MemoryEntry]:
        """Retrieve memories for a specific layer, optionally filtered by character."""
        all_mems = self.memories.get(memory_type, [])
        if character_id:
            return [m for m in all_mems if m.character_id is None or m.character_id == character_id]
        return all_mems

    def search_memories(self, query: str, top_k: int = 5, character_id: Optional[str] = None) -> List[MemoryEntry]:
        """Search across all long-term, story, event, relationship, user, and world memories."""
        searchable_types = [
            MemoryType.LONG_TERM, MemoryType.STORY, MemoryType.CHARACTER,
            MemoryType.RELATIONSHIP, MemoryType.EVENT, MemoryType.USER, MemoryType.WORLD
        ]
        candidates = []
        for m_type in searchable_types:
            for mem in self.memories[m_type]:
                if character_id is None or mem.character_id is None or mem.character_id == character_id:
                    candidates.append(mem)

        return MemoryRetrievalEngine.rank_memories(query, candidates, top_k=top_k)

    def load_memory_list(self, entries: List[MemoryEntry]) -> None:
        """Clear and load memory list from persistence engine."""
        self.memories = {m_type: [] for m_type in MemoryType}
        for entry in entries:
            if entry.memory_type in self.memories:
                self.memories[entry.memory_type].append(entry)
