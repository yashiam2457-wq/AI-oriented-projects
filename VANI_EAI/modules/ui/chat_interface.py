import os
import sys
from typing import List, Dict, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich.live import Live
from rich.prompt import Prompt
from modules.config.settings import Settings
from modules.llm.llm_client import LLMClient
from modules.tts.tts_client import TTSClient
from modules.stt.stt_client import STTClient
from modules.memory.memory_manager import MemoryManager
from modules.persona.persona_manager import PersonaManager
from modules.journal.journal_manager import JournalManager
from modules.analytics.analytics import AnalyticsDashboard
from modules.profile.profile_manager import ProfileManager


class ChatInterface:
    def __init__(self, client: LLMClient, settings: Settings):
        self.client = client
        self.settings = settings
        self.console = Console()
        self.history: List[Dict[str, str]] = []

        # Persona: load and apply the single persona
        self.persona_manager = PersonaManager()
        self.persona_manager.apply(self.settings)

        # Profile: load user profile
        self.profile_manager = ProfileManager(self.settings)

        # Build initial system prompt
        self._refresh_system_prompt()

        # Memory: load prior context
        self.memory_manager = MemoryManager(self.settings)
        self._init_history()

        # TTS / STT
        self.tts_client = TTSClient(self.settings)
        self.tts_client.start()
        self.stt_client = STTClient(self.settings)

        # Journal
        self.journal_manager = JournalManager(self.settings)

        # Analytics
        self.analytics = AnalyticsDashboard(self.settings)

    # ------------------------------------------------------------------
    # History helpers
    # ------------------------------------------------------------------

    def _init_history(self):
        """Initialises conversation history with the system prompt and prior context."""
        self.history = [{"role": "system", "content": self.settings.system_prompt}]
        prior = self.memory_manager.load_recent_context()
        if prior:
            self.history.extend(prior)
            self.console.print(
                f"[dim cyan]Resumed from last session ({len(prior)} prior turns loaded).[/dim cyan]"
            )

    def clear_history(self):
        """Clears user/assistant history and reinitialises with the system prompt."""
        self._init_history()
        self.console.print("[yellow]Conversation history cleared.[/yellow]")

    def _refresh_system_prompt(self):
        """Rebuilds the system prompt from persona + profile context."""
        persona = self.persona_manager.get()
        self.settings.system_prompt = persona.get(
            "system_prompt",
            "You are VANI, a close friend. Talk naturally.",
        )
        profile_ctx = self.profile_manager.build_context_block()
        if profile_ctx:
            self.settings.system_prompt += profile_ctx

        if self.history and self.history[0]["role"] == "system":
            self.history[0]["content"] = self.settings.system_prompt

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def display_welcome(self):
        """Displays the welcome panel."""
        os.system("cls" if os.name == "nt" else "clear")
        welcome_text = Text()
        welcome_text.append("VANI\n", style="bold magenta")
        welcome_text.append(
            f"Model: {self.settings.model_name}  |  Mode: {self.settings.llm_mode.upper()}\n\n",
            style="italic cyan",
        )
        welcome_text.append("Commands:\n", style="bold yellow")
        for cmd, desc in [
            ("/clear",           "Clear conversation history"),
            ("/info",            "Show system settings"),
            ("/tts",             "Toggle Text-to-Speech"),
            ("/voice",           "Toggle hands-free voice input"),
            ("/history",         "List saved sessions"),
            ("/load N",          "Load session N into context"),
            ("/journal",         "List journal entries"),
            ("/journal N",       "Read journal entry N"),
            ("/stats",           "Conversation analytics"),
            ("/profile",         "Show your profile and notes"),
            ("/profile name X",  "Set your preferred name"),
            ("/note <text>",     "Add something for VANI to remember"),
            ("/notes",           "List all remembered notes"),
            ("/forget ID",       "Remove a note by its ID"),
            ("/exit",            "Quit"),
        ]:
            welcome_text.append(f"  {cmd:<22} - {desc}\n", style="green")

        self.console.print(
            Panel(
                welcome_text,
                title="[bold green]VANI Ready[/bold green]",
                border_style="magenta",
                expand=False,
            )
        )

    def display_info(self):
        """Displays current system configuration."""
        info_text = Text()
        info_text.append(f"Persona        : {self.settings.active_persona}\n", style="bold cyan")
        info_text.append(f"LLM Mode       : {self.settings.llm_mode}\n", style="cyan")
        if self.settings.llm_mode == "local":
            info_text.append(f"Model Path     : {self.settings.local_model_path}\n", style="cyan")
        else:
            info_text.append(f"Base URL       : {self.settings.server_base_url}\n", style="cyan")
        info_text.append(f"Temperature    : {self.settings.temperature}\n", style="cyan")
        info_text.append(f"Max Tokens     : {self.settings.max_tokens}\n", style="cyan")
        info_text.append(
            f"TTS            : {'ON' if self.settings.tts_enabled else 'OFF'}"
            f" | Voice: {self.settings.kokoro_voice}"
            f" | Speed: {self.settings.kokoro_speed}x\n",
            style="cyan",
        )
        info_text.append(
            f"Voice Input    : {'ENABLED' if self.settings.voice_input_enabled else 'DISABLED'}"
            f" | Whisper model: {self.settings.whisper_model}\n",
            style="cyan",
        )
        info_text.append(
            f"Memory         : {'ENABLED' if self.settings.memory_enabled else 'DISABLED'}"
            f" | Max Turns: {self.settings.memory_max_turns}\n",
            style="cyan",
        )
        info_text.append(f"Profile Path   : {self.settings.profile_path}\n", style="cyan")
        info_text.append(f"System Prompt  : {self.settings.system_prompt[:120]}…", style="italic white")
        self.console.print(
            Panel(info_text, title="[bold yellow]System Settings[/bold yellow]", border_style="yellow", expand=False)
        )

    def _display_history_list(self):
        """Shows all saved sessions in a rich table."""
        sessions = self.memory_manager.list_sessions()
        if not sessions:
            self.console.print("[yellow]No saved sessions found.[/yellow]")
            return
        table = Table(title="Saved Sessions", show_header=True, header_style="bold cyan")
        table.add_column("#", justify="right", style="bold white", no_wrap=True)
        table.add_column("Timestamp", style="cyan")
        table.add_column("Persona", style="magenta")
        table.add_column("Turns", justify="right", style="green")
        for i, s in enumerate(sessions, 1):
            table.add_row(str(i), s["timestamp"], s["persona"], str(s["turns"]))
        self.console.print(table)
        self.console.print("[dim]Use /load <N> to restore a session.[/dim]")

    def _display_journal_list(self):
        """Shows all journal entries in a rich table."""
        entries = self.journal_manager.list_entries()
        if not entries:
            self.console.print("[yellow]No journal entries yet.[/yellow]")
            return
        table = Table(title="Journal Entries", show_header=True, header_style="bold magenta")
        table.add_column("#", justify="right", style="bold white", no_wrap=True)
        table.add_column("Date", style="cyan")
        table.add_column("Persona", style="magenta")
        table.add_column("Turns", justify="right", style="green")
        for i, e in enumerate(entries, 1):
            table.add_row(str(i), e["date"], e["persona"], e.get("turns", "?"))
        self.console.print(table)
        self.console.print("[dim]Use /journal <N> to read a specific entry.[/dim]")

    def _display_journal_entry(self, index: int):
        """Renders a specific journal entry as a formatted panel."""
        text = self.journal_manager.read_entry(index)
        if text is None:
            self.console.print(f"[red]Journal entry {index} not found.[/red]")
            return
        self.console.print(
            Panel(
                Markdown(text),
                title=f"[bold magenta]Journal Entry #{index}[/bold magenta]",
                border_style="magenta",
                expand=False,
            )
        )

    def _display_profile(self):
        """Renders a profile summary with preferred name and notes."""
        text = Text()
        name = self.profile_manager.name or "<Not set>"
        text.append("Name : ", style="bold cyan")
        text.append(f"{name}\n\n", style="white")
        text.append("Remembered Notes:\n", style="bold yellow")
        notes = self.profile_manager.list_notes()
        if notes:
            for n in notes:
                text.append(f"  [{n['id']}] ", style="bold green")
                text.append(f"{n['text']} ", style="white")
                text.append(f"({n['created']})\n", style="dim white")
        else:
            text.append(
                "  No notes saved yet. Use /note <text> to have VANI remember things.",
                style="italic dim white",
            )
        self.console.print(
            Panel(
                text,
                title="[bold magenta]Profile & Notes[/bold magenta]",
                border_style="magenta",
                expand=False,
            )
        )

    def _display_notes(self):
        """Displays notes in a structured table."""
        notes = self.profile_manager.list_notes()
        if not notes:
            self.console.print("[yellow]No notes found. Use /note <text> to add one.[/yellow]")
            return
        table = Table(title="VANI Remembered Notes", show_header=True, header_style="bold yellow")
        table.add_column("ID", justify="right", style="bold green", no_wrap=True)
        table.add_column("Note", style="white")
        table.add_column("Added On", style="cyan")
        for n in notes:
            table.add_row(str(n["id"]), n["text"], n["created"])
        self.console.print(table)

    # ------------------------------------------------------------------
    # Streaming TTS helper
    # ------------------------------------------------------------------

    def _speak_stream_increments(self, response_text: str, is_finished: bool = False):
        """Queues complete sentences for TTS as they arrive in the stream."""
        if not self.settings.tts_enabled:
            return
        text = response_text[self.last_spoken_idx:]
        if not text:
            return
        if is_finished:
            clean = text.strip()
            if clean:
                self.tts_client.speak(clean)
            self.last_spoken_idx = len(response_text)
            return
        # Split on natural sentence boundaries
        delimiters = [". ", "? ", "! ", "\n"]
        min_pos = len(text)
        found = False
        for delim in delimiters:
            pos = text.find(delim)
            if pos != -1 and pos + len(delim) < min_pos:
                min_pos = pos + len(delim)
                found = True
        if found:
            sentence = text[:min_pos].strip()
            if sentence:
                self.tts_client.speak(sentence)
            self.last_spoken_idx += min_pos
            # Recurse to catch multiple sentences in one chunk
            self._speak_stream_increments(response_text, is_finished=False)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def start_loop(self):
        """Starts the main conversation loop."""
        self.display_welcome()

        try:
            while True:
                try:
                    # ── Input (typed or spoken) ──────────────────────────
                    if self.settings.voice_input_enabled:
                        user_input = Prompt.ask(
                            "\n[bold green]You (Press Enter to speak, or type a command)[/bold green]",
                            default="",
                        ).strip()
                        if not user_input:
                            self.tts_client.stop_speaking()
                            user_input = self.stt_client.listen().strip()
                            if not user_input:
                                continue
                            self.console.print(f"[bold green]You:[/bold green] {user_input}")
                    else:
                        user_input = Prompt.ask("\n[bold green]You[/bold green]").strip()

                    if not user_input:
                        continue

                    # ── Command routing ──────────────────────────────────
                    cmd = user_input.lower().strip()

                    if cmd in ["/exit", "/quit"]:
                        self.console.print("[bold red]Goodbye![/bold red]")
                        break

                    if cmd == "/clear":
                        self.clear_history()
                        continue

                    if cmd == "/info":
                        self.display_info()
                        continue

                    if cmd == "/tts":
                        self.settings.tts_enabled = not self.settings.tts_enabled
                        if self.settings.tts_enabled:
                            self.tts_client.start()
                            self.console.print("[green]TTS enabled.[/green]")
                        else:
                            self.tts_client.stop_speaking()
                            self.console.print("[yellow]TTS disabled.[/yellow]")
                        continue

                    if cmd == "/voice":
                        self.settings.voice_input_enabled = not self.settings.voice_input_enabled
                        state = "enabled" if self.settings.voice_input_enabled else "disabled"
                        self.console.print(f"[green]Voice input {state}.[/green]")
                        continue

                    if cmd == "/history":
                        self._display_history_list()
                        continue

                    if cmd.startswith("/load"):
                        parts = cmd.split()
                        if len(parts) < 2 or not parts[1].isdigit():
                            self.console.print("[yellow]Usage: /load <N>  — see /history for list.[/yellow]")
                            continue
                        idx = int(parts[1])
                        turns = self.memory_manager.load_session_by_index(idx)
                        if not turns:
                            self.console.print(f"[red]Session {idx} not found or empty.[/red]")
                            continue
                        self.history = [{"role": "system", "content": self.settings.system_prompt}]
                        self.history.extend(turns)
                        self.console.print(f"[green]Session {idx} loaded — {len(turns)} turns restored.[/green]")
                        continue

                    if cmd == "/journal":
                        self._display_journal_list()
                        continue

                    if cmd.startswith("/journal "):
                        parts = cmd.split()
                        if len(parts) >= 2 and parts[1].isdigit():
                            self._display_journal_entry(int(parts[1]))
                        else:
                            self.console.print("[yellow]Usage: /journal <N>[/yellow]")
                        continue

                    if cmd == "/stats":
                        self.console.print(self.analytics.render_dashboard())
                        continue

                    if cmd == "/profile":
                        self._display_profile()
                        continue

                    if cmd.startswith("/profile name "):
                        name = user_input[len("/profile name "):].strip()
                        self.profile_manager.set_name(name)
                        self._refresh_system_prompt()
                        self.console.print(f"[green]Name set to: {name}[/green]")
                        continue

                    if cmd.startswith("/note "):
                        note_text = user_input[len("/note "):].strip()
                        note_id = self.profile_manager.add_note(note_text)
                        self._refresh_system_prompt()
                        self.console.print(f"[green]Note #{note_id} saved.[/green]")
                        continue

                    if cmd == "/notes":
                        self._display_notes()
                        continue

                    if cmd.startswith("/forget "):
                        parts = cmd.split()
                        if len(parts) >= 2 and parts[1].isdigit():
                            note_id = int(parts[1])
                            if self.profile_manager.delete_note(note_id):
                                self._refresh_system_prompt()
                                self.console.print(f"[green]Note #{note_id} forgotten.[/green]")
                            else:
                                self.console.print(f"[red]Note #{note_id} not found.[/red]")
                        else:
                            self.console.print("[yellow]Usage: /forget <ID>[/yellow]")
                        continue

                    # ── Normal conversation turn ─────────────────────────
                    self.tts_client.stop_speaking()
                    self.history.append({"role": "user", "content": user_input})

                    # Compress history if needed
                    self.history = self.memory_manager.compress_history(self.history)

                    self.console.print(f"\n[bold magenta]{self.settings.active_persona}[/bold magenta]")
                    assistant_response = ""
                    self.last_spoken_idx = 0

                    with Live(
                        Text("…", style="italic dim white"),
                        console=self.console,
                        refresh_per_second=10,
                    ) as live:
                        try:
                            stream = self.client.generate_stream(self.history)
                            for chunk in stream:
                                assistant_response += chunk
                                live.update(Markdown(assistant_response))
                                self._speak_stream_increments(assistant_response, is_finished=False)
                            self._speak_stream_increments(assistant_response, is_finished=True)
                        except Exception as e:
                            live.update(f"[red]Error generating response: {e}[/red]")
                            self.console.print(
                                "[red]Ensure your model server is running or model path is valid.[/red]"
                            )
                            if self.history[-1]["role"] == "user":
                                self.history.pop()
                            continue

                    if assistant_response:
                        self.history.append({"role": "assistant", "content": assistant_response})

                except (KeyboardInterrupt, EOFError):
                    self.console.print("\n[bold red]Session ended. Goodbye![/bold red]")
                    break

        finally:
            # Save session and auto-generate journal entry
            self.memory_manager.save_session(self.history, persona=self.settings.active_persona)
            saved = self.journal_manager.generate_and_save(
                self.history,
                self.settings.active_persona,
            )
            if saved:
                self.console.print(f"[dim cyan]Journal entry saved → {saved.name}[/dim cyan]")
            self.tts_client.close()
