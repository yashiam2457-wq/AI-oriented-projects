import pytest
from rich.panel import Panel
from modules.emotion.mood_tracker import MoodTracker

def test_mood_tracker_classification():
    tracker = MoodTracker()
    
    # Test Anxiety keyword
    assert tracker.analyze_text("I feel so stressed and worried right now.") == "Anxiety"
    # Test Sadness keyword
    assert tracker.analyze_text("I feel very sad and lonely.") == "Sadness"
    # Test Anger keyword
    assert tracker.analyze_text("This is annoying, I am so angry!") == "Anger"
    # Test Joy keyword
    assert tracker.analyze_text("I am having a wonderful and happy day!") == "Joy"
    # Test Neutral keyword
    assert tracker.analyze_text("The weather is normal.") == "Neutral"
    
    assert tracker.history == ["Anxiety", "Sadness", "Anger", "Joy", "Neutral"]


def test_mood_tracker_remedy():
    tracker = MoodTracker()
    
    panel_anxiety = tracker.get_remedy("Anxiety")
    assert isinstance(panel_anxiety, Panel)
    assert "Box Breathing" in str(panel_anxiety.title)
    
    panel_anger = tracker.get_remedy("Anger")
    assert isinstance(panel_anger, Panel)
    assert "5-4-3-2-1 Grounding" in str(panel_anger.title)


def test_mood_tracker_summary_panel():
    tracker = MoodTracker()
    
    # No history case
    empty_panel = tracker.generate_summary_panel()
    assert isinstance(empty_panel, Panel)
    
    # Populated history case
    tracker.analyze_text("worried")
    tracker.analyze_text("happy")
    summary_panel = tracker.generate_summary_panel()
    assert isinstance(summary_panel, Panel)
    assert "Session Mood Analytics" in str(summary_panel.title)
