import pytest
from modules.tts.tts_refiner import TTSSpeechRefiner

def test_clean_markdown():
    refiner = TTSSpeechRefiner()
    
    markdown_text = "### Welcome!\n- This is a **bold** and *italic* code: `print(123)`\nCheck [link](http://example.com) out."
    cleaned = refiner.clean_markdown(markdown_text)
    
    assert "#" not in cleaned
    assert "*" not in cleaned
    assert "`" not in cleaned
    assert "-" not in cleaned
    assert "bold" in cleaned
    assert "link" in cleaned
    assert "http" not in cleaned

def test_expand_abbreviations():
    refiner = TTSSpeechRefiner()
    
    raw = "VANI uses an LLM, e.g. Mistral, for AI companion tasks."
    expanded = refiner.expand_abbreviations(raw)
    
    assert "Vah-nee" in expanded
    assert "L L M" in expanded
    assert "for example" in expanded
    assert "A I" in expanded

def test_split_into_clauses_with_pauses():
    refiner = TTSSpeechRefiner()
    
    text = "Hello, how are you? I am doing great."
    clauses = refiner.split_into_clauses(text)
    
    # Expected clauses: 
    # ("Hello", 0.15)
    # ("how are you", 0.35)
    # ("I am doing great", 0.35)
    assert len(clauses) == 3
    assert clauses[0][0] == "Hello"
    assert clauses[0][1] == 0.15
    assert clauses[1][0] == "how are you"
    assert clauses[1][1] == 0.35
    assert clauses[2][0] == "I am doing great"
    assert clauses[2][1] == 0.35

def test_full_tts_refinement_pipeline():
    refiner = TTSSpeechRefiner()
    
    text = "**Hello**! VANI is here. Open a browser, e.g. Chrome, for testing."
    refined = refiner.refine(text)
    
    assert len(refined) == 5
    assert refined[0] == ("Hello", 0.35)
    assert refined[1] == ("Vah-nee is here", 0.35)
    assert refined[2] == ("Open a browser", 0.15)
    assert refined[3] == ("for example Chrome", 0.15)
    assert refined[4] == ("for testing", 0.35)
