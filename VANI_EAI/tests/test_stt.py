from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from modules.config.settings import Settings
from modules.stt.stt_client import STTClient

def test_stt_settings_integration():
    settings = Settings(
        voice_input_enabled=True,
        vosk_model_path="test_vosk_model"
    )
    assert settings.voice_input_enabled is True
    assert settings.vosk_model_path == "test_vosk_model"


def test_stt_downloader_triggers_if_missing():
    settings = Settings(vosk_model_path="mocked_models/vosk-model-small-en-us-0.15")
    client = STTClient(settings)
    
    mock_response = MagicMock()
    mock_response.headers = {'content-length': '100'}
    mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
    
    # Mock exists check to force download path
    with patch.object(Path, "exists", return_value=False), \
         patch("requests.get", return_value=mock_response) as mock_get, \
         patch("zipfile.ZipFile") as mock_zip, \
         patch.object(Path, "unlink") as mock_unlink:
             
        client._check_and_download_model()
        
        mock_get.assert_called_with("https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip", stream=True)
        mock_zip.assert_called_once()
        mock_unlink.assert_called_once()
