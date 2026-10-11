"""
Story Progression, Narrative Arc Tracking, and Situational Adaptability Module.
Tracks narrative phase, pacing/tension, active objectives, completed milestones,
relationship trust state, situational adaptation, and progression-based behavior evolution.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional

class StoryArcPhase(str, Enum):
    SETUP = "Setup & Exposition"
    RISING_ACTION = "Rising Action"
    CLIMAX = "Climax"
    FALLING_ACTION = "Falling Action"
    RESOLUTION = "Resolution"

@dataclass
class SituationalAdaptationState:
    danger_level: str = "Low"  # "Low", "Moderate", "High", "Critical / Life-Threatening"
    situation_type: str = "Casual"  # "Casual", "Combat", "Stealth", "Negotiation", "Investigation", "Crisis / Comfort"
    dynamic_mood: str = "Calm"
    dynamic_speaking_style: str = "Standard"
    situational_rules: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "danger_level": self.danger_level,
            "situation_type": self.situation_type,
            "dynamic_mood": self.dynamic_mood,
            "dynamic_speaking_style": self.dynamic_speaking_style,
            "situational_rules": self.situational_rules
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SituationalAdaptationState":
        if not data:
            return cls()
        return cls(
            danger_level=data.get("danger_level", "Low"),
            situation_type=data.get("situation_type", "Casual"),
            dynamic_mood=data.get("dynamic_mood", "Calm"),
            dynamic_speaking_style=data.get("dynamic_speaking_style", "Standard"),
            situational_rules=data.get("situational_rules", [])
        )

@dataclass
class ProgressionBehaviorState:
    trust_unlocked_traits: List[str] = field(default_factory=list)
    arc_adapted_rules: List[str] = field(default_factory=list)
    milestone_acquired_behaviors: List[str] = field(default_factory=list)
    story_specific_catchphrases: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trust_unlocked_traits": self.trust_unlocked_traits,
            "arc_adapted_rules": self.arc_adapted_rules,
            "milestone_acquired_behaviors": self.milestone_acquired_behaviors,
            "story_specific_catchphrases": self.story_specific_catchphrases
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProgressionBehaviorState":
        if not data:
            return cls()
        return cls(
            trust_unlocked_traits=data.get("trust_unlocked_traits", []),
            arc_adapted_rules=data.get("arc_adapted_rules", []),
            milestone_acquired_behaviors=data.get("milestone_acquired_behaviors", []),
            story_specific_catchphrases=data.get("story_specific_catchphrases", [])
        )

@dataclass
class StoryProgressionState:
    story_arc: StoryArcPhase = StoryArcPhase.SETUP
    chapter: int = 1
    scene_turn: int = 1
    total_turns: int = 0
    tension_level: str = "Moderate"
    active_objectives: List[str] = field(default_factory=list)
    completed_milestones: List[str] = field(default_factory=list)
    relationship_trust_score: float = 5.0  # 0.0 (Hostile) to 10.0 (Unshakeable)
    relationship_status: str = "Neutral / Acquaintance"
    current_location_state: str = "Initial Scene"
    situational_adaptation: SituationalAdaptationState = field(default_factory=SituationalAdaptationState)
    evolved_behaviors: ProgressionBehaviorState = field(default_factory=ProgressionBehaviorState)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "story_arc": self.story_arc.value,
            "chapter": self.chapter,
            "scene_turn": self.scene_turn,
            "total_turns": self.total_turns,
            "tension_level": self.tension_level,
            "active_objectives": self.active_objectives,
            "completed_milestones": self.completed_milestones,
            "relationship_trust_score": self.relationship_trust_score,
            "relationship_status": self.relationship_status,
            "current_location_state": self.current_location_state,
            "situational_adaptation": self.situational_adaptation.to_dict(),
            "evolved_behaviors": self.evolved_behaviors.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoryProgressionState":
        if not data:
            return cls()
        arc_val = data.get("story_arc", StoryArcPhase.SETUP.value)
        try:
            arc_enum = StoryArcPhase(arc_val)
        except ValueError:
            arc_enum = StoryArcPhase.SETUP

        return cls(
            story_arc=arc_enum,
            chapter=int(data.get("chapter", 1)),
            scene_turn=int(data.get("scene_turn", 1)),
            total_turns=int(data.get("total_turns", 0)),
            tension_level=data.get("tension_level", "Moderate"),
            active_objectives=data.get("active_objectives", []),
            completed_milestones=data.get("completed_milestones", []),
            relationship_trust_score=float(data.get("relationship_trust_score", 5.0)),
            relationship_status=data.get("relationship_status", "Neutral / Acquaintance"),
            current_location_state=data.get("current_location_state", "Initial Scene"),
            situational_adaptation=SituationalAdaptationState.from_dict(data.get("situational_adaptation", {})),
            evolved_behaviors=ProgressionBehaviorState.from_dict(data.get("evolved_behaviors", {}))
        )

class StoryProgressionTracker:
    """Manages and dynamically updates story arc, milestone tracking, trust level, situational adaptation, and progression behaviors."""

    def __init__(self, state: Optional[StoryProgressionState] = None):
        self.state = state or StoryProgressionState()

    def advance_turn(
        self,
        user_intent: str = "",
        emotion: str = "",
        message_analysis: Any = None,
        location: str = ""
    ) -> None:
        """Advance turn counters, evaluate narrative pacing shift, and compute behavioral adaptations."""
        self.state.scene_turn += 1
        self.state.total_turns += 1

        if location:
            self.state.current_location_state = location

        # Advance Chapter every 15 turns automatically if not already advanced manually
        if self.state.scene_turn > 15:
            self.state.chapter += 1
            self.state.scene_turn = 1

        # Update Story Arc Phase based on total turns / milestones
        self._update_story_arc()

        # Update Trust level slightly based on tone
        self._adjust_trust_from_emotion(emotion)

        # Update Situational Adaptations & Progression Evolved Behaviors
        self.evaluate_situational_adaptation(message_analysis)
        self.update_progression_behaviors()

    def add_milestone(self, milestone: str) -> None:
        """Record a completed plot milestone."""
        if milestone and milestone not in self.state.completed_milestones:
            self.state.completed_milestones.append(milestone)
            self._update_story_arc()
            self.update_progression_behaviors()

    def add_objective(self, objective: str) -> None:
        """Add a new active quest/objective."""
        if objective and objective not in self.state.active_objectives:
            self.state.active_objectives.append(objective)

    def complete_objective(self, objective: str) -> None:
        """Mark an objective as completed and move to milestone list."""
        if objective in self.state.active_objectives:
            self.state.active_objectives.remove(objective)
        self.add_milestone(f"Objective Completed: {objective}")

    def adjust_trust(self, delta: float) -> None:
        """Adjust trust score (-5.0 to +5.0) and update relationship status label and evolved behaviors."""
        self.state.relationship_trust_score = max(0.0, min(10.0, self.state.relationship_trust_score + delta))
        
        score = self.state.relationship_trust_score
        if score >= 9.0:
            self.state.relationship_status = "Unshakeable Bond / Soul Connection"
        elif score >= 7.5:
            self.state.relationship_status = "Close Confidant / Highly Trusted"
        elif score >= 6.0:
            self.state.relationship_status = "Trusted Ally / Warm Friend"
        elif score >= 4.0:
            self.state.relationship_status = "Neutral / Acquaintance"
        elif score >= 2.0:
            self.state.relationship_status = "Strained / Distrustful"
        else:
            self.state.relationship_status = "Hostile Enemy / Open Conflict"

        self.update_progression_behaviors()

    def evaluate_situational_adaptation(self, message_analysis: Any = None) -> SituationalAdaptationState:
        """Dynamically evaluate situational danger, mood, speaking style, and scene rules."""
        actions = getattr(message_analysis, "action_parts", []) if message_analysis else []
        actions_str = " ".join(actions).lower()
        emotion = getattr(message_analysis, "emotional_tone", "").lower() if message_analysis else ""
        intent_val = getattr(message_analysis, "intent", "").value if hasattr(getattr(message_analysis, "intent", None), "value") else str(getattr(message_analysis, "intent", ""))

        danger = "Low"
        sit_type = "Casual"
        mood = "Calm & Engaged"
        speaking_style = "Natural & Conversational"
        rules = []

        # Check Combat / Danger Cues
        combat_keywords = ["attack", "strike", "sword", "fight", "draw", "punch", "slash", "shoot", "kill", "fire", "enemy"]
        stealth_keywords = ["whisper", "sneak", "stealth", "shadow", "quiet", "hide", "creep", "cautious"]
        crisis_keywords = ["gasp", "injure", "wound", "bleed", "help", "save", "cry", "fear", "panic", "collapse"]
        investigate_keywords = ["inspect", "examine", "search", "study", "look", "analyze", "check"]

        if any(kw in actions_str or kw in emotion for kw in combat_keywords):
            sit_type = "Combat / Tactical"
            danger = "High" if "High" in self.state.tension_level or "Intense" in self.state.tension_level else "Moderate"
            mood = "Tense & Combat-Ready"
            speaking_style = "Direct, Urgent, Sharp"
            rules = [
                "Maintain high tactical alertness and respond swiftly to physical threats.",
                "Keep dialogue concise and focused on battle awareness."
            ]
        elif any(kw in actions_str or kw in emotion for kw in stealth_keywords):
            sit_type = "Stealth / Covert"
            danger = "Moderate"
            mood = "Vigilant & Secretive"
            speaking_style = "Whispered, Hushed, Subdued"
            rules = [
                "Speak in hushed tones and maintain stealth awareness.",
                "Avoid unnecessary noise or sudden overt actions."
            ]
        elif any(kw in actions_str or kw in emotion for kw in crisis_keywords) or "Anxious" in emotion:
            sit_type = "Crisis / Emotional Support"
            danger = "Moderate"
            mood = "Focused & Reassuring"
            speaking_style = "Calm, Steady, Empathetic"
            rules = [
                "Provide immediate grounding support or medical/tactical assistance.",
                "Acknowledge the emotional tension of the moment."
            ]
        elif any(kw in actions_str for kw in investigate_keywords) or intent_val == "question":
            sit_type = "Investigation"
            danger = "Low"
            mood = "Observant & Analytical"
            speaking_style = "Inquisitive and Deliberate"
            rules = [
                "Focus attention on environmental clues, subtle details, and evidence."
            ]

        # Adjust danger if tension level is High/Climax
        if self.state.story_arc == StoryArcPhase.CLIMAX:
            danger = "Critical / Life-Threatening" if danger == "High" else "High"
            if not rules:
                rules = ["High narrative tension: heighten urgency and emotional stakes."]

        adaptation = SituationalAdaptationState(
            danger_level=danger,
            situation_type=sit_type,
            dynamic_mood=mood,
            dynamic_speaking_style=speaking_style,
            situational_rules=rules
        )
        self.state.situational_adaptation = adaptation
        return adaptation

    def update_progression_behaviors(self) -> ProgressionBehaviorState:
        """Evolve character behaviors based on trust score, story arc, and milestones."""
        score = self.state.relationship_trust_score
        arc = self.state.story_arc
        ms_list = self.state.completed_milestones

        trust_traits = []
        arc_rules = []
        ms_behaviors = []

        # 1. Trust-unlocked traits
        if score >= 8.5:
            trust_traits = ["unshakably loyal", "openly vulnerable", "deeply protective"]
        elif score >= 6.5:
            trust_traits = ["warmly trusting", "cooperative", "willing to share secrets"]
        elif score <= 2.5:
            trust_traits = ["coldly suspicious", "guarded", "hostile"]
        elif score <= 4.0:
            trust_traits = ["cautious", "skeptical"]

        # 2. Story Arc Adapted Rules
        if arc == StoryArcPhase.SETUP:
            arc_rules = ["Act exploratory and establish initial boundaries."]
        elif arc == StoryArcPhase.RISING_ACTION:
            arc_rules = ["Show rising engagement with active plot objectives."]
        elif arc == StoryArcPhase.CLIMAX:
            arc_rules = [
                "Demonstrate intense emotional investment in current high-stakes crisis.",
                "Prioritize crucial decisions and shared survival."
            ]
        elif arc == StoryArcPhase.FALLING_ACTION:
            arc_rules = ["Reflect on the aftermath of major climax events."]
        elif arc == StoryArcPhase.RESOLUTION:
            arc_rules = ["Exhibit a sense of closure, wisdom gained, and lasting rapport."]

        # 3. Milestone Acquired Behaviors
        for ms in ms_list[-3:]:
            clean_ms = ms.replace("Objective Completed: ", "")
            ms_behaviors.append(f"Remember and act upon past milestone: '{clean_ms}'")

        prog_behavior = ProgressionBehaviorState(
            trust_unlocked_traits=trust_traits,
            arc_adapted_rules=arc_rules,
            milestone_acquired_behaviors=ms_behaviors,
            story_specific_catchphrases=self.state.evolved_behaviors.story_specific_catchphrases
        )
        self.state.evolved_behaviors = prog_behavior
        return prog_behavior

    def format_progression_prompt_block(self) -> str:
        """Construct formatted prompt section for LLM context injection."""
        lines = []
        lines.append("=== STORY PROGRESSION & NARRATIVE ARC ===")
        lines.append(f"Story Arc Phase: {self.state.story_arc.value}")
        lines.append(f"Chapter: {self.state.chapter} | Turn Count: {self.state.total_turns} | Pacing / Tension: {self.state.tension_level}")
        lines.append(f"Relationship Status: {self.state.relationship_status} (Trust Score: {self.state.relationship_trust_score:.1f}/10.0)")
        
        if self.state.active_objectives:
            lines.append(f"Active Objectives: {', '.join(self.state.active_objectives)}")
        if self.state.completed_milestones:
            recent_ms = self.state.completed_milestones[-3:]
            lines.append(f"Recent Milestones: {'; '.join(recent_ms)}")

        # Include situational adaptation info if active
        sit = self.state.situational_adaptation
        if sit and sit.situation_type != "Casual":
            lines.append(f"Situational Mode: {sit.situation_type} | Danger Level: {sit.danger_level}")
            lines.append(f"Situational Mood Overlay: {sit.dynamic_mood} | Voice: {sit.dynamic_speaking_style}")

        # Include evolved behaviors if present
        bev = self.state.evolved_behaviors
        if bev:
            if bev.trust_unlocked_traits:
                lines.append(f"Story-Evolved Trust Traits: {', '.join(bev.trust_unlocked_traits)}")
            if bev.arc_adapted_rules:
                lines.append(f"Story Arc Directives: {' '.join(bev.arc_adapted_rules)}")

        return "\n".join(lines)

    def _update_story_arc(self) -> None:
        """Dynamically set arc phase based on total turns and milestones."""
        turns = self.state.total_turns
        ms_count = len(self.state.completed_milestones)

        if turns <= 5 and ms_count == 0:
            self.state.story_arc = StoryArcPhase.SETUP
            self.state.tension_level = "Low"
        elif turns <= 25 or ms_count < 3:
            self.state.story_arc = StoryArcPhase.RISING_ACTION
            self.state.tension_level = "Moderate"
        elif turns <= 40 or ms_count < 6:
            self.state.story_arc = StoryArcPhase.CLIMAX
            self.state.tension_level = "High / Intense"
        elif turns <= 50:
            self.state.story_arc = StoryArcPhase.FALLING_ACTION
            self.state.tension_level = "Cooling Down"
        else:
            self.state.story_arc = StoryArcPhase.RESOLUTION
            self.state.tension_level = "Calm / Concluding"

    def _adjust_trust_from_emotion(self, emotion: str) -> None:
        """Slight trust drift based on emotional tone."""
        if "Friendly" in emotion or "Warm" in emotion:
            self.adjust_trust(0.1)
        elif "Hostile" in emotion or "Aggressive" in emotion:
            self.adjust_trust(-0.2)
        elif "Secretive" in emotion:
            self.adjust_trust(-0.05)

