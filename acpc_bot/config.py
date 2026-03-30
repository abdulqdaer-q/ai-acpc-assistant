import os
from dataclasses import dataclass
from pathlib import Path

from .bot_config import BotConfig


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    bot_config_file: Path
    bot_config: BotConfig
    telegram_bot_token: str
    telegram_api_id: int
    telegram_api_hash: str
    telegram_session_name: str
    telegram_workdir: Path
    llm_provider: str
    openai_api_key: str
    openai_model: str
    gemini_api_key: str
    gemini_model: str
    ollama_url: str
    ollama_model: str
    final_memory_file: Path
    chunk_summaries_file: Path
    state_file: Path
    max_history_messages: int
    llm_timeout_seconds: int
    request_timeout_seconds: int
    telegram_send_limit: int

    @classmethod
    def from_env(cls) -> "Settings":
        bot_config_file = Path(os.getenv("BOT_CONFIG_FILE", "bot_config.json"))
        return cls(
            bot_config_file=bot_config_file,
            bot_config=BotConfig.load(bot_config_file),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            telegram_api_id=_env_int("TELEGRAM_API_ID", 0),
            telegram_api_hash=os.getenv("TELEGRAM_API_HASH", "").strip(),
            telegram_session_name=os.getenv("TELEGRAM_SESSION_NAME", "acpc_mentor_bot").strip(),
            telegram_workdir=Path(os.getenv("TELEGRAM_WORKDIR", ".pyrogram")),
            llm_provider=os.getenv("LLM_PROVIDER", "auto").strip().lower(),
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
            ollama_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate").strip(),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b").strip(),
            final_memory_file=Path(os.getenv("FINAL_MEMORY_FILE", "final_memory.json")),
            chunk_summaries_file=Path(os.getenv("CHUNK_SUMMARIES_FILE", "chunk_summaries.json")),
            state_file=Path(os.getenv("BOT_STATE_FILE", "telegram_bot_state.json")),
            max_history_messages=_env_int("MAX_HISTORY_MESSAGES", 8),
            llm_timeout_seconds=_env_int("LLM_TIMEOUT_SECONDS", 180),
            request_timeout_seconds=_env_int("REQUEST_TIMEOUT_SECONDS", 60),
            telegram_send_limit=_env_int("TELEGRAM_SEND_LIMIT", 3900),
        )

    def resolved_provider(self) -> str:
        if self.llm_provider in {"openai", "gemini", "ollama"}:
            return self.llm_provider
        if self.openai_api_key:
            return "openai"
        if self.gemini_api_key:
            return "gemini"
        return "ollama"

    def resolved_model(self) -> str:
        provider = self.resolved_provider()
        if provider == "openai":
            return self.openai_model
        if provider == "gemini":
            return self.gemini_model
        return self.ollama_model

    def validate(self) -> None:
        if not self.bot_config_file.exists():
            raise FileNotFoundError(f"Missing {self.bot_config_file}")
        if not self.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set.")
        if not self.telegram_api_id:
            raise RuntimeError("TELEGRAM_API_ID is not set.")
        if not self.telegram_api_hash:
            raise RuntimeError("TELEGRAM_API_HASH is not set.")
        if not self.final_memory_file.exists():
            raise FileNotFoundError(f"Missing {self.final_memory_file}")
        if not self.chunk_summaries_file.exists():
            raise FileNotFoundError(f"Missing {self.chunk_summaries_file}")

        provider = self.resolved_provider()
        if provider == "openai" and not self.openai_api_key:
            raise RuntimeError("LLM_PROVIDER=openai requires OPENAI_API_KEY.")
        if provider == "gemini" and not self.gemini_api_key:
            raise RuntimeError("LLM_PROVIDER=gemini requires GEMINI_API_KEY.")

        self.telegram_workdir.mkdir(parents=True, exist_ok=True)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
