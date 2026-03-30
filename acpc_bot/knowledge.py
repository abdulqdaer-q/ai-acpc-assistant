import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Settings
from .text_utils import detect_taxonomy, normalize_space, tokenize


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


@dataclass(frozen=True)
class ChunkDocument:
    chunk_index: int
    start_date: str
    end_date: str
    summary: str
    topics: list[str]
    highlights: list[str]
    action_items: list[str]
    open_questions: list[str]
    taxonomy: list[str]
    search_text: str
    tokens: set[str]
    topic_tokens: set[str]


def build_chunk_document(raw: dict[str, Any]) -> ChunkDocument:
    search_parts = [
        raw.get("summary", ""),
        *raw.get("topics", []),
        *raw.get("highlights", []),
        *raw.get("action_items", []),
        *raw.get("open_questions", []),
    ]
    search_text = "\n".join(part for part in search_parts if part)
    return ChunkDocument(
        chunk_index=int(raw.get("chunk_index", 0)),
        start_date=str(raw.get("start_date", "")),
        end_date=str(raw.get("end_date", "")),
        summary=str(raw.get("summary", "")),
        topics=[str(item) for item in raw.get("topics", [])],
        highlights=[str(item) for item in raw.get("highlights", [])],
        action_items=[str(item) for item in raw.get("action_items", [])],
        open_questions=[str(item) for item in raw.get("open_questions", [])],
        taxonomy=detect_taxonomy(search_text),
        search_text=search_text,
        tokens=set(tokenize(search_text)),
        topic_tokens=set(tokenize(" ".join(raw.get("topics", [])))),
    )


class KnowledgeBase:
    def __init__(self, final_memory: dict[str, Any], chunks: list[ChunkDocument]) -> None:
        self.final_memory = final_memory
        self.chunks = chunks

    @classmethod
    def load(cls, settings: Settings) -> "KnowledgeBase":
        final_memory = load_json(settings.final_memory_file)
        raw_chunks = load_json(settings.chunk_summaries_file)
        chunks = [build_chunk_document(item) for item in raw_chunks]
        return cls(final_memory=final_memory, chunks=chunks)

    def search(self, query: str, limit: int) -> list[ChunkDocument]:
        query_tokens = tokenize(query)
        query_text = normalize_space(query).lower()
        query_taxonomy = detect_taxonomy(query)

        scored: list[tuple[int, int, ChunkDocument]] = []
        for chunk in self.chunks:
            score = 0

            for token in query_tokens:
                if token in chunk.tokens:
                    score += 2
                if token in chunk.topic_tokens:
                    score += 4

            if query_text and query_text in chunk.search_text.lower():
                score += 8

            for label in query_taxonomy:
                if label in chunk.taxonomy:
                    score += 6

            if score > 0:
                scored.append((score, chunk.chunk_index, chunk))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored[:limit]]
