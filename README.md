# ai-acpc-assistant

ACPC mentor bot for Telegram.

It answers programming-contest questions using:
- extracted ACPC camp knowledge from `chunk_summaries.json`
- global camp memory from `final_memory.json`
- a configurable mentorship prompt in `bot_config.json`
- a pluggable LLM backend: OpenAI, Gemini, or Ollama

## What It Does

- runs as a Telegram bot using Pyrogram
- retrieves relevant camp-memory chunks for each question
- follows a no-spoiler mentorship style instead of dumping code immediately
- reviews pasted code and asks follow-up questions
- keeps short per-chat memory in `telegram_bot_state.json`
- lets you tweak prompt text, retrieval limits, and generation settings without editing Python code

## Architecture

- entrypoint: [telegram_bot.py](/Users/aqassab/personal/ai-acpc-assistant/telegram_bot.py)
- runtime bootstrap: `acpc_bot/runner.py`
- Telegram app and handlers: `acpc_bot/app.py`
- config loading: `acpc_bot/config.py`
- bot behavior config: `acpc_bot/bot_config.py`
- retrieval and knowledge loading: `acpc_bot/knowledge.py`
- prompt assembly: `acpc_bot/prompts.py`
- LLM providers: `acpc_bot/llm.py`
- mentor orchestration: `acpc_bot/mentor.py`
- conversation state: `acpc_bot/state.py`

## Files Tracked vs Ignored

Tracked:
- `bot_config.json`
- `chunk_summaries.json`
- `final_memory.json`

Ignored:
- raw private export `telegram_chat.json`
- transient summarization state `progress.json`, `summaries.json`
- `.env`
- Pyrogram session directory `.pyrogram/`
- local bot memory `telegram_bot_state.json`

The deployment assumption is that derived knowledge files are safe to ship, while the raw chat export is not.

## Configuration

There are 2 configuration layers:

1. Environment variables for secrets and runtime wiring.
2. JSON config for prompt text, metadata, retrieval settings, and generation tuning.

### 1. Environment Variables

Start from `.env.example`:

```bash
cp .env.example .env
```

Required Telegram values:

```bash
TELEGRAM_BOT_TOKEN=...
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
```

Select one LLM provider:

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
```

or:

```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
```

or:

```bash
LLM_PROVIDER=ollama
OLLAMA_URL=http://127.0.0.1:11434/api/generate
OLLAMA_MODEL=qwen2.5:3b
```

### 2. JSON Bot Config

The file `bot_config.json` is the main place to tweak mentor behavior.

It contains:
- `metadata`: bot name, version, description, owner
- `prompts.system`: the full mentor system prompt
- `prompts.labels`: section labels used in the assembled user prompt
- `prompts.response_requirements`: output rules passed to the model
- `prompts.error_message`: runtime fallback message
- `retrieval`: how many chunks/highlights/open questions are injected
- `llm`: generation tuning like `temperature`, output-token caps, and Ollama context size

Example:

```json
{
  "metadata": {
    "name": "ACPC Mentor Bot",
    "version": "1.0.0"
  },
  "prompts": {
    "system": "Your full mentor prompt here",
    "response_requirements": [
      "Do not dump the full solution immediately.",
      "Always end with a check-in question."
    ]
  },
  "retrieval": {
    "max_chunks": 5
  },
  "llm": {
    "temperature": 0.2
  }
}
```

If you want a different config file:

```bash
export BOT_CONFIG_FILE=bot_config.json
```

## Install

```bash
./venv/bin/python -m pip install -r requirements.txt
```

## Run

```bash
set -a
source .env
set +a
./venv/bin/python telegram_bot.py
```

## Telegram Usage

In private chat:
- send any question directly

In groups:
- use `/ask <question>`
- mention the bot
- or reply to one of the bot messages

Supported commands:
- `/start`
- `/help`
- `/status`
- `/reset`
- `/ask`

## Deployment Notes

- Pyrogram requires `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`, not only the bot token.
- The bot stores its Telegram session in `.pyrogram/`.
- The bot stores short conversational memory in `telegram_bot_state.json`.
- For production, provide `.env`, keep `bot_config.json`, `chunk_summaries.json`, and `final_memory.json` next to the app.

## Development Notes

- Python code should stay simple and explicit.
- Prompt behavior should be changed in `bot_config.json`, not hardcoded in Python.
- Secrets must stay in `.env`, never in tracked source files.

## Verification

Basic local checks:

```bash
./venv/bin/python -m py_compile telegram_bot.py acpc_bot/*.py
```

This repo was verified with:
- `py_compile`
- import-level smoke tests for the Pyrogram app
- config-driven prompt assembly
