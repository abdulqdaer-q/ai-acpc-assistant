import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = {
    "metadata": {
        "name": "ACPC Mentor Bot",
        "version": "1.0.0",
        "description": "Telegram bot that answers ACPC camp questions using extracted camp memory and an online or local LLM backend.",
        "owner": "ACPC Camp",
    },
    "prompts": {
        "system": (
            "Role: You are the Lead Technical Mentor for the ACPC (Arab Collegiate Programming Contest) Camp. "
            "You are a world-class expert in C++, Algorithms, and Distributed Systems with a teaching philosophy rooted in Guided Discovery.\n\n"
            "Core Instruction: When a student or participant asks for help with a problem (Codeforces, CSES, or Camp-specific), "
            "follow the ACPC Mentorship Protocol:\n\n"
            "1. The No-Spoil Discovery Phase\n"
            "- Do not provide the full code immediately.\n"
            "- Analyze constraints and time complexity tradeoffs, especially O(N log N) vs O(N^2).\n"
            "- Use Socratic hinting like: What happens if the input is already sorted? Can we reduce this to a Prefix Sum or frequency-counting problem?\n"
            "- Explain the algorithm with clear step-by-step logic or metaphors when useful.\n\n"
            "2. Technical Standards\n"
            "- Emphasize efficiency, unnecessary loops, and the right STL/container choice.\n"
            "- Force attention to edge cases: N=0, N=1, duplicates, negative numbers, overflow, and long long where needed.\n"
            "- Encourage clean competitive-programming C++ with ios::sync_with_stdio(0); cin.tie(0); while keeping readable variable names.\n\n"
            "3. Problem-Solving Taxonomy\n"
            "- If the student is stuck, classify the problem when useful using camp patterns such as Frequency Arrays/Sets, Binary Search/Logarithms, Graph Theory, Dynamic Programming, and Two Pointers / Prefix Sum.\n\n"
            "4. Code Review Style\n"
            "- If the student provides code, do not just fix it. Review it.\n"
            "- Point to the exact failing line if line numbers are available.\n"
            "- Explain why TLE, WA, RE, or overflow is happening.\n"
            "- Suggest the Walied Approach when appropriate: Can this be solved without a loop using math?\n\n"
            "5. Tone and Context\n"
            "- Tone: encouraging, professional, challenging, peer-mentor.\n"
            "- Language: English by default, but blend Arabic technical terms when helpful.\n"
            "- Always end with a short check-in question that helps the student take the next implementation step.\n\n"
            "Use the retrieved camp-memory context below as supporting background, not as a source of invented facts. "
            "If the context is weak or unrelated, say so briefly and still mentor from first principles."
        ),
        "labels": {
            "student_question": "Student question",
            "detected_taxonomy": "Detected taxonomy",
            "conversation_history": "Recent conversation with this student",
            "global_memory": "Global ACPC camp memory",
            "retrieved_chunks": "Retrieved relevant camp-memory chunks",
            "code": "Student code with line numbers",
        },
        "no_code_text": "No code provided.",
        "no_taxonomy_text": "No strong taxonomy match",
        "response_requirements": [
            "Do not dump the full solution immediately.",
            "Give a diagnosis, the next reasoning step, edge cases, and one check-in question.",
            "If code is present, review the student's logic instead of silently rewriting it.",
            "If Arabic phrasing helps, mix in short Arabic technical hints naturally.",
            "Keep the answer practical and specific.",
            "If the problem statement is incomplete or you are not confident, say that clearly, do not invent details, and ask for the missing statement, constraints, examples, or code.",
        ],
        "error_message": (
            "I could not generate a mentor response right now.\n"
            "Reason: {error}\n"
            "Check the selected LLM provider, credentials, and knowledge files."
        ),
    },
    "retrieval": {
        "max_chunks": 5,
        "global_highlights_limit": 4,
        "global_open_questions_limit": 4,
        "chunk_highlights_limit": 3,
        "chunk_open_questions_limit": 2,
    },
    "llm": {
        "temperature": 0.2,
        "openai_max_output_tokens": 900,
        "gemini_max_output_tokens": 900,
        "ollama_num_ctx": 8192,
    },
}


def _merge_defaults(defaults: Any, overrides: Any) -> Any:
    if isinstance(defaults, dict) and isinstance(overrides, dict):
        merged = dict(defaults)
        for key, value in overrides.items():
            merged[key] = _merge_defaults(defaults.get(key), value) if key in defaults else value
        return merged
    return overrides if overrides is not None else defaults


@dataclass(frozen=True)
class MetadataConfig:
    name: str
    version: str
    description: str
    owner: str


@dataclass(frozen=True)
class PromptConfig:
    system: str
    labels: dict[str, str]
    no_code_text: str
    no_taxonomy_text: str
    response_requirements: list[str]
    error_message: str


@dataclass(frozen=True)
class RetrievalConfig:
    max_chunks: int
    global_highlights_limit: int
    global_open_questions_limit: int
    chunk_highlights_limit: int
    chunk_open_questions_limit: int


@dataclass(frozen=True)
class LLMGenerationConfig:
    temperature: float
    openai_max_output_tokens: int
    gemini_max_output_tokens: int
    ollama_num_ctx: int


@dataclass(frozen=True)
class BotConfig:
    metadata: MetadataConfig
    prompts: PromptConfig
    retrieval: RetrievalConfig
    llm: LLMGenerationConfig

    @classmethod
    def load(cls, path: Path) -> "BotConfig":
        if not path.exists():
            raise FileNotFoundError(f"Missing bot config file: {path}")

        with path.open("r", encoding="utf-8") as file:
            raw = json.load(file)

        merged = _merge_defaults(DEFAULT_CONFIG, raw)
        metadata = merged["metadata"]
        prompts = merged["prompts"]
        retrieval = merged["retrieval"]
        llm = merged["llm"]

        return cls(
            metadata=MetadataConfig(
                name=str(metadata["name"]),
                version=str(metadata["version"]),
                description=str(metadata["description"]),
                owner=str(metadata["owner"]),
            ),
            prompts=PromptConfig(
                system=str(prompts["system"]),
                labels={str(key): str(value) for key, value in prompts["labels"].items()},
                no_code_text=str(prompts["no_code_text"]),
                no_taxonomy_text=str(prompts["no_taxonomy_text"]),
                response_requirements=[str(item) for item in prompts["response_requirements"]],
                error_message=str(prompts["error_message"]),
            ),
            retrieval=RetrievalConfig(
                max_chunks=int(retrieval["max_chunks"]),
                global_highlights_limit=int(retrieval["global_highlights_limit"]),
                global_open_questions_limit=int(retrieval["global_open_questions_limit"]),
                chunk_highlights_limit=int(retrieval["chunk_highlights_limit"]),
                chunk_open_questions_limit=int(retrieval["chunk_open_questions_limit"]),
            ),
            llm=LLMGenerationConfig(
                temperature=float(llm["temperature"]),
                openai_max_output_tokens=int(llm["openai_max_output_tokens"]),
                gemini_max_output_tokens=int(llm["gemini_max_output_tokens"]),
                ollama_num_ctx=int(llm["ollama_num_ctx"]),
            ),
        )
