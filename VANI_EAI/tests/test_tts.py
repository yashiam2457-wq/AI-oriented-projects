import queue
import time
from unittest.mock import MagicMock, patch
import pytest
from modules.config.settings import Settings
from modules.tts.tts_client import TTSClient

def test_tts_settings_integration():
    settings = Settings(
        tts_enabled=True,
        tts_rate=180,
        tts_volume=0.8,
        tts_voice_index=1
    )
    assert settings.tts_enabled is True
    assert settings.tts_rate == 180
    assert settings.tts_volume == 0.8
    assert settings.tts_voice_index == 1


def test_tts_client_initialization_and_speaking():
    settings = Settings(
        tts_enabled=True,
        tts_rate=180,
        tts_volume=0.8,
        tts_voice_index=0
    )
    
    mock_engine = MagicMock()
    mock_voices = [MagicMock(id="voice_0"), MagicMock(id="voice_1")]
    mock_engine.getProperty.return_value = mock_voices
    
    with patch("pyttsx3.init", return_value=mock_engine) as mock_init:
        client = TTSClient(settings)
        
        # Test start launches thread and initializes engine
        client.start()
        
        # Wait briefly for thread to initialize and loop once
        timeout = 2.0
        start_time = time.time()
        while not client.running and time.time() - start_time < timeout:
            time.sleep(0.05)
            
        assert client.running is True
        mock_init.assert_called_once()
        mock_engine.setProperty.assert_any_call("rate", 180)
        mock_engine.setProperty.assert_any_call("volume", 0.8)
        mock_engine.setProperty.assert_any_call("voice", "voice_0")
        
        # Test speaking queues text and calls say/runAndWait
        client.speak("Test sentence")
        
        # Wait for queue to be processed
        start_time = time.time()
        while not client.queue.empty() and time.time() - start_time < timeout:
            time.sleep(0.05)
            
        # Give the thread loop a small amount of time to execute say/runAndWait
        time.sleep(0.1)
        
        mock_engine.say.assert_called_with("Test sentence")
        mock_engine.runAndWait.assert_called()
        
        # Test stop speaking drains queue and calls engine stop
        client.speak("Another sentence")
        client.stop_speaking()
        assert client.queue.empty() is True
        mock_engine.stop.assert_called()
        
        # Clean up
        client.close()
        assert client.running is False
