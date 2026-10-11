import json
from pathlib import Path
from modules.config.settings import load_settings, Settings

def test_default_settings():
    settings = Settings()
    assert settings.llm_mode == "server"
    assert settings.temperature == 0.7
    assert settings.max_tokens == 512

def test_load_settings_from_file(tmp_path):
    config_data = {
        "llm_mode": "local",
        "local_model_path": "test_model.gguf",
        "temperature": 0.5,
        "max_tokens": 100,
        "system_prompt": "Test Prompt"
    }
    
    config_file = tmp_path / "config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config_data, f)
        
    settings = load_settings(config_file)
    assert settings.llm_mode == "local"
    assert settings.local_model_path == "test_model.gguf"
    assert settings.temperature == 0.5
    assert settings.max_tokens == 100
    assert settings.system_prompt == "Test Prompt"
