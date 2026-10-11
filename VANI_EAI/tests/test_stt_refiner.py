import pytest
from modules.stt.speech_refiner import (
    SpeechRefiner,
    remove_fillers,
    apply_substitutions,
    remove_repeated_words,
    capitalise_sentence,
    add_terminal_punctuation
)

def test_remove_fillers():
    assert remove_fillers("um i feel fine uh") == "i feel fine"
    assert remove_fillers("you know i literally don't know") == "i don't know"
    assert remove_fillers("basically i kind of want to sleep") == "i want to sleep"

def test_apply_substitutions():
    assert apply_substitutions("i gonna see cuz they wanna leave") == "i going to see because they want to leave"
    assert apply_substitutions("nope that is kinda cool") == "no that is kind of cool"

def test_remove_repeated_words():
    assert remove_repeated_words("i i feel very very sad sad") == "i feel very sad"
    assert remove_repeated_words("no change here") == "no change here"

def test_capitalise_sentence():
    assert capitalise_sentence("hello") == "Hello"
    assert capitalise_sentence("") == ""

def test_add_terminal_punctuation():
    assert add_terminal_punctuation("hello") == "hello."
    assert add_terminal_punctuation("hello!") == "hello!"
    assert add_terminal_punctuation("hello?") == "hello?"

def test_full_stt_refinement():
    refiner = SpeechRefiner()
    raw = "um uh i i gonna go like you know home cuz i kinda feel tired er"
    refined = refiner.refine(raw)
    assert refined == "I going to go home because i feel tired."
