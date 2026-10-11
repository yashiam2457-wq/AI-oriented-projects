import re
from typing import List, Dict
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

class MoodTracker:
    """Tracks session mood history and recommends offline mindfulness remedies."""
    
    def __init__(self):
        self.history: List[str] = []
        
        # Mapping keyword regular expressions to emotions
        self.keywords = {
            "Anxiety": re.compile(
                r"\b(anxious|anxiety|stressed|stress|panic|panicking|worry|worried|nervous|uneasy|scared|fear|fearful|frightened|overwhelmed|tense)\b", 
                re.IGNORECASE
            ),
            "Sadness": re.compile(
                r"\b(sad|sadness|depressed|depression|lonely|grief|grieving|hurt|crying|hopeless|empty|miserable|unhappy|heartbroken|pain)\b", 
                re.IGNORECASE
            ),
            "Anger": re.compile(
                r"\b(angry|anger|mad|furious|annoyed|irritated|frustrated|pissed|rage|hating|hate|offended)\b", 
                re.IGNORECASE
            ),
            "Joy": re.compile(
                r"\b(happy|happiness|glad|excited|peaceful|joy|joyful|blessed|wonderful|great|good|smiling|excellent|happy|calm)\b", 
                re.IGNORECASE
            )
        }
        
    def analyze_text(self, text: str) -> str:
        """Classifies the emotion of the user text based on keywords and appends to history."""
        detected = []
        
        for emotion, pattern in self.keywords.items():
            if pattern.search(text):
                detected.append(emotion)
                
        # Resolve to a single emotion
        if not detected:
            resolved = "Neutral"
        elif "Anxiety" in detected:
            resolved = "Anxiety"
        elif "Sadness" in detected:
            resolved = "Sadness"
        elif "Anger" in detected:
            resolved = "Anger"
        else:
            resolved = "Joy"
            
        self.history.append(resolved)
        return resolved

    def get_remedy(self, mood: str) -> Panel:
        """Returns a beautifully formatted Rich panel with a specific mindfulness exercise."""
        text = Text()
        
        if mood == "Anxiety":
            text.append("Box Breathing Exercise (4-4-4-4 Technique)\n\n", style="bold yellow")
            text.append("Use this to calm your nervous system immediately:\n", style="white")
            text.append("  1. Breathe in through your nose for 4 seconds.\n", style="cyan")
            text.append("  2. Hold your breath for 4 seconds.\n", style="cyan")
            text.append("  3. Exhale slowly through your mouth for 4 seconds.\n", style="cyan")
            text.append("  4. Pause and hold for another 4 seconds.\n", style="cyan")
            text.append("  5. Repeat this cycle 3-4 times. Focus completely on the counting.", style="white")
            title = "[bold yellow]Mindfulness Remedy: Box Breathing[/bold yellow]"
            border_style = "yellow"
            
        elif mood == "Sadness":
            text.append("Self-Compassion Grounding Break\n\n", style="bold magenta")
            text.append("A gentle grounding reminder for when you are feeling low:\n", style="white")
            text.append("  • Place a hand gently over your heart or on your arm.\n", style="cyan")
            text.append("  • Take two slow, deep breaths.\n", style="cyan")
            text.append("  • Repeat to yourself softly:\n", style="white")
            text.append("    \"It is okay to feel sad. I am experiencing a difficult moment.\n", style="italic cyan")
            text.append("     May I be patient with myself. May I give myself kindness.\"", style="italic cyan")
            title = "[bold magenta]Mindfulness Remedy: Self-Compassion[/bold magenta]"
            border_style = "magenta"
            
        elif mood == "Anger":
            text.append("5-4-3-2-1 Grounding Technique\n\n", style="bold red")
            text.append("Use this to release frustration and anchor yourself in the present:\n", style="white")
            text.append("  5. Identify FIVE things you can see in your room.\n", style="cyan")
            text.append("  4. Touch FOUR physical objects near you (e.g. your desk, clothes).\n", style="cyan")
            text.append("  3. Listen closely to THREE distinct sounds.\n", style="cyan")
            text.append("  2. Identify TWO things you can smell.\n", style="cyan")
            text.append("  1. Notice ONE thing you can taste (or taste of your mouth).\n", style="cyan")
            text.append("  Take a long, deep breath and let it go.", style="white")
            title = "[bold red]Mindfulness Remedy: 5-4-3-2-1 Grounding[/bold red]"
            border_style = "red"
            
        elif mood == "Joy":
            text.append("Gratitude Journal Prompt\n\n", style="bold green")
            text.append("Celebrate this positive energy and ground it in your memory:\n", style="white")
            text.append("  • Close your eyes and recall three simple things you feel grateful for today\n", style="cyan")
            text.append("    (e.g., a warm cup of water/tea, a kind word, a comfortable seat).\n", style="white")
            text.append("  • Sense the warmth in your body as you hold these thoughts for 10 seconds.", style="cyan")
            title = "[bold green]Mindfulness Practice: Gratitude[/bold green]"
            border_style = "green"
            
        else: # Neutral
            text.append("Mindful Minute Practice\n\n", style="bold blue")
            text.append("Maintain your calm state and reset your focus:\n", style="white")
            text.append("  • Take three deep breaths, counting each inhale and exhale.\n", style="cyan")
            text.append("  • Focus entirely on the physical sensation of air entering and leaving your nostrils.\n", style="cyan")
            text.append("  • Rest in this quiet space for a few seconds before returning to your work.", style="white")
            title = "[bold blue]Mindfulness Practice: Mindful Minute[/bold blue]"
            border_style = "blue"
            
        return Panel(text, title=title, border_style=border_style, expand=False)

    def generate_summary_panel(self) -> Panel:
        """Generates a summary Panel showing session mood statistics and timeline graph."""
        if not self.history:
            return Panel(Text("No conversation data available yet to analyze mood.", style="italic white"), 
                         title="[bold yellow]Session Mood Analytics[/bold yellow]", border_style="yellow")
                         
        total_turns = len(self.history)
        counts = {}
        for mood in self.history:
            counts[mood] = counts.get(mood, 0) + 1
            
        # Draw Statistics Table
        table = Table(title="Mood Distribution", show_header=True, header_style="bold magenta", box=None)
        table.add_column("Mood", style="bold cyan")
        table.add_column("Percentage", justify="right", style="green")
        
        for mood in ["Joy", "Anxiety", "Sadness", "Anger", "Neutral"]:
            count = counts.get(mood, 0)
            if count > 0:
                pct = int(100 * count / total_turns)
                table.add_row(mood, f"{pct}%")
                
        # Draw Timeline Arrow graph
        timeline_text = Text()
        timeline_text.append("\nSession Emotion Timeline:\n  ", style="bold yellow")
        
        colors = {
            "Joy": "green",
            "Anxiety": "yellow",
            "Sadness": "magenta",
            "Anger": "red",
            "Neutral": "blue"
        }
        
        for idx, mood in enumerate(self.history):
            color = colors.get(mood, "white")
            timeline_text.append(mood, style=f"bold {color}")
            if idx < len(self.history) - 1:
                timeline_text.append(" ──➔ ", style="white")
                
        # Recommended remedy based on latest turn
        latest_mood = self.history[-1]
        
        # Combine elements
        summary_console = Text()
        summary_console.append("VANI Emotion Tracking Summary\n\n", style="bold magenta")
        summary_console.append(timeline_text)
        summary_console.append(f"\n\nLatest Detected Emotion: ", style="bold white")
        summary_console.append(latest_mood, style=f"bold {colors.get(latest_mood, 'white')}")
        
        remedy_panel = self.get_remedy(latest_mood)
        
        # Let's put everything inside a single layout
        from rich.console import Group
        group = Group(
            summary_console,
            Table.grid(padding=1),
            table,
            Table.grid(padding=1),
            remedy_panel
        )
        
        return Panel(group, title="[bold yellow]Session Mood Analytics[/bold yellow]", border_style="yellow", expand=False)
