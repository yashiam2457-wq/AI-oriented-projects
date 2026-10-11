"""
Main CLI Application Entry Point for Offline Roleplay AI Framework.
Features interactive story starter wizard, formatted terminal UI,
runtime character switching, party management, and complete /command REPL loop.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional, List

# Try importing rich for enhanced terminal formatting, fallback to clean ANSI text if unavailable
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.markdown import Markdown
    from rich.prompt import Prompt, Confirm
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None

from config import config, RoleplayMode, StartupMode
from character import Character, CharacterManager
from memory import MemoryType
from engine import LMStudioClient, ContextBudgetManager, Summarizer, PromptBuilder
from session import SessionManager, StoryContext, PersistenceEngine
from analyzer import MessageAnalyzer, MessageAnalysisResult
from progression import StoryProgressionTracker, StoryProgressionState

# Setup logging
config.paths.logs_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=config.paths.logs_dir / "app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("Main")

def print_banner():
    """Display application startup header."""
    header = """
====================================================================
               OFFLINE ROLEPLAY AI FRAMEWORK
           Character Simulation Engine & Local Memory
====================================================================
"""
    if HAS_RICH:
        console.print(Panel("[bold cyan]OFFLINE ROLEPLAY AI FRAMEWORK[/bold cyan]\n[italic dim]Character Simulation Engine & Persistent Memory[/italic dim]", expand=False))
    else:
        print(header)

class RoleplayCLI:
    """Main REPL loop and terminal controller."""

    def __init__(self):
        self.char_manager = CharacterManager()
        self.persistence = PersistenceEngine()
        self.session_manager = SessionManager(self.persistence)
        self.llm_client = LMStudioClient()
        self.summarizer = Summarizer(self.llm_client)
        self.user_name: str = "Yash"
        self.latest_analysis: Optional[MessageAnalysisResult] = None

    def print_msg(self, text: str, style: str = "white"):
        """Helper to print formatted messages."""
        if HAS_RICH:
            console.print(text, style=style)
        else:
            print(text)

    def print_character_speech(self, char_name: str, speech: str):
        """Format and print character dialogue/narration."""
        if HAS_RICH:
            console.print(Panel(Markdown(speech), title=f"[bold green]{char_name}[/bold green]", border_style="green"))
        else:
            print(f"\n[{char_name}]:\n{speech}\n")

    def run(self):
        """Application main execution loop."""
        print_banner()

        # Step 1: Check LM Studio connectivity
        connected, conn_msg = self.llm_client.check_connection()
        if connected:
            self.print_msg(f"[SUCCESS] {conn_msg}", "bold green")
        else:
            self.print_msg(f"[WARNING] {conn_msg}", "bold yellow")
            self.print_msg("Ensure LM Studio local server is running on http://localhost:1234", "dim")

        # Step 2: Session Startup Wizard
        self.startup_wizard()

        # Step 3: Command REPL Loop
        self.repl_loop()

    def startup_wizard(self):
        """Interactive startup wizard: New Story, Load Story, Create Character, Switch Character, Quick Start."""
        while True:
            self.print_msg("\n--- STARTUP SESSION SELECTION ---", "bold cyan")
            active = self.char_manager.get_active_character()
            active_name = active.character_name if active else "None"
            self.print_msg(f"Active Persona: {active_name}", "dim")
            self.print_msg("1. Create New Story")
            self.print_msg("2. Load Previous Story / Session")
            self.print_msg("3. Create New Persona / Character")
            self.print_msg("4. Select / Switch Active Character")
            self.print_msg("5. Quick Start with Active Character")

            choice = input("\nSelect Option [1-5] (Default 1): ").strip() or "1"

            if choice == "3":
                self.create_character_wizard()
                continue
            elif choice == "4":
                self.display_character_list()
                target = input("\nEnter Character Name or ID to switch: ").strip()
                if target:
                    ok, msg = self.char_manager.switch_character(target)
                    self.print_msg(f"[{'SUCCESS' if ok else 'ERROR'}] {msg}", "bold green" if ok else "bold red")
                continue
            elif choice == "2":
                sessions = self.persistence.list_sessions()
                if sessions:
                    self.print_msg("\nSaved Sessions:", "bold yellow")
                    for idx, s in enumerate(sessions, 1):
                        cid = s.get("active_character_id", "")
                        c_obj = self.char_manager.get_character(cid) if cid else None
                        c_name = c_obj.character_name if c_obj else (cid or "Unknown Character")
                        self.print_msg(f" [{idx}] {s['session_title']} | Character: {c_name} (Session ID: {s['session_id']}) | Mode: {s['mode']}")
                    s_choice = input("\nEnter Session Number or ID: ").strip()
                    selected_id = None
                    if s_choice.isdigit() and 1 <= int(s_choice) <= len(sessions):
                        selected_id = sessions[int(s_choice) - 1]["session_id"]
                    elif s_choice:
                        selected_id = s_choice

                    if selected_id:
                        ok, msg = self.session_manager.load_session(selected_id)
                        if ok:
                            active_char = self.char_manager.get_character(self.session_manager.active_session.active_character_id)
                            if active_char:
                                self.char_manager.active_character_id = active_char.character_id
                            c_display = active_char.character_name if active_char else "Unknown"
                            self.print_msg(f"[SUCCESS] Loaded session '{self.session_manager.active_session.session_title}' | Character: {c_display} | Session ID: {selected_id}", "bold green")
                            self.display_last_conversation(selected_id)
                            break
                else:
                    self.print_msg("No saved sessions found.", "bold yellow")
                    continue
            elif choice == "1":
                self.create_new_story_wizard()
                break
            else:
                # Start or continue conversation with active character
                self.start_active_character_session()
                break

    def start_active_character_session(self):
        """Start or resume a roleplay session with the active character."""
        active_char = self.char_manager.get_active_character()
        if not active_char:
            self.print_msg("[ERROR] No active character found.", "bold red")
            return

        # Check if an existing session for this active character exists
        sessions = self.persistence.list_sessions()
        char_session = None
        for s in sessions:
            if s.get("active_character_id") == active_char.character_id or active_char.character_name.lower() in s.get("session_title", "").lower():
                char_session = s
                break

        if char_session:
            # Load existing session and display previous conversation
            ok, msg = self.session_manager.load_session(char_session["session_id"])
            if ok:
                self.char_manager.active_character_id = active_char.character_id
                self.print_msg(f"[SUCCESS] Resumed session '{char_session['session_title']}' | Character: {active_char.character_name} | Session ID: {char_session['session_id']}", "bold green")
                self.display_last_conversation(char_session["session_id"])
                return

        # If no previous session exists, create a new session for this character
        self.print_msg(f"\n[Starting new conversation with '{active_char.character_name}']", "bold cyan")
        story = StoryContext(
            title=f"Conversation with {active_char.character_name}",
            genre=active_char.species or "Roleplay",
            world=active_char.nationality or "Roleplay Realm",
            setting=active_char.current_location or "Active Location",
            scenario=active_char.current_situation or "Engaging in conversation.",
            goal=f"Interact and roleplay with {active_char.character_name}.",
            main_character_id=active_char.character_id
        )

        self.session_manager.create_new_session(
            title=f"Conversation with {active_char.character_name}",
            mode=RoleplayMode.SINGLE_CHARACTER,
            story=story,
            active_char_id=active_char.character_id
        )

        # Generate default opening conversation scene from active character
        self.print_msg(f"\n[Generating opening scene for {active_char.character_name}...]", "dim")
        opening_prompt = (
            f"Describe the immediate physical scene and deliver your opening action and greeting as {active_char.character_name}. "
            f"Location: {active_char.current_location}. Situation: {active_char.current_situation}."
        )
        self.process_chat_turn(opening_prompt, is_opening=True)

    def display_last_conversation(self, session_id: str, limit: int = 6):
        """Display recent conversation history before resuming a loaded session."""
        active_char = self.char_manager.get_active_character()
        char_name = active_char.character_name if active_char else "Unknown Character"

        history = self.persistence.get_chat_history(session_id, limit=limit)
        if not history:
            self.print_msg(f"\n[No previous conversation history found for {char_name} (Session ID: {session_id})]", "dim")
            return

        self.print_msg(f"\n=== RECENT CONVERSATION HISTORY (Character: {char_name} | Session ID: {session_id}) ===", "bold cyan")
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            char_id = msg.get("character_id")

            if role == "user":
                self.print_msg(f"\n{self.user_name}: {content}", "bold blue")
            else:
                char_obj = self.char_manager.get_character(char_id) if char_id else active_char
                speaker_name = char_obj.character_name if char_obj else "Narrator"
                self.print_character_speech(speaker_name, content)
        self.print_msg("================================================================================\n", "bold cyan")

    def create_character_wizard(self) -> Optional[Character]:
        """Interactive CLI wizard to create a new character persona."""
        self.print_msg("\n--- CREATE NEW CHARACTER PERSONA ---", "bold cyan")
        name = input("Character Name (e.g. Lyra Nightshade): ").strip()
        if not name:
            self.print_msg("Character creation cancelled (name required).", "bold red")
            return None

        nickname = input(f"Nickname (Default: {name}): ").strip() or name
        char_id = name.lower().replace(" ", "_")
        
        age = input("Age (Default: 25): ").strip() or "25"
        gender = input("Gender (Default: Female): ").strip() or "Female"
        occupation = input("Occupation (Default: Adventurer / Rogue): ").strip() or "Adventurer / Rogue"
        species = input("Species (Default: Human): ").strip() or "Human"
        
        self.print_msg("\nPersona Details (Press Enter to use defaults):", "dim")
        background = input("Background (Default: Mysterious past): ").strip() or "Mysterious past"
        personality = input("Personality Traits (comma separated): ").strip()
        traits = [t.strip() for t in personality.split(",") if t.strip()] or ["observant", "pragmatic"]

        new_char = Character(
            character_id=char_id,
            character_name=name,
            nickname=nickname,
            age=age,
            gender=gender,
            occupation=occupation,
            species=species,
            background=background,
            personality_traits=traits
        )

        saved_path = self.char_manager.save_character(new_char)
        self.char_manager.active_character_id = new_char.character_id
        if new_char.character_id not in self.char_manager.active_party_ids:
            self.char_manager.active_party_ids.append(new_char.character_id)

        self.print_msg(f"[SUCCESS] Created and activated character persona '{name}' ({char_id})", "bold green")
        self.print_msg(f"Saved to: {saved_path}", "dim")
        return new_char

    def create_new_story_wizard(self):
        """Wizard to construct a new story context and roleplay session."""
        self.print_msg("\n--- START NEW ROLEPLAY STORY ---", "bold cyan")

        active_char = self.char_manager.get_active_character()
        if not active_char:
            self.print_msg("[WARNING] No active character selected. Select or create one first.", "bold yellow")
            self.display_character_list()
            target = input("\nEnter Character Name or ID (or press Enter to create new): ").strip()
            if target:
                ok, msg = self.char_manager.switch_character(target)
                self.print_msg(f"[{'SUCCESS' if ok else 'ERROR'}] {msg}", "bold green" if ok else "bold red")
                active_char = self.char_manager.get_active_character()
            else:
                active_char = self.create_character_wizard()

        if not active_char:
            active_char = self.char_manager._create_default_character()

        self.print_msg(f"\nActive Persona for this story: '{active_char.character_name}'", "bold green")
        change_char = input("Switch or create character persona for this story first? [y/N]: ").strip().lower()
        if change_char == 'y':
            self.print_msg("1. Select existing persona")
            self.print_msg("2. Create brand new persona")
            c_opt = input("Select [1-2] (Default 1): ").strip() or "1"
            if c_opt == "2":
                self.create_character_wizard()
            else:
                self.display_character_list()
                target = input("\nEnter Character Name or ID to switch: ").strip()
                if target:
                    ok, msg = self.char_manager.switch_character(target)
                    self.print_msg(f"[{'SUCCESS' if ok else 'ERROR'}] {msg}", "bold green" if ok else "bold red")
            active_char = self.char_manager.get_active_character()

        title = input("\nStory Title (Default: Fantasy Journey): ").strip() or "Fantasy Journey"
        genre = input("Genre (Default: Dark Fantasy): ").strip() or "Dark Fantasy"
        theme = input("Theme (Default: Discovery & Mystery): ").strip() or "Discovery & Mystery"
        world = input("World / Realm Name (Default: Elandria): ").strip() or "Elandria"
        setting = input("Setting / Location (Default: The Whispering Forest): ").strip() or "The Whispering Forest"
        scenario = input("Initial Scenario (Default: Investigating mysterious ruins): ").strip() or "Investigating mysterious ruins"
        goal = input("Main Objective (Default: Find the lost relic): ").strip() or "Find the lost relic"

        self.print_msg("\nSelect Roleplay Mode:", "bold yellow")
        self.print_msg("1. Single Character")
        self.print_msg("2. Multi Character Party")
        self.print_msg("3. Narrator Only")
        self.print_msg("4. Character + Narrator")
        self.print_msg("5. Interactive Story")
        self.print_msg("6. Sandbox Mode")
        mode_choice = input("Select Mode [1-6] (Default 1): ").strip() or "1"

        mode_map = {
            "1": RoleplayMode.SINGLE_CHARACTER,
            "2": RoleplayMode.MULTI_CHARACTER,
            "3": RoleplayMode.NARRATOR_ONLY,
            "4": RoleplayMode.CHARACTER_NARRATOR,
            "5": RoleplayMode.INTERACTIVE_STORY,
            "6": RoleplayMode.SANDBOX
        }
        selected_mode = mode_map.get(mode_choice, RoleplayMode.SINGLE_CHARACTER)

        story = StoryContext(
            title=title, genre=genre, theme=theme, world=world,
            setting=setting, scenario=scenario, goal=goal,
            main_character_id=active_char.character_id if active_char else "default_hero",
            user_name=self.user_name
        )

        session = self.session_manager.create_new_session(
            title=title, mode=selected_mode, story=story,
            active_char_id=active_char.character_id if active_char else "default_hero"
        )

        # Startup Mode (Auto generate scene vs User first message)
        self.print_msg("\nStartup Mode:", "bold yellow")
        self.print_msg("1. Automatically generate first opening scene")
        self.print_msg("2. Write first message yourself")
        start_choice = input("Select Option [1-2] (Default 1): ").strip() or "1"

        if start_choice == "1":
            self.print_msg("\n[Generating opening scene...]", "dim")
            opening_prompt = f"Describe the opening scene for {title}. Scenario: {scenario}. Setting: {setting}."
            self.process_chat_turn(opening_prompt, is_opening=True)

    def repl_loop(self):
        """Main REPL command and chat loop."""
        self.print_msg("\n=== ROLEPLAY ENGINE ACTIVE ===", "bold green")
        self.print_msg("Type '/help' for a list of terminal commands. Type '/exit' to quit.\n", "dim")

        while True:
            try:
                active_char = self.char_manager.get_active_character()
                char_label = active_char.character_name if active_char else "Persona"
                user_input = input(f"\n{self.user_name} (Persona: {char_label}) > ").strip()

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    if not self.handle_command(user_input):
                        break
                else:
                    self.process_chat_turn(user_input)

            except (KeyboardInterrupt, EOFError):
                self.print_msg("\nExiting and saving session...", "bold yellow")
                self.session_manager.save_current_session()
                break

    def process_chat_turn(self, user_input: str, is_opening: bool = False):
        """Process a single turn of user interaction and generate AI response."""
        session = self.session_manager.active_session
        if not session:
            self.print_msg("[ERROR] No active session loaded.", "bold red")
            return

        active_char = self.char_manager.get_active_character()
        if not active_char:
            self.print_msg("[ERROR] No active character selected. Use /switch.", "bold red")
            return

        # Perform Message Understanding Analysis
        analysis = MessageAnalyzer.analyze_message(
            user_input, user_name=self.user_name, active_char_name=active_char.character_name
        )
        self.latest_analysis = analysis

        # Auto-seed memories from message analysis
        if self.session_manager.memory_manager and analysis.auto_memories:
            for m_type, m_content, m_imp in analysis.auto_memories:
                self.session_manager.memory_manager.add_memory(
                    m_type, m_content, character_id=active_char.character_id, importance=m_imp
                )

        # Advance Story Arc & Progression Tracking
        prog_tracker = StoryProgressionTracker(session.progression)
        prog_tracker.advance_turn(
            user_intent=analysis.intent.value,
            emotion=analysis.emotional_tone,
            message_analysis=analysis,
            location=active_char.current_location
        )

        # Save user message to database history
        if not is_opening:
            self.persistence.add_chat_message(session.session_id, "user", user_input)

        # Retrieve relevant memories
        retrieved_memories = []
        if self.session_manager.memory_manager:
            retrieved_memories = self.session_manager.memory_manager.search_memories(
                user_input, top_k=config.memory.max_retrieved_memories, character_id=active_char.character_id
            )

        # Fetch recent chat history
        raw_history = self.persistence.get_chat_history(session.session_id, limit=config.memory.max_recent_chat_turns)
        formatted_history = []
        for h in raw_history:
            role = "user" if h["role"] == "user" else "assistant"
            formatted_history.append({"role": role, "content": h["content"]})

        # Build System Prompt with Message Understanding & Story Progression
        party_chars = self.char_manager.list_party()
        system_prompt = PromptBuilder.build_system_prompt(
            active_character=active_char,
            mode=session.mode,
            story_info=session.story.__dict__,
            retrieved_memories=retrieved_memories,
            party_characters=party_chars,
            message_analysis=analysis,
            story_progression=session.progression
        )

        system_msg = {"role": "system", "content": system_prompt}

        # Truncate to context budget
        final_messages = ContextBudgetManager.fit_messages_in_budget(
            system_msg, formatted_history, max_context_tokens=config.lm_studio.context_window_size
        )

        # Generate response from LM Studio
        response_text = self.llm_client.generate_chat_completion(final_messages)

        # Save AI response to DB
        speaker_name = "Narrator" if session.mode == RoleplayMode.NARRATOR_ONLY else active_char.character_name
        self.persistence.add_chat_message(session.session_id, "assistant", response_text, character_id=active_char.character_id)

        # Display formatted response
        self.print_character_speech(speaker_name, response_text)

        # Background summarization trigger check
        if len(raw_history) >= config.memory.max_recent_chat_turns:
            new_summary = self.summarizer.summarize_conversation(formatted_history, session.story_summary)
            session.story_summary = new_summary
            self.session_manager.memory_manager.add_memory(
                MemoryType.STORY, f"Story Progress Summary: {new_summary}", importance=3.0
            )

    def handle_command(self, cmd_line: str) -> bool:
        """Parse and execute terminal /commands. Returns False if exiting."""
        parts = cmd_line.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in ["/exit", "/quit"]:
            self.session_manager.save_current_session()
            self.print_msg("Session saved. Goodbye!", "bold green")
            return False

        elif cmd == "/help":
            self.display_help()

        elif cmd == "/list":
            self.display_character_list()

        elif cmd == "/create":
            self.create_character_wizard()

        elif cmd == "/rename":
            if not args:
                self.display_character_list()
                active_char = self.char_manager.get_active_character()
                default_target = active_char.character_name if active_char else ""
                target_prompt = f"\nEnter Character Name or ID to rename (Default: '{default_target}'): " if default_target else "\nEnter Character Name or ID to rename: "
                target = input(target_prompt).strip() or default_target
                if not target:
                    self.print_msg("Usage: /rename <character_name_or_id> [new_name]", "bold yellow")
                else:
                    new_name = input(f"Enter new name for '{target}': ").strip()
                    if not new_name:
                        self.print_msg("[ERROR] New character name cannot be empty.", "bold red")
                    else:
                        ok, msg = self.char_manager.rename_character(target, new_name)
                        self.print_msg(f"[{'SUCCESS' if ok else 'ERROR'}] {msg}", "bold green" if ok else "bold red")
            else:
                if "->" in args:
                    target_part, new_part = args.split("->", 1)
                    target = target_part.strip()
                    new_name = new_part.strip()
                else:
                    parts_args = args.split(maxsplit=1)
                    if len(parts_args) == 2:
                        target, new_name = parts_args[0].strip(), parts_args[1].strip()
                    else:
                        target = parts_args[0].strip()
                        new_name = input(f"Enter new name for '{target}': ").strip()

                if not new_name:
                    self.print_msg("[ERROR] New character name cannot be empty.", "bold red")
                else:
                    ok, msg = self.char_manager.rename_character(target, new_name)
                    self.print_msg(f"[{'SUCCESS' if ok else 'ERROR'}] {msg}", "bold green" if ok else "bold red")

        elif cmd in ["/username", "/user"]:
            if not args:
                self.print_msg(f"Current User Name: '{self.user_name}'", "bold cyan")
                new_user_name = input("Enter new user name: ").strip()
            else:
                new_user_name = args.strip()

            if new_user_name:
                old_name = self.user_name
                self.user_name = new_user_name
                if self.session_manager.active_session and hasattr(self.session_manager.active_session.story, "user_name"):
                    self.session_manager.active_session.story.user_name = new_user_name
                self.print_msg(f"[SUCCESS] User name changed from '{old_name}' to '{self.user_name}'.", "bold green")
            else:
                self.print_msg("[ERROR] User name cannot be empty.", "bold red")

        elif cmd == "/switch":
            if not args:
                self.display_character_list()
                target = input("\nEnter Character Name or ID to switch: ").strip()
                if target:
                    ok, msg = self.char_manager.switch_character(target)
                    self.print_msg(f"[{'SUCCESS' if ok else 'ERROR'}] {msg}", "bold green" if ok else "bold red")
                    if ok and self.session_manager.active_session:
                        self.session_manager.active_session.active_character_id = self.char_manager.active_character_id
            else:
                ok, msg = self.char_manager.switch_character(args)
                self.print_msg(f"[{'SUCCESS' if ok else 'ERROR'}] {msg}", "bold green" if ok else "bold red")
                if ok and self.session_manager.active_session:
                    self.session_manager.active_session.active_character_id = self.char_manager.active_character_id

        elif cmd == "/add":
            if not args:
                self.print_msg("Usage: /add <character_name_or_id>", "bold yellow")
            else:
                ok, msg = self.char_manager.add_to_party(args)
                self.print_msg(f"[{'SUCCESS' if ok else 'ERROR'}] {msg}", "bold green" if ok else "bold red")

        elif cmd == "/remove":
            if not args:
                self.print_msg("Usage: /remove <character_name_or_id>", "bold yellow")
            else:
                ok, msg = self.char_manager.remove_from_party(args)
                self.print_msg(f"[{'SUCCESS' if ok else 'ERROR'}] {msg}", "bold green" if ok else "bold red")

        elif cmd == "/save":
            ok, msg = self.session_manager.save_current_session()
            self.print_msg(f"[{'SUCCESS' if ok else 'ERROR'}] {msg}", "bold green" if ok else "bold red")

        elif cmd == "/load":
            if not args:
                self.print_msg("Usage: /load <session_id>", "bold yellow")
            else:
                ok, msg = self.session_manager.load_session(args)
                self.print_msg(f"[{'SUCCESS' if ok else 'ERROR'}] {msg}", "bold green" if ok else "bold red")
                if ok:
                    active_char = self.char_manager.get_character(self.session_manager.active_session.active_character_id)
                    if active_char:
                        self.char_manager.active_character_id = active_char.character_id
                    self.display_last_conversation(args)

        elif cmd == "/export":
            filename = args or "session_export.json"
            export_path = config.paths.sessions_dir / filename
            ok, msg = self.session_manager.export_session_to_file(export_path)
            self.print_msg(f"[{'SUCCESS' if ok else 'ERROR'}] {msg}", "bold green" if ok else "bold red")

        elif cmd == "/import":
            if not args:
                self.print_msg("Usage: /import <filename>", "bold yellow")
            else:
                import_path = config.paths.sessions_dir / args
                ok, msg = self.session_manager.import_session_from_file(import_path)
                self.print_msg(f"[{'SUCCESS' if ok else 'ERROR'}] {msg}", "bold green" if ok else "bold red")

        elif cmd in ["/progression", "/arc", "/adapt"]:
            session = self.session_manager.active_session
            if session:
                prog = session.progression
                self.print_msg(f"\n--- NARRATIVE PROGRESSION & SITUATIONAL ADAPTATION ---", "bold cyan")
                self.print_msg(f"Story Arc Phase: {prog.story_arc.value} (Chapter {prog.chapter}, Turn {prog.total_turns})")
                self.print_msg(f"Pacing / Tension: {prog.tension_level}")
                self.print_msg(f"Relationship Status: {prog.relationship_status} (Trust Score: {prog.relationship_trust_score:.1f}/10.0)")
                
                # Situational Adaptation
                sit = prog.situational_adaptation
                if sit:
                    self.print_msg(f"\n[Situational Adaptation Mode]", "bold yellow")
                    self.print_msg(f" Mode: {sit.situation_type} | Danger Level: {sit.danger_level}")
                    self.print_msg(f" Dynamic Mood Overlay: {sit.dynamic_mood}")
                    self.print_msg(f" Dynamic Voice Delivery: {sit.dynamic_speaking_style}")
                    if sit.situational_rules:
                        self.print_msg(f" Scene Directives: {' '.join(sit.situational_rules)}")

                # Story Evolved Behaviors
                bev = prog.evolved_behaviors
                if bev and (bev.trust_unlocked_traits or bev.arc_adapted_rules or bev.milestone_acquired_behaviors):
                    self.print_msg(f"\n[Story-Evolved Behaviors (This Session Only)]", "bold yellow")
                    if bev.trust_unlocked_traits:
                        self.print_msg(f" Trust-Unlocked Traits: {', '.join(bev.trust_unlocked_traits)}")
                    if bev.arc_adapted_rules:
                        self.print_msg(f" Story Arc Directives: {' '.join(bev.arc_adapted_rules)}")
                    if bev.milestone_acquired_behaviors:
                        self.print_msg(" Milestone Directives:")
                        for mb in bev.milestone_acquired_behaviors:
                            self.print_msg(f"  - {mb}")

                if prog.active_objectives:
                    self.print_msg(f"\nActive Objectives: {', '.join(prog.active_objectives)}")
                if prog.completed_milestones:
                    self.print_msg("Completed Milestones:")
                    for ms in prog.completed_milestones:
                        self.print_msg(f" - {ms}")

        elif cmd == "/analyze":
            if self.latest_analysis:
                a = self.latest_analysis
                self.print_msg("\n--- LATEST MESSAGE TURN ANALYSIS ---", "bold cyan")
                self.print_msg(f"Detected Intent: {a.intent.value.upper()}")
                self.print_msg(f"Perceived Tone: {a.emotional_tone}")
                self.print_msg(f"Physical Action: {a.physical_actions or 'None'}")
                self.print_msg(f"Spoken Dialogue: {a.spoken_dialogue or 'None'}")
                if a.extracted_entities:
                    self.print_msg(f"Extracted Entities: {', '.join(a.extracted_entities)}")
                if a.auto_memories:
                    self.print_msg("Auto-Generated Memories:")
                    for m_type, m_content, m_imp in a.auto_memories:
                        self.print_msg(f" - [{m_type.value.upper()}] {m_content} (Imp: {m_imp})")
            else:
                self.print_msg("No message turn analyzed yet.", "bold yellow")

        elif cmd == "/story":
            session = self.session_manager.active_session
            if session:
                self.print_msg(f"\n--- STORY CONTEXT: {session.story.title} ---", "bold cyan")
                self.print_msg(f"Genre: {session.story.genre} | World: {session.story.world}")
                self.print_msg(f"Scenario: {session.story.scenario}")
                self.print_msg(f"Goal: {session.story.goal}")
                if session.story_summary:
                    self.print_msg(f"Summary: {session.story_summary}", "italic")

        elif cmd == "/summary":
            session = self.session_manager.active_session
            if session:
                self.print_msg(f"\n--- STORY SUMMARY ---", "bold cyan")
                self.print_msg(session.story_summary or "No summary generated yet.")

        elif cmd == "/memory":
            if self.session_manager.memory_manager:
                self.print_msg("\n--- RECENT MEMORIES ---", "bold cyan")
                for m_type, m_list in self.session_manager.memory_manager.memories.items():
                    if m_list:
                        self.print_msg(f"\n[{m_type.value.upper()}]", "bold yellow")
                        for mem in m_list[-5:]:
                            self.print_msg(f" - {mem.content} (Importance: {mem.importance})")

        elif cmd == "/search":
            if not args:
                self.print_msg("Usage: /search <query_string>", "bold yellow")
            elif self.session_manager.active_session:
                res = self.persistence.search_messages_and_memories(args, self.session_manager.active_session.session_id)
                self.print_msg(f"\n--- SEARCH RESULTS FOR '{args}' ---", "bold cyan")
                self.print_msg(f"Matching Messages ({len(res['messages'])}):")
                for m in res["messages"]:
                    self.print_msg(f" [{m['role']}] {m['content'][:100]}...")
                self.print_msg(f"Matching Memories ({len(res['memories'])}):")
                for mem in res["memories"]:
                    self.print_msg(f" - {mem['content']}")

        elif cmd == "/history":
            if self.session_manager.active_session:
                history = self.persistence.get_chat_history(self.session_manager.active_session.session_id, limit=15)
                self.print_msg("\n--- CHAT HISTORY (Last 15) ---", "bold cyan")
                for msg in history:
                    role_label = msg.get("character_id") or msg["role"]
                    self.print_msg(f"{role_label}: {msg['content'][:120]}...")

        elif cmd == "/reset":
            if self.session_manager.active_session:
                self.persistence.delete_session(self.session_manager.active_session.session_id)
                self.print_msg("Active session chat history reset.", "bold yellow")

        else:
            self.print_msg(f"Unknown command '{cmd}'. Type '/help' for available commands.", "bold red")

        return True

    def display_help(self):
        """Display help command table."""
        help_text = """
Terminal Command Reference:
  /help               - Display this help reference
  /list               - List all available characters & active party
  /switch <name>      - Switch active primary character persona
  /rename [target] [new] - Rename character persona name
  /username [name]    - View or change your player/user display name
  /add <name>         - Add character to active party roster
  /remove <name>      - Remove character from active party roster
  /progression        - Inspect story arc phase, milestones, trust & situational adaptations
  /adapt              - View current situational adaptation & story-evolved behaviors
  /analyze            - View intent analysis breakdown of latest message
  /save               - Save current session state and memories
  /load <session_id>  - Load a saved roleplay session
  /export [filename]  - Export session state to JSON file
  /import <filename>  - Import session from JSON file
  /story              - Display active story title, setting, and scenario
  /summary            - View current story summary
  /memory             - Inspect active hierarchical memories
  /search <query>     - Search messages and long-term memories
  /history            - Display recent conversation log history
  /reset              - Reset current session chat history
  /exit               - Save state and exit application
"""
        self.print_msg(help_text, "cyan")

    def display_character_list(self):
        """Display character roster and active character status."""
        self.print_msg("\n--- CHARACTER ROSTER ---", "bold cyan")
        active = self.char_manager.get_active_character()
        party_ids = set(self.char_manager.active_party_ids)

        for cid, char in self.char_manager.characters.items():
            status = []
            if active and cid == active.character_id:
                status.append("ACTIVE")
            if cid in party_ids:
                status.append("IN PARTY")
            status_str = f" [{', '.join(status)}]" if status else ""
            self.print_msg(f" • {char.character_name} ({char.character_id}){status_str} - {char.occupation}")

if __name__ == "__main__":
    cli = RoleplayCLI()
    cli.run()
