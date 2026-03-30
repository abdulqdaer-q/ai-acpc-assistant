import time
from typing import Protocol

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import Settings


class LLMClient(Protocol):
    def generate(self, system_prompt: str, prompt: str) -> str:
        ...


class BaseHTTPClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ai-acpc-assistant/1.0"})
        retry = Retry(
            total=self.settings.bot_config.llm.max_retries,
            connect=self.settings.bot_config.llm.max_retries,
            read=self.settings.bot_config.llm.max_retries,
            status=self.settings.bot_config.llm.max_retries,
            backoff_factor=self.settings.bot_config.llm.retry_backoff_seconds,
            status_forcelist=(408, 429, 500, 502, 503, 504),
            allowed_methods=frozenset({"POST"}),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _post_json(self, url: str, *, headers: dict[str, str] | None = None, json_body: dict) -> dict:
        last_error: Exception | None = None
        for attempt in range(1, self.settings.bot_config.llm.max_retries + 1):
            try:
                response = self.session.post(
                    url,
                    headers=headers,
                    json=json_body,
                    timeout=(
                        self.settings.request_timeout_seconds,
                        self.settings.llm_timeout_seconds,
                    ),
                )
                response.raise_for_status()
                return response.json()
            except Exception as error:
                last_error = error
                if attempt == self.settings.bot_config.llm.max_retries:
                    break
                time.sleep(self.settings.bot_config.llm.retry_backoff_seconds * attempt)

        raise RuntimeError(f"LLM request failed after retries: {last_error}") from last_error


class OpenAIResponsesClient(BaseHTTPClient):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)

    def generate(self, system_prompt: str, prompt: str) -> str:
        payload = {
            "model": self.settings.openai_model,
            "temperature": self.settings.bot_config.llm.temperature,
            "max_output_tokens": self.settings.bot_config.llm.openai_max_output_tokens,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                },
            ],
        }
        body = self._post_json(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json_body=payload,
        )
        return self._extract_text(body)

    @staticmethod
    def _extract_text(body: dict) -> str:
        texts = []
        for item in body.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    text = str(content.get("text", "")).strip()
                    if text:
                        texts.append(text)

        combined = "\n".join(texts).strip()
        if combined:
            return combined

        error = body.get("error")
        if error:
            raise RuntimeError(f"OpenAI response error: {error}")
        raise RuntimeError("OpenAI returned no output_text content.")


class GeminiClient(BaseHTTPClient):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)

    def generate(self, system_prompt: str, prompt: str) -> str:
        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": self.settings.bot_config.llm.temperature,
                "maxOutputTokens": self.settings.bot_config.llm.gemini_max_output_tokens,
            },
        }
        body = self._post_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.settings.gemini_model}:generateContent",
            headers={
                "x-goog-api-key": self.settings.gemini_api_key,
                "Content-Type": "application/json",
            },
            json_body=payload,
        )
        return self._extract_text(body)

    @staticmethod
    def _extract_text(body: dict) -> str:
        texts = []
        for candidate in body.get("candidates", []):
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                text = str(part.get("text", "")).strip()
                if text:
                    texts.append(text)

        combined = "\n".join(texts).strip()
        if combined:
            return combined

        prompt_feedback = body.get("promptFeedback")
        if prompt_feedback:
            raise RuntimeError(f"Gemini returned no candidates: {prompt_feedback}")
        raise RuntimeError("Gemini returned no text output.")


class OllamaClient(BaseHTTPClient):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)

    def generate(self, system_prompt: str, prompt: str) -> str:
        payload = {
            "model": self.settings.ollama_model,
            "system": system_prompt,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.settings.bot_config.llm.temperature,
                "num_ctx": self.settings.bot_config.llm.ollama_num_ctx,
            },
        }
        body = self._post_json(
            self.settings.ollama_url,
            json_body=payload,
        )
        text = str(body.get("response", "")).strip()
        if not text:
            raise RuntimeError("Ollama returned an empty response.")
        return text


def build_llm_client(settings: Settings) -> LLMClient:
    provider = settings.resolved_provider()
    if provider == "openai":
        return OpenAIResponsesClient(settings)
    if provider == "gemini":
        return GeminiClient(settings)
    return OllamaClient(settings)
