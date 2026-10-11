"""
speech_refiner.py — Phase 11: Human Speech Refinement

Offline post-processing pipeline that cleans raw Vosk STT transcriptions
before they are sent to the LLM. Each step is independently testable.
"""

import re
from typing import List

# ── Filler words to strip ────────────────────────────────────────────────────
_FILLERS = {
    "um", "uh", "uhh", "umm", "er", "err", "hmm", "hm",
    "like", "you know", "you know what i mean", "i mean",
    "sort of", "kind of", "kinda", "sorta",
    "basically", "literally", "actually", "honestly",
    "right", "okay so", "so yeah", "yeah so",
}

# ── Common STT normalisation substitutions ───────────────────────────────────
_STT_SUBSTITUTIONS: List[tuple] = [
    # Contractions / informal speech
    (r"\bgonna\b",       "going to"),
    (r"\bwanna\b",       "want to"),
    (r"\bgotta\b",       "got to"),
    (r"\bcoulda\b",      "could have"),
    (r"\bwoulda\b",      "would have"),
    (r"\bshoulda\b",     "should have"),
    (r"\bdunno\b",       "don't know"),
    (r"\bkinda\b",       "kind of"),
    (r"\bsorta\b",       "sort of"),
    (r"\bcuz\b",         "because"),
    (r"\bcause\b",       "because"),
    (r"\bcoz\b",         "because"),
    (r"\byeah\b",        "yes"),
    (r"\bnope\b",        "no"),
    (r"\bgive me\b",     "give me"),
    (r"\bcome on\b",     "come on"),
    # Number words (common ones)
    (r"\blemme\b",       "let me"),
    (r"\binit\b",        "isn't it"),
]


def remove_fillers(text: str) -> str:
    """Strips standalone filler words/phrases from text."""
    # Sort fillers longest-first so multi-word fillers match before single words
    sorted_fillers = sorted(_FILLERS, key=len, reverse=True)
    for filler in sorted_fillers:
        # Match as whole phrase surrounded by word boundaries or whitespace
        pattern = r"(?<!\w)" + re.escape(filler) + r"(?!\w)"
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    # Collapse multiple spaces left by removals
    text = re.sub(r"  +", " ", text).strip()
    return text


def apply_substitutions(text: str) -> str:
    """Applies common STT normalisation substitutions."""
    for pattern, replacement in _STT_SUBSTITUTIONS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def remove_repeated_words(text: str) -> str:
    """Removes consecutive duplicate words (e.g. 'i i feel' → 'i feel')."""
    return re.sub(r"\b(\w+)( \1\b)+", r"\1", text, flags=re.IGNORECASE)


def capitalise_sentence(text: str) -> str:
    """Capitalises the first character of the text."""
    if not text:
        return text
    return text[0].upper() + text[1:]


def add_terminal_punctuation(text: str) -> str:
    """Adds a period if the text has no sentence-ending punctuation."""
    if text and text[-1] not in ".?!":
        text += "."
    return text


def normalise_whitespace(text: str) -> str:
    """Collapses any leftover multi-spaces and strips leading/trailing space."""
    return re.sub(r"  +", " ", text).strip()


class SpeechRefiner:
    """Applies the full offline refinement pipeline to raw STT transcriptions."""

    def refine(self, raw_text: str) -> str:
        """Runs all refinement steps in order and returns the cleaned text."""
        if not raw_text or not raw_text.strip():
            return raw_text

        text = raw_text.strip().lower()  # Vosk is always lowercase

        text = remove_fillers(text)
        text = apply_substitutions(text)
        text = remove_repeated_words(text)
        text = normalise_whitespace(text)
        text = capitalise_sentence(text)
        text = add_terminal_punctuation(text)

        return text
