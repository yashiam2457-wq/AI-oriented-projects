import re
from typing import List, Tuple

class TTSSpeechRefiner:
    """Refines assistant response text to sound more human-like, natural, and well-paced when spoken via pyttsx3."""

    def __init__(self):
        self.expansions = [
            (r"\be\.g\.(?!\w)", "for example"),
            (r"\bi\.e\.(?!\w)", "that is"),
            (r"\betc\.(?!\w)", "et cetera"),
            (r"\bAI\b", "A I"),
            (r"\bLLM\b", "L L M"),
            (r"\bLLMs\b", "L L Ms"),
            (r"\bSTT\b", "S T T"),
            (r"\bTTS\b", "T T S"),
            (r"\bVANI\b", "Vah-nee"),
            (r"\bCLI\b", "C L I"),
            (r"\bJSON\b", "Jay-son"),
            (r"\bUI\b", "U I"),
            (r"\bUX\b", "U X"),
        ]

    def clean_markdown(self, text: str) -> str:
        """Strips markdown styling symbols that cause speech synthesis engines to read awkwardly."""
        # 1. Remove markdown links: [text](url) -> text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        
        # 2. Remove code blocks syntax
        text = text.replace("```", "")
        
        # 3. Strip bold/italic symbols
        text = text.replace("**", "").replace("__", "").replace("*", "").replace("_", "")
        
        # 4. Remove inline code backticks
        text = text.replace("`", "")
        
        # 5. Remove headers: #, ##, etc.
        text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
        
        # 6. Remove bullet point markers at line start
        text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
        
        return text

    def expand_abbreviations(self, text: str) -> str:
        """Replaces shorthand abbreviations with their natural phonetic equivalents."""
        for pattern, replacement in self.expansions:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def split_into_clauses(self, text: str) -> List[Tuple[str, float]]:
        """Splits the text into conversational clauses at punctuation marks and returns pause timings."""
        # Split on sentence end (. ! ? ; \n) and clause separators (, :)
        # Retain split separators in list to assign pause time
        tokens = re.split(r"([.!?;\n]+|[,:]+)", text)
        
        clauses = []
        current_clause = ""
        
        for token in tokens:
            if not token:
                continue
                
            # Check if token is sentence terminator (longer pause)
            if re.match(r"^[.!?;\n]+$", token):
                if current_clause.strip():
                    clauses.append((current_clause.strip(), 0.35))
                current_clause = ""
            # Check if token is clause separator (shorter pause)
            elif re.match(r"^[,:]+$", token):
                if current_clause.strip():
                    clauses.append((current_clause.strip(), 0.15))
                current_clause = ""
            else:
                current_clause += token
                
        # Handle trailing text without punctuation
        if current_clause.strip():
            clauses.append((current_clause.strip(), 0.0))
            
        return clauses

    def refine(self, text: str) -> List[Tuple[str, float]]:
        """Runs the entire TTS speech refinement pipeline."""
        if not text or not text.strip():
            return []
            
        cleaned = self.clean_markdown(text)
        expanded = self.expand_abbreviations(cleaned)
        clauses = self.split_into_clauses(expanded)
        
        # Return only non-empty clauses
        return [(c, p) for c, p in clauses if c.strip()]
