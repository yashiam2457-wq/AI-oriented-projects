import sys
from abc import ABC, abstractmethod
from typing import Iterator, List, Dict
from modules.config.settings import Settings

class LLMClient(ABC):
    """Abstract base class for all LLM clients in VANI."""
    
    @abstractmethod
    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate a complete response for the given conversation history."""
        pass
        
    @abstractmethod
    def generate_stream(self, messages: List[Dict[str, str]]) -> Iterator[str]:
        """Stream chunks of response for the given conversation history."""
        pass


class LocalServerClient(LLMClient):
    """Client for connecting to an OpenAI-compatible local API server (e.g., LM Studio)."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        try:
            from openai import OpenAI
            self.client = OpenAI(
                base_url=settings.server_base_url,
                api_key=settings.server_api_key
            )
        except ImportError:
            print("Error: The 'openai' package is required for Server mode but is not installed.", file=sys.stderr)
            raise

    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        response = self.client.chat.completions.create(
            model=self.settings.model_name,
            messages=messages,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens
        )
        return response.choices[0].message.content or ""

    def generate_stream(self, messages: List[Dict[str, str]]) -> Iterator[str]:
        response = self.client.chat.completions.create(
            model=self.settings.model_name,
            messages=messages,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
            stream=True
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class LlamaCppClient(LLMClient):
    """Client for direct local inference using llama-cpp-python GGUF loading."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        try:
            from llama_cpp import Llama
        except ImportError:
            print("Error: The 'llama-cpp-python' package is required for Local mode but is not installed.", file=sys.stderr)
            raise
            
        if not settings.local_model_path:
            raise ValueError("Local model path is not specified in settings.")
            
        model_path = settings.local_model_path
        # Check if model exists
        if not hasattr(self, "_mock_mode") and not getattr(settings, "_mock_mode", False):
            import os
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found at {model_path}. Please download it or adjust local_model_path.")

        self.llm = Llama(
            model_path=model_path,
            n_ctx=settings.n_ctx,
            n_gpu_layers=settings.n_gpu_layers,
            verbose=False
        )

    def _convert_messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert chat messages list to Mistral instruct chat template prompt.
        
        Mistral instruct format:
        <s>[INST] Instruction [/INST] Model answer</s>[INST] Follow-up [/INST]
        """
        prompt = ""
        has_system = any(msg.get("role") == "system" for msg in messages)
        first_user = True
        
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                # Inject system prompt at the very beginning inside instruction block
                prompt += f"<s>[INST] <<SYS>>\n{content}\n<</SYS>>\n"
            elif role == "user":
                if first_user:
                    if has_system:
                        # Append content directly to the already opened INST block
                        prompt += f"{content} [/INST]"
                    else:
                        prompt += f"<s>[INST] {content} [/INST]"
                    first_user = False
                else:
                    # Append user follow-up
                    prompt += f" [INST] {content} [/INST]"
            elif role == "assistant":
                prompt += f" {content}</s>"
        return prompt

    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        prompt = self._convert_messages_to_prompt(messages)
        response = self.llm(
            prompt,
            max_tokens=self.settings.max_tokens,
            temperature=self.settings.temperature,
            stop=["</s>", "[INST]"]
        )
        return response["choices"][0]["text"] or ""

    def generate_stream(self, messages: List[Dict[str, str]]) -> Iterator[str]:
        prompt = self._convert_messages_to_prompt(messages)
        response = self.llm(
            prompt,
            max_tokens=self.settings.max_tokens,
            temperature=self.settings.temperature,
            stop=["</s>", "[INST]"],
            stream=True
        )
        for chunk in response:
            text = chunk["choices"][0]["text"]
            if text:
                yield text


def get_llm_client(settings: Settings) -> LLMClient:
    """Factory function to instantiate the LLM client based on configured settings."""
    if settings.llm_mode == "server":
        return LocalServerClient(settings)
    elif settings.llm_mode == "local":
        return LlamaCppClient(settings)
    else:
        raise ValueError(f"Unknown LLM mode: {settings.llm_mode}")
