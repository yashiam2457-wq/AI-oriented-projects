import argparse
import sys
from pathlib import Path

from modules.config.settings import load_settings
from modules.llm.llm_client import get_llm_client
from modules.ui.chat_interface import ChatInterface

def main():
    parser = argparse.ArgumentParser(description="VANI — Offline AI companion")
    parser.add_argument("--mode", choices=["server", "local"], help="LLM runtime mode: 'server' (LM Studio) or 'local' (llama-cpp)")
    parser.add_argument("--model-path", type=str, help="Path to local GGUF model file (local mode only)")
    parser.add_argument("--base-url", type=str, help="API base URL for server mode")
    parser.add_argument("--voice", action="store_true", help="Enable voice input on startup")
    parser.add_argument("--no-tts", action="store_true", help="Disable text-to-speech output")
    parser.add_argument("--no-memory", action="store_true", help="Disable session memory loading")
    parser.add_argument(
        "--whisper",
        choices=["tiny", "base"],
        help="Whisper STT model size: 'tiny' (~75 MB, fastest) or 'base' (~145 MB, recommended)",
    )
    args = parser.parse_args()

    # Load configuration
    config_path = Path(__file__).parent / "config.json"
    settings = load_settings(config_path)

    # Override config with CLI arguments
    if args.mode:
        settings.llm_mode = args.mode
    if args.model_path:
        settings.local_model_path = args.model_path
    if args.base_url:
        settings.server_base_url = args.base_url
    if args.voice:
        settings.voice_input_enabled = True
    if args.no_tts:
        settings.tts_enabled = False
    if args.no_memory:
        settings.memory_enabled = False
    if args.whisper:
        settings.whisper_model = args.whisper

    print("Starting VANI…")

    try:
        client = get_llm_client(settings)
    except Exception as e:
        print(f"\nInitialisation error: {e}", file=sys.stderr)
        print("Check your config.json or model server.", file=sys.stderr)
        sys.exit(1)

    ui = ChatInterface(client, settings)
    ui.start_loop()

if __name__ == "__main__":
    main()
