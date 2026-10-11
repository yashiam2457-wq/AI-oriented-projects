"""test_adaptive_rate.py — Phase 13: Adaptive rate engine verification tests."""
import pytest
from modules.tts.adaptive_engine import compute_adaptive_params


# ── Disabled ─────────────────────────────────────────────────────────────────

def test_adaptive_disabled_returns_none():
    rate, pause = compute_adaptive_params(
        "hello", "Friendly", 175, "Neutral", adaptive_enabled=False
    )
    assert rate is None
    assert pause is None


# ── Word-count rules ──────────────────────────────────────────────────────────

def test_long_message_slows_rate():
    """Messages with more than 20 words should produce a rate below the base."""
    long_msg = " ".join(["word"] * 25)  # 25 words
    rate, _ = compute_adaptive_params(long_msg, "Friendly", 175, "Neutral")
    base = 175  # Friendly base rate
    assert rate < base  # should slow down


def test_short_message_speeds_rate():
    """Messages with fewer than 5 words should produce a rate above the base."""
    short_msg = "hi"  # 1 word
    rate, _ = compute_adaptive_params(short_msg, "Friendly", 175, "Neutral")
    base = 175
    assert rate > base  # should speed up


def test_medium_message_neutral_rate():
    """Messages with 5–20 words should not modify the word-count factor."""
    mid_msg = " ".join(["word"] * 10)  # 10 words, neutral
    rate, _ = compute_adaptive_params(mid_msg, "Friendly", 175, "Neutral")
    assert rate == 175  # no word-count modifier, no mood modifier → exact base


# ── Mood rules ────────────────────────────────────────────────────────────────

def test_anxiety_slows_rate_and_extends_pause():
    mid_msg = " ".join(["word"] * 10)
    rate, pause = compute_adaptive_params(mid_msg, "Friendly", 175, "Anxiety")
    assert rate < 175
    assert pause > 1.0  # Friendly base pause is 1.0


def test_sadness_slows_rate():
    mid_msg = " ".join(["word"] * 10)
    rate, _ = compute_adaptive_params(mid_msg, "Friendly", 175, "Sadness")
    assert rate < 175


def test_anger_slows_rate():
    mid_msg = " ".join(["word"] * 10)
    rate, _ = compute_adaptive_params(mid_msg, "Friendly", 175, "Anger")
    assert rate < 175


def test_joy_speeds_rate():
    mid_msg = " ".join(["word"] * 10)
    rate, _ = compute_adaptive_params(mid_msg, "Friendly", 175, "Joy")
    assert rate > 175


# ── Clamping ──────────────────────────────────────────────────────────────────

def test_rate_clamped_to_100_minimum():
    """Even with maximum slowing factors, rate must not drop below 100."""
    long_msg = " ".join(["word"] * 25)
    rate, _ = compute_adaptive_params(long_msg, "Emotional Support", 135, "Anxiety")
    assert rate >= 100


def test_rate_clamped_to_250_maximum():
    """Even with maximum speeding factors, rate must not exceed 250."""
    short_msg = "yes"
    rate, _ = compute_adaptive_params(short_msg, "Playful", 195, "Joy")
    assert rate <= 250


def test_pause_clamped_to_minimum_0_5():
    short_msg = "ok"
    _, pause = compute_adaptive_params(short_msg, "Playful", 195, "Joy")
    assert pause >= 0.5


def test_pause_clamped_to_maximum_2_0():
    long_msg = " ".join(["word"] * 25)
    _, pause = compute_adaptive_params(long_msg, "Emotional Support", 135, "Anxiety")
    assert pause <= 2.0


# ── Voice Mode baselines ──────────────────────────────────────────────────────

def test_calm_mode_uses_145_base():
    mid_msg = " ".join(["word"] * 10)
    rate, _ = compute_adaptive_params(mid_msg, "Calm", 175, "Neutral")
    assert rate == 145  # Calm base is 145, neutral mood, medium message → no modifier


def test_emotional_support_mode_base_135():
    mid_msg = " ".join(["word"] * 10)
    rate, _ = compute_adaptive_params(mid_msg, "Emotional Support", 175, "Neutral")
    assert rate == 135
