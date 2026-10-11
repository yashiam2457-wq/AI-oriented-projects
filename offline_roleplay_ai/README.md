# Offline Roleplay AI Framework

A production-quality, fully offline **Character Simulation Engine** running entirely in your terminal using Python, SQLite, and LM Studio (OpenAI-compatible local server) hosting Mistral 7B Instruct.

---

## Key Features

- **100% Offline & Private**: Zero cloud calls, zero external APIs, zero telemetry.
- **Deep Persona Simulation**: Supports over 60 character fields (traits, bio, beliefs, catchphrases, speech style, combat style, boundaries, system & roleplay directives).
- **Auto-Repair Persona Engine**: Automatically validates character JSON files and supplies sensible default fallbacks for missing fields.
- **Hierarchical Memory**: Working, Recent, Long-Term, Story, Character, Relationship, Event, User, and World memory layers.
- **Offline BM25 / Keyword Retrieval**: Ranks and injects top-K relevant memories into prompt context without heavy online vector embedding services.
- **Runtime Character Switching**: Instantly switch active character persona with `/switch <name>` during ongoing conversations with strict memory isolation.
- **Multi-Character Support**: Manage party rosters with `/add`, `/remove`, `/list` for party conversations.
- **6 Roleplay Modes**: Single Character, Multi Character, Narrator Only, Character + Narrator, Interactive Story, and Sandbox Mode.
- **SQLite Persistence**: Complete history tracking, session save/load, export/import, message search (`/search`), and background chat summarization.

---

## File Architecture

```
offline_roleplay_ai/
├── main.py                     # Terminal UI, Story Starter Wizard, & REPL Command Parser
├── config.py                   # System options, LM Studio settings, paths, & modes
├── character.py                # 60+ field persona schema, auto-repair, & party manager
├── memory.py                   # Hierarchical memory system & BM25 offline retrieval
├── analyzer.py                 # Message intent parsing, action/dialogue separation, tone & memory auto-seeding
├── progression.py              # Narrative arc tracker, chapter/pacing state, milestones, & relationship trust
├── engine.py                   # LM Studio REST client, context budget manager, summarizer, & prompt builder
├── session.py                  # SQLite database engine, session state persistence, & export/import
├── characters/
│   ├── default_persona.json    # Complete sample character template (Aiden Vance)
│   └── narrator.json           # Narrator persona template
├── test_engine.py              # Pytest automated test suite
└── README.md                   # Complete documentation guide
```

---

## Setup & Prerequisites

### 1. LM Studio Setup
1. Download and launch [LM Studio](https://lmstudio.ai/).
2. Download **Mistral 7B Instruct** (or any GGUF model).
3. Start the **Local Server** in LM Studio (default port: `1234`, endpoint: `http://localhost:1234/v1`).

### 2. Python Environment
Requires Python 3.11+.

```bash
cd c:/Users/Loq/Documents/programs/offline_roleplay_ai
python -m pytest test_engine.py
```

---

## Usage Guide

Run the framework directly from the command line:

```bash
python main.py
```

### Story Starter Wizard
Upon launch, you will be presented with the interactive setup:
1. **Create New Story**: Prompted for title, genre, theme, setting, scenario, goal, and roleplay mode.
2. **Startup Mode**: Choose between automatically generating an opening scene or writing the first message yourself.
3. **Load Previous Session**: Resume an existing roleplay session right where you stopped.

---

## Terminal Command Reference

During conversation, type any `/command`:

| Command | Description |
|---|---|
| `/help` | Display terminal command reference |
| `/list` | List all loaded characters & active party members |
| `/switch <name>` | Instantly switch active primary persona |
| `/add <name>` | Add character persona to active party roster |
| `/remove <name>` | Remove character persona from active party |
| `/progression` | Inspect story arc phase, chapter, tension, milestones, objectives & relationship trust |
| `/analyze` | View intent, dialogue/action breakdown, emotional tone & auto-memories of latest message |
| `/save` | Save active session state and hierarchical memories |
| `/load <session_id>` | Load a saved roleplay session |
| `/export [filename]` | Export session history and memories to JSON |
| `/import <filename>` | Import session from JSON export file |
| `/story` | Display current story context, setting, and goal |
| `/summary` | View current story summary |
| `/memory` | Inspect recent retrieved long-term memories |
| `/search <query>` | Search past messages and memories |
| `/history` | Display recent conversation history |
| `/reset` | Clear chat history of active session |
| `/exit` | Save session state and exit engine |

---

## Character JSON Schema (60+ Fields)

Character JSON files located in `characters/` include fields such as:

- `character_id`, `character_name`, `nickname`, `aliases`, `age`, `gender`, `occupation`, `species`, `nationality`, `language`
- `background`, `biography`, `appearance`, `personality_traits`, `strengths`, `weaknesses`, `goals`, `motivations`, `beliefs`, `values`, `fears`, `likes`, `dislikes`, `hobbies`
- `speaking_style`, `vocabulary`, `formality`, `humor_level`, `emotion_style`, `intelligence`, `knowledge_areas`
- `behavior_rules`, `conversation_style`, `response_length_preference`, `catchphrases`
- `relationships`, `family`, `friends`, `enemies`, `secrets`, `skills`, `combat_style`, `special_abilities`
- `world_rules`, `story_context`, `current_mood`, `current_location`, `current_situation`
- `memory_rules`, `forbidden_topics`, `boundaries`, `system_rules`, `roleplay_rules`, `custom_instructions`
- `example_dialogues`, `example_reactions`, `example_internal_thoughts`, `example_narration_style`, `metadata`

---

## Troubleshooting

- **LM Studio Connection Error**: Verify LM Studio server is running on `http://localhost:1234`. Test in browser at `http://localhost:1234/v1/models`.
- **Context Trimming**: The engine automatically trims older chat history turns when approaching model context limits while retaining system prompt directives.
