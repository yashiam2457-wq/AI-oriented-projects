"""
adaptive_engine.py — Phase 13: Adaptive rate computation (extracted for testability).

Exposes `compute_adaptive_params()` so it can be unit-tested without
instantiating the full ChatInterface or TTS engine.
"""
from typing import Optional, Tuple
from modules.tts.voice_mode import VoiceModeManager

_vmm = VoiceModeManager()


def compute_adaptive_params(
    user_input: str,
    active_voice_mode: str,
    base_tts_rate: int,
    latest_mood: str = "Neutral",
    adaptive_enabled: bool = True,
) -> Tuple[Optional[int], Optional[float]]:
    """
    Returns (rate_override, pause_multiplier_override) based on:
      - Active voice mode baseline
      - Message word count (engagement proxy)
      - Latest detected mood
    Returns (None, None) when adaptive is disabled.
    """
    if not adaptive_enabled:
        return None, None

    mode = _vmm.get_mode(active_voice_mode)
    base_rate  = mode["base_rate"]  if mode else base_tts_rate
    base_pause = mode["pause_multiplier"] if mode else 1.0

    words      = user_input.split()
    word_count = len(words)

    rate_modifier  = 0
    pause_modifier = 0.0

    # ── Word-count engagement ────────────────────────────────────────────────
    if word_count > 20:        # User is sharing a lot; slow down to sound attentive
        rate_modifier  = -20
        pause_modifier =  0.2
    elif word_count < 5:       # Quick remark; pick up the pace
        rate_modifier  =  15
        pause_modifier = -0.1

    # ── Emotional state engagement ───────────────────────────────────────────
    if latest_mood in ("Anxiety", "Sadness", "Anger"):
        rate_modifier  -= 15
        pause_modifier +=  0.3
    elif latest_mood == "Joy":
        rate_modifier  +=  10
        pause_modifier -=  0.05

    final_rate  = max(100, min(250, base_rate  + rate_modifier))
    final_pause = max(0.5, min(2.0, base_pause + pause_modifier))

    return final_rate, final_pause
