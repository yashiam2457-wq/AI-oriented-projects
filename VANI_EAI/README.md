# VANI - Offline Multimodal Emotional AI Companion (Phase 2)

VANI is a warm, calm, patient, and emotionally aware AI companion designed to provide offline emotional support. It operates fully locally on your machine, protecting user privacy by ensuring that no data is transmitted to external servers. It can operate either by running direct local inference using `llama-cpp-python` or by interfacing with local OpenAI-compatible APIs (like LM Studio or Ollama).

---

## Features

- **Empathetic Companion**: Tailored system instructions guide VANI to respond with empathy, avoiding common robotic phrases and clichés.
- **Offline local execution**: Support for running quantized models (in GGUF format) locally using `llama-cpp-python` for maximum security and privacy.
- **Offline Text-to-Speech (TTS)**: Real-time, queue-based, sentence-by-sentence voice responses using the local system synthesizer via `pyttsx3`.
- **External server support**: An alternative mode connects to local model servers such as LM Studio.
- **Rich CLI interface**: Live, real-time streaming of response tokens rendered beautifully in markdown formatting using the `rich` library.
- **Session state commands**: Easy-to-use in-session CLI commands (`/info`, `/clear`, `/tts`, `/exit`).
- **Pydantic configuration validation**: Strongly-typed and validated runtime settings.

---

## Directory Structure

```text
VANI/
├── main.py                    # Application entrypoint
├── config.json                # JSON configuration file for default settings
├── requirements.txt           # Python dependencies
├── modules/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py        # Settings configuration class (Pydantic)
│   ├── llm/
│   │   ├── __init__.py
│   │   └── llm_client.py      # LLM clients factory & concrete client classes
│   ├── tts/
│   │   ├── __init__.py
│   │   └── tts_client.py      # Background-threaded local TTS engine client
│   └── ui/
│       ├── __init__.py
│       └── chat_interface.py  # Interactive terminal user interface
└── tests/
    ├── test_config.py         # Tests for configuration schema loading
    ├── test_llm.py            # Tests and mocks for LLM clients
    └── test_tts.py            # Tests and mocks for TTS background queue engine
```

---

## Setup & Installation

### 1. Prerequisites
- **Python**: Version 3.8 or higher is recommended.
- **GGUF Model (Optional for local mode)**: Download a chat-instruct model (e.g., Mistral-7B-Instruct-v0.2.Q4_0.gguf) and place it locally in your file system.

### 2. Virtual Environment Setup
Create and activate a virtual environment to manage dependencies:

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows (PowerShell/CMD)
.\venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```

### 3. Dependency Installation
Install the required packages from `requirements.txt`:

```bash
pip install -r requirements.txt
```

> **Note**: Building `llama-cpp-python` from source might require C++ compiler tools installed on your operating system (like Build Tools for Visual Studio on Windows or Xcode Command Line Tools on macOS).

---

## Configuration

Configurations are declared in [config.json](file:///c:/Users/Loq/Documents/programs/VANI/config.json). Key settings include:
- `llm_mode`: The operational mode, either `"server"` (for external hosting) or `"local"` (for direct GGUF inference).
- `local_model_path`: File path to the GGUF model (used in local mode).
- `server_base_url`: Endpoint for local hosting servers (used in server mode).
- `temperature`: Creativity of the LLM responses (default `0.7`).
- `tts_enabled`: Activates Text-to-Speech audio synthesis (default `false`).
- `tts_rate`: Controls speech tempo (speed) in words per minute (default `175`).
- `tts_volume`: Controls speech volume from `0.0` to `1.0` (default `1.0`).
- `tts_voice_index`: Selects the synthesizer voice profile index (default `0`).
- `system_prompt`: Custom personality and guidelines for VANI.

---

## How to Run

VANI can be executed from the terminal using [main.py](file:///c:/Users/Loq/Documents/programs/VANI/main.py):

### 1. Server Mode (Default)
In server mode, VANI sends requests to a running OpenAI-compatible model host (e.g. LM Studio, Ollama):
```bash
python main.py --mode server
```

### 2. Local Mode
For direct, offline inference using `llama-cpp-python`:
```bash
python main.py --mode local --model-path <path_to_gguf_model>
```

### Command-Line Arguments
Override options can be passed to [main.py](file:///c:/Users/Loq/Documents/programs/VANI/main.py) on execution:
- `--mode`: Choose between `server` and `local`.
- `--model-path`: Path to a GGUF model file.
- `--base-url`: Custom endpoint for your model server.
- `--tts`: Force-enable Text-to-Speech voice synthesis on startup.

---

## Using VANI Chat Interface

Once VANI has initialized, you will enter the interactive CLI. The interface supports the following commands:
- `/clear`: Clear conversation history and start a new session.
- `/info`: Print current settings (mode, paths, temperature, TTS configurations).
- `/tts`: Toggle Text-to-Speech voice responses on or off dynamically.
- `/exit` or `/quit`: Cleanly terminate the VANI process.

---

## Verification & Testing

Verify your setup by running the test suite:
```bash
python -m pytest
```
All test suites verify both settings parsing (using temporary JSON configs) and mock prompt generation logic (ensuring the system prompt conforms to Mistral's instruct templates).
