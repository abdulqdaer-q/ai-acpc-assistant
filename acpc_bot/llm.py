from typing import Protocol

import requests

from .config import Settings


class LLMClient(Protocol):
    def generate(self, system_prompt: str, prompt: str) -> str:
        ...


class OpenAIResponsesClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()

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

        response = self.session.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        return self._extract_text(response.json())

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


class GeminiClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()

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

        response = self.session.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.settings.gemini_model}:generateContent",
            headers={
                "x-goog-api-key": self.settings.gemini_api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        return self._extract_text(response.json())

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


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()

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

        response = self.session.post(
            self.settings.ollama_url,
            json=payload,
            timeout=self.settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
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
