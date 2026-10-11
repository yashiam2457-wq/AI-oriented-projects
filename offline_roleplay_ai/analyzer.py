"""
Message Understanding and Intent Analysis Module for Offline Roleplay AI Framework.
Parses physical action vs dialogue, intent classification, emotional tone,
entity extraction, and automatic memory candidate extraction.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional
from memory import MemoryType

class MessageIntent(str, Enum):
    ACTION = "action"
    DIALOGUE = "dialogue"
    QUESTION = "question"
    FACT_REVEAL = "fact_reveal"
    EMOTION = "emotion"
    DECISION = "decision"
    HYBRID = "hybrid"

@dataclass
class MessageAnalysisResult:
    raw_text: str
    dialogue_parts: List[str] = field(default_factory=list)
    action_parts: List[str] = field(default_factory=list)
    intent: MessageIntent = MessageIntent.DIALOGUE
    emotional_tone: str = "Neutral"
    extracted_entities: List[str] = field(default_factory=list)
    auto_memories: List[Tuple[MemoryType, str, float]] = field(default_factory=list)

    @property
    def spoken_dialogue(self) -> str:
        """Combine all spoken dialogue segments into a single string."""
        return " ".join(self.dialogue_parts).strip()

    @property
    def physical_actions(self) -> str:
        """Combine all physical action segments into a single string."""
        return " ".join(self.action_parts).strip()

class MessageAnalyzer:
    """Offline NLP & Heuristic Analyzer to extract rich context from user messages."""

    # Keywords for intent detection
    QUESTION_WORDS = {"what", "why", "how", "who", "where", "when", "can", "could", "would", "is", "are", "do", "does", "did"}
    DECISION_WORDS = {"choose", "decide", "agree", "refuse", "accept", "reject", "let's", "will do", "promise", "swear"}
    FACT_WORDS = {"my name is", "i am", "i have", "i know", "i hid", "i possess", "secret", "remember", "always", "never"}

    # Keywords for emotional tone
    EMOTION_PATTERNS = {
        "Hostile / Aggressive": [r"\b(attack|strike|kill|draw|sword|fight|hate|glare|threat|punch|anger)\b"],
        "Friendly / Warm": [r"\b(smile|hug|thank|laugh|friend|glad|help|warm|kind|gentle)\b"],
        "Anxious / Fearful": [r"\b(fear|afraid|tremble|scared|nervous|worry|hesitate|darkness|gasp)\b"],
        "Secretive / Cautious": [r"\b(whisper|stealth|sneak|quiet|hidden|shadow|look around|cautious|mutter)\b"],
        "Curious / Inquisitive": [r"\b(inspect|examine|look at|search|study|curious|wonder|ask)\b"],
        "Decisive / Confident": [r"\b(declare|stand|command|march|firm|lead|resolve|bound)\b"]
    }

    @classmethod
    def analyze_message(
        cls,
        text: str,
        user_name: str = "Player",
        active_char_name: str = "Character"
    ) -> MessageAnalysisResult:
        """Perform comprehensive analysis of input message turn."""
        if not text or not text.strip():
            return MessageAnalysisResult(raw_text="")

        clean_text = text.strip()
        actions, dialogue = cls._extract_actions_and_dialogue(clean_text)
        intent = cls._classify_intent(clean_text, actions, dialogue)
        tone = cls._detect_emotional_tone(clean_text)
        entities = cls._extract_entities(clean_text)
        memories = cls._generate_auto_memories(clean_text, actions, dialogue, intent, user_name, active_char_name)

        return MessageAnalysisResult(
            raw_text=clean_text,
            dialogue_parts=dialogue,
            action_parts=actions,
            intent=intent,
            emotional_tone=tone,
            extracted_entities=entities,
            auto_memories=memories
        )

    @classmethod
    def _extract_actions_and_dialogue(cls, text: str) -> Tuple[List[str], List[str]]:
        """Separate actions enclosed in () or * * from spoken dialogue."""
        actions = []
        dialogue = []

        pattern = r'(\([^)]+\)|\*[^*]+\*)'
        parts = re.split(pattern, text)

        for part in parts:
            part_str = part.strip()
            if not part_str:
                continue

            if (part_str.startswith('(') and part_str.endswith(')')) or \
               (part_str.startswith('*') and part_str.endswith('*')):
                action_clean = part_str[1:-1].strip()
                if action_clean:
                    actions.append(action_clean)
            else:
                dialogue.append(part_str)

        return actions, dialogue

    @classmethod
    def _classify_intent(cls, text: str, actions: List[str], dialogue: List[str]) -> MessageIntent:
        """Determine primary intent of the user message."""
        lower_text = text.lower()

        is_question = any(lower_text.startswith(w) or f" {w} " in lower_text for w in cls.QUESTION_WORDS) or "?" in text
        is_decision = any(w in lower_text for w in cls.DECISION_WORDS)
        is_fact = any(w in lower_text for w in cls.FACT_WORDS)

        if actions and dialogue:
            return MessageIntent.HYBRID
        elif actions and not dialogue:
            return MessageIntent.ACTION
        elif is_question:
            return MessageIntent.QUESTION
        elif is_decision:
            return MessageIntent.DECISION
        elif is_fact:
            return MessageIntent.FACT_REVEAL
        else:
            return MessageIntent.DIALOGUE

    @classmethod
    def _detect_emotional_tone(cls, text: str) -> str:
        """Identify emotional nuance in the text."""
        lower_text = text.lower()
        for emotion, patterns in cls.EMOTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, lower_text):
                    return emotion
        return "Neutral / Calm"

    @classmethod
    def _extract_entities(cls, text: str) -> List[str]:
        """Extract key potential entities (Capitalized words, items, locations)."""
        entities = []
        words = text.split()
        for i, word in enumerate(words):
            clean_w = re.sub(r'[^\w]', '', word)
            if clean_w and clean_w[0].isupper() and len(clean_w) > 2:
                if i > 0 and clean_w not in entities:
                    entities.append(clean_w)
        return entities[:5]

    @classmethod
    def _generate_auto_memories(
        cls,
        text: str,
        actions: List[str],
        dialogue: List[str],
        intent: MessageIntent,
        user_name: str,
        active_char_name: str
    ) -> List[Tuple[MemoryType, str, float]]:
        """Automatically create candidate memories based on turn analysis."""
        auto_mems = []

        if actions:
            action_text = "; ".join(actions)
            auto_mems.append((
                MemoryType.EVENT,
                f"{user_name} performed action: {action_text}",
                2.0
            ))

        lower_text = text.lower()
        if "my name is" in lower_text or "i am " in lower_text:
            auto_mems.append((
                MemoryType.USER,
                f"User Fact: {text[:100]}",
                3.0
            ))

        if intent == MessageIntent.DECISION:
            auto_mems.append((
                MemoryType.LONG_TERM,
                f"{user_name} made key narrative decision: {text[:120]}",
                3.5
            ))

        if any(w in lower_text for w in ["thank", "trust", "love", "friend", "promise", "help"]):
            auto_mems.append((
                MemoryType.RELATIONSHIP,
                f"{user_name} expressed positive regard towards {active_char_name}: {text[:100]}",
                2.5
            ))
        elif any(w in lower_text for w in ["hate", "betray", "lie", "threat", "fight", "kill"]):
            auto_mems.append((
                MemoryType.RELATIONSHIP,
                f"{user_name} expressed hostility/conflict towards {active_char_name}: {text[:100]}",
                3.0
            ))

        return auto_mems
