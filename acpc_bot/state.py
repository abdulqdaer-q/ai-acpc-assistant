import json
from pathlib import Path
from threading import RLock
from typing import Any

from .text_utils import truncate_text


class ConversationStateStore:
    def __init__(self, path: Path, max_history_messages: int) -> None:
        self.path = path
        self.max_history_messages = max_history_messages
        self._lock = RLock()
        self._state = self._load_state()

    def _empty_state(self) -> dict[str, Any]:
        return {"history": {}}

    def _load_state(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty_state()

        with self.path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return self._empty_state()

        data.setdefault("history", {})
        return data

    def _save_locked(self) -> None:
        self.path.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")

    def append_message(self, chat_id: int, role: str, content: str) -> None:
        with self._lock:
            key = str(chat_id)
            history = self._state.setdefault("history", {}).setdefault(key, [])
            history.append({"role": role, "content": content})
            self._state["history"][key] = history[-self.max_history_messages :]
            self._save_locked()

    def reset_history(self, chat_id: int) -> None:
        with self._lock:
            self._state.setdefault("history", {})[str(chat_id)] = []
            self._save_locked()

    def render_history(self, chat_id: int) -> str:
        with self._lock:
            history = list(self._state.get("history", {}).get(str(chat_id), []))

        if not history:
            return "No prior conversation."

        rendered = []
        for item in history[-self.max_history_messages :]:
            role = item.get("role", "user").capitalize()
            content = truncate_text(item.get("content", ""), 700)
            rendered.append(f"{role}: {content}")
        return "\n".join(rendered)
