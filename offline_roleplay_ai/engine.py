"""
Core Engine Module for Offline Roleplay AI Framework.
Interactions with LM Studio local API, Context Budget Manager, Summarizer, and Dynamic Prompt Builder.
"""

import json
import logging
import re
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

from config import config, RoleplayMode
from character import Character
from memory import MemoryEntry, HierarchicalMemoryManager
from analyzer import MessageAnalysisResult
from progression import StoryProgressionState

logger = logging.getLogger(__name__)

class LMStudioClient:
    """Offline REST client for LM Studio OpenAI-compatible API."""

    def __init__(self, api_base_url: Optional[str] = None, model_name: Optional[str] = None):
        self.api_base_url = (api_base_url or config.lm_studio.api_base_url).rstrip('/')
        self.model_name = model_name or config.lm_studio.model_name
        self.timeout = config.lm_studio.timeout_seconds

    def check_connection(self) -> tuple[bool, str]:
        """Test connection to LM Studio local server."""
        url = f"{self.api_base_url}/models"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OfflineRoleplayAI/1.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    models = [m.get("id", "") for m in data.get("data", [])]
                    model_str = ", ".join(models) if models else "Connected (no model ID list)"
                    return True, f"LM Studio online at {self.api_base_url}. Active models: {model_str}"
                return False, f"LM Studio returned status code {response.status}"
        except urllib.error.URLError as e:
            return False, f"Could not connect to LM Studio at {self.api_base_url}: {e.reason}"
        except Exception as e:
            return False, f"LM Studio connection error: {e}"

    def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None
    ) -> str:
        """Send chat messages to LM Studio and return generated response string."""
        url = f"{self.api_base_url}/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature if temperature is not None else config.lm_studio.temperature,
            "top_p": config.lm_studio.top_p,
            "max_tokens": max_tokens if max_tokens is not None else config.lm_studio.max_tokens,
            "stop": stop or config.lm_studio.stop_sequences,
            "stream": False
        }

        json_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=json_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "OfflineRoleplayAI/1.0"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    resp_obj = json.loads(response.read().decode('utf-8'))
                    choices = resp_obj.get("choices", [])
                    if choices and "message" in choices[0]:
                        return choices[0]["message"].get("content", "").strip()
                    return "[No content returned from LM Studio]"
                else:
                    logger.error(f"LM Studio API error status {response.status}")
                    return f"[Error: LM Studio returned status {response.status}]"
        except urllib.error.URLError as e:
            logger.error(f"LM Studio URLError: {e}")
            return f"[LM Studio Connection Error: Ensure LM Studio server is running at {self.api_base_url}]"
        except Exception as e:
            logger.error(f"LM Studio Exception: {e}")
            return f"[Generation Error: {e}]"

class ContextBudgetManager:
    """Manages token context limits and dynamically trims context items."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count (approx 3.8 chars per token for English)."""
        return int(len(text) / 3.8) + 1

    @classmethod
    def fit_messages_in_budget(
        cls,
        system_message: Dict[str, str],
        chat_history: List[Dict[str, str]],
        max_context_tokens: int = 8192,
        reserved_response_tokens: int = 1024
    ) -> List[Dict[str, str]]:
        """Trim chat history from the top to ensure system message + history fits budget."""
        budget = max_context_tokens - reserved_response_tokens
        sys_tokens = cls.estimate_tokens(system_message.get("content", ""))
        available_history_budget = max(500, budget - sys_tokens)

        trimmed_history: List[Dict[str, str]] = []
        current_tokens = 0

        # Add messages from newest to oldest until budget is exhausted
        for msg in reversed(chat_history):
            msg_tokens = cls.estimate_tokens(msg.get("content", ""))
            if current_tokens + msg_tokens > available_history_budget:
                break
            trimmed_history.insert(0, msg)
            current_tokens += msg_tokens

        return [system_message] + trimmed_history

class Summarizer:
    """Automated summary engine using LM Studio."""

    def __init__(self, llm_client: LMStudioClient):
        self.llm_client = llm_client

    def summarize_conversation(self, chat_history: List[Dict[str, str]], existing_summary: str = "") -> str:
        """Summarize older conversation history into concise key events & plot points."""
        chat_text = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in chat_history])
        
        prompt = (
            "Summarize the following roleplay session conversation.\n"
            "Retain key character actions, major decisions, revealed secrets, narrative milestones, and plot progression.\n"
            f"Existing Story Summary:\n{existing_summary or 'None'}\n\n"
            f"Recent Conversation to Summarize:\n{chat_text}\n\n"
            "Output concise bullet points capturing the updated state of the story:"
        )

        messages = [
            {"role": "system", "content": "You are an expert story summarizer and roleplay chronicler."},
            {"role": "user", "content": prompt}
        ]

        summary_result = self.llm_client.generate_chat_completion(messages, temperature=0.3, max_tokens=500)
        return summary_result.strip()

class PromptBuilder:
    """Dynamic Roleplay Prompt Construction Engine."""

    @classmethod
    def build_system_prompt(
        cls,
        active_character: Character,
        mode: RoleplayMode,
        story_info: Dict[str, str],
        retrieved_memories: List[MemoryEntry],
        party_characters: Optional[List[Character]] = None,
        message_analysis: Optional[MessageAnalysisResult] = None,
        story_progression: Optional[StoryProgressionState] = None
    ) -> str:
        """Construct comprehensive system prompt according to selected roleplay mode."""
        lines = []

        # Core Identity Directives
        lines.append("=== MANDATORY SYSTEM DIRECTIVES ===")
        lines.append("You are operating as a pure Character Simulation Engine.")
        lines.append("You MUST NEVER break character, mention AI limits, or output generic assistant pleasantries.")
        lines.append("Always remain 100% in character with full fidelity to tone, vocabulary, emotion, and rules.")

        # Active Mode Context
        lines.append(f"\n=== ROLEPLAY MODE: {mode.value.upper()} ===")
        if mode == RoleplayMode.SINGLE_CHARACTER:
            lines.append(f"You are roleplaying as '{active_character.character_name}'. Respond solely as this character.")
        elif mode == RoleplayMode.MULTI_CHARACTER:
            party_names = ", ".join([c.character_name for c in (party_characters or [active_character])])
            lines.append(f"Active Character Roster: {party_names}.")
            lines.append("You can respond as the active character or format responses for multiple characters if relevant.")
        elif mode == RoleplayMode.NARRATOR_ONLY:
            lines.append("You are acting strictly as the Story Narrator / Game Master. Describe environment, NPC reactions, and consequences.")
        elif mode == RoleplayMode.CHARACTER_NARRATOR:
            lines.append(f"Combine third-person narration of the scene with active dialogue as '{active_character.character_name}'.")
        elif mode == RoleplayMode.INTERACTIVE_STORY:
            lines.append("Provide rich narrative choices and describe outcomes based on user decisions.")
        elif mode == RoleplayMode.SANDBOX:
            lines.append("Unrestricted creative sandbox mode. Respond in accordance with world rules and active character.")

        # Story & Setting Context
        if story_info:
            lines.append("\n=== STORY & WORLD CONTEXT ===")
            if story_info.get("title"): lines.append(f"Story Title: {story_info['title']}")
            if story_info.get("genre"): lines.append(f"Genre: {story_info['genre']}")
            if story_info.get("world"): lines.append(f"World/Setting: {story_info['world']}")
            if story_info.get("scenario"): lines.append(f"Current Scenario: {story_info['scenario']}")
            if story_info.get("goal"): lines.append(f"Current Objective: {story_info['goal']}")

        # Dynamic Story Progression & Arc Context
        if story_progression:
            lines.append("\n=== STORY PROGRESSION & NARRATIVE ARC ===")
            lines.append(f"Story Arc Phase: {story_progression.story_arc.value}")
            lines.append(f"Chapter: {story_progression.chapter} | Turn Count: {story_progression.total_turns} | Tension Pacing: {story_progression.tension_level}")
            lines.append(f"Relationship Status: {story_progression.relationship_status} (Trust Score: {story_progression.relationship_trust_score:.1f}/10.0)")
            if story_progression.active_objectives:
                lines.append(f"Active Story Objectives: {', '.join(story_progression.active_objectives)}")
            if story_progression.completed_milestones:
                recent_ms = story_progression.completed_milestones[-3:]
                lines.append(f"Recent Narrative Milestones: {'; '.join(recent_ms)}")

            # Evolved Story Progression Behaviors
            bev = story_progression.evolved_behaviors
            if bev and (bev.trust_unlocked_traits or bev.arc_adapted_rules or bev.milestone_acquired_behaviors):
                lines.append("\n=== EVOLVED STORY PROGRESSION BEHAVIORS (This Story Only) ===")
                if bev.trust_unlocked_traits:
                    lines.append(f"Trust-Unlocked Traits: {', '.join(bev.trust_unlocked_traits)}")
                if bev.arc_adapted_rules:
                    lines.append(f"Story Arc Behavior Rules: {' '.join(bev.arc_adapted_rules)}")
                if bev.milestone_acquired_behaviors:
                    lines.append(f"Milestone-Acquired Directives: {'; '.join(bev.milestone_acquired_behaviors)}")

            # Dynamic Situational Adaptation
            sit = story_progression.situational_adaptation
            if sit and sit.situation_type != "Casual":
                lines.append("\n=== DYNAMIC SITUATIONAL ADAPTATION ===")
                lines.append(f"Situation Type: {sit.situation_type} | Danger Level: {sit.danger_level}")
                lines.append(f"Situational Mood Overlay: {sit.dynamic_mood}")
                lines.append(f"Situational Voice & Delivery: {sit.dynamic_speaking_style}")
                if sit.situational_rules:
                    lines.append(f"Temporary Scene Directives: {' '.join(sit.situational_rules)}")

        # Latest Message Analysis & Intent Understanding
        if message_analysis:
            lines.append("\n=== LATEST MESSAGE UNDERSTANDING & INTENT ===")
            lines.append(f"Detected Intent: {message_analysis.intent.value.upper()}")
            lines.append(f"Perceived Emotional Tone: {message_analysis.emotional_tone}")
            if message_analysis.physical_actions:
                lines.append(f"Physical Action/Event in Scene: {message_analysis.physical_actions}")
            if message_analysis.spoken_dialogue:
                lines.append(f"Spoken Dialogue: {message_analysis.spoken_dialogue}")
            if message_analysis.extracted_entities:
                lines.append(f"Key Mentioned Entities: {', '.join(message_analysis.extracted_entities)}")

        # Character Persona Definition (Injecting Detailed 60+ Fields)
        lines.append("\n=== BASE CHARACTER PERSONA (CORE TEMPLATE) ===")
        lines.append(f"Name: {active_character.character_name} (Nickname: {active_character.nickname or 'N/A'})")
        lines.append(f"Age: {active_character.age} | Gender: {active_character.gender} | Occupation: {active_character.occupation}")
        lines.append(f"Species: {active_character.species} | Language: {active_character.language}")
        lines.append(f"Appearance: {active_character.appearance}")
        lines.append(f"Background: {active_character.background}")
        lines.append(f"Core Personality Traits: {', '.join(active_character.personality_traits)}")
        lines.append(f"Goals: {', '.join(active_character.goals)}")
        lines.append(f"Motivations: {', '.join(active_character.motivations)}")
        lines.append(f"Beliefs & Values: {', '.join(active_character.beliefs)} | {', '.join(active_character.values)}")
        lines.append(f"Fears: {', '.join(active_character.fears)}")
        lines.append(f"Speaking Style: {active_character.speaking_style}")
        lines.append(f"Vocabulary & Formality: {active_character.vocabulary} ({active_character.formality})")
        lines.append(f"Emotion & Humor: {active_character.emotion_style} | Humor: {active_character.humor_level}")
        lines.append(f"Current Mood: {active_character.current_mood}")
        lines.append(f"Current Location: {active_character.current_location}")
        lines.append(f"Current Situation: {active_character.current_situation}")

        if active_character.behavior_rules:
            lines.append(f"Core Behavior Rules: {' '.join(active_character.behavior_rules)}")
        if active_character.catchphrases:
            lines.append(f"Catchphrases: {', '.join(active_character.catchphrases)}")
        if active_character.custom_instructions:
            lines.append(f"Custom Instructions: {active_character.custom_instructions}")

        # Relevant Retrieved Long-Term Memories
        if retrieved_memories:
            lines.append("\n=== RELEVANT RETRIEVED MEMORIES & FACTS ===")
            for mem in retrieved_memories:
                lines.append(f"- [{mem.memory_type.value.upper()}] {mem.content}")

        # Roleplay Formatting Directives
        lines.append("\n=== FORMATTING & ACTION PARSING DIRECTIVES ===")
        lines.append("- Text inside parentheses `(action or physical event)` or asterisks `*action*` in User input represents a physical action, event, gesture, or environmental change performed by the User in the scene.")
        lines.append("- Parenthesized text is NOT spoken dialogue. Treat it as a physical event occurring in the room/scene and react to it physically and narratively.")
        lines.append("- Text outside parentheses is spoken dialogue addressed to you.")
        lines.append("- In your responses, use *asterisks* for physical actions, gestures, and scene narration.")
        lines.append("- Use regular text or quotation marks for spoken dialogue.")
        lines.append("- Keep response style aligned with the character's preferences.")

        return "\n".join(lines)
