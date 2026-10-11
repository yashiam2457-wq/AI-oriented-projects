import sys
from unittest.mock import MagicMock, patch
import pytest
from modules.config.settings import Settings
from modules.llm.llm_client import LocalServerClient, LlamaCppClient, get_llm_client

def test_local_server_client_generation():
    # Setup settings
    settings = Settings(llm_mode="server", server_base_url="http://mock-url/v1", server_api_key="mock-key")
    
    # Mock OpenAI
    mock_openai = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Hello from mock server"
    mock_response.choices = [mock_choice]
    mock_openai.chat.completions.create.return_value = mock_response

    with patch("openai.OpenAI", return_value=mock_openai):
        client = LocalServerClient(settings)
        response = client.generate_response([{"role": "user", "content": "Hi"}])
        
        assert response == "Hello from mock server"
        mock_openai.chat.completions.create.assert_called_once()


def test_local_server_client_stream():
    settings = Settings(llm_mode="server", server_base_url="http://mock-url/v1", server_api_key="mock-key")
    
    # Mock stream response
    mock_openai = MagicMock()
    chunk1 = MagicMock()
    chunk1.choices = [MagicMock()]
    chunk1.choices[0].delta.content = "Hello "
    chunk2 = MagicMock()
    chunk2.choices = [MagicMock()]
    chunk2.choices[0].delta.content = "world"
    mock_openai.chat.completions.create.return_value = [chunk1, chunk2]

    with patch("openai.OpenAI", return_value=mock_openai):
        client = LocalServerClient(settings)
        stream = client.generate_stream([{"role": "user", "content": "Hi"}])
        response = "".join(list(stream))
        
        assert response == "Hello world"


def test_llama_cpp_client_prompt_conversion():
    # Set mock_mode attribute dynamically or mock model path check
    settings = Settings(llm_mode="local", local_model_path="mock_model.gguf")
    settings_dict = settings.__dict__
    settings_dict["_mock_mode"] = True
    
    mock_llama = MagicMock()
    
    with patch("llama_cpp.Llama", return_value=mock_llama):
        client = LlamaCppClient(settings)
        
        # Test Mistral instruct format conversion
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"}
        ]
        prompt = client._convert_messages_to_prompt(messages)
        expected_prompt = (
            "<s>[INST] <<SYS>>\nSystem prompt\n<</SYS>>\n"
            "Hello [/INST] Hi there</s>"
            " [INST] How are you? [/INST]"
        )
        assert prompt == expected_prompt


def test_get_llm_client_factory():
    settings_server = Settings(llm_mode="server")
    with patch("openai.OpenAI"):
        client = get_llm_client(settings_server)
        assert isinstance(client, LocalServerClient)
        
    settings_local = Settings(llm_mode="local", local_model_path="mock_model.gguf")
    settings_local.__dict__["_mock_mode"] = True
    with patch("llama_cpp.Llama"):
        client = get_llm_client(settings_local)
        assert isinstance(client, LlamaCppClient)
        
    with pytest.raises(ValueError):
        invalid_settings = Settings(llm_mode="invalid")
        get_llm_client(invalid_settings)
