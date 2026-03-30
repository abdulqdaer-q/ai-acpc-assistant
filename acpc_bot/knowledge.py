import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Settings
from .security import detect_injection_signals
from .text_utils import detect_taxonomy, normalize_space, tokenize


CODEFORCES_ID_PATTERN = re.compile(r"\b\d{3,4}[A-Z]\d?\b", re.IGNORECASE)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _coerce_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def _normalize_problem_id(value: Any) -> str:
    return normalize_space(str(value or "")).lower()


def extract_problem_ids(text: str) -> set[str]:
    return {match.group(0).lower() for match in CODEFORCES_ID_PATTERN.finditer(text or "")}


@dataclass(frozen=True)
class KnowledgeDocument:
    doc_id: str
    source: str
    source_weight: float
    doc_type: str
    title: str
    summary: str
    topics: list[str]
    highlights: list[str]
    action_items: list[str]
    open_questions: list[str]
    taxonomy: list[str]
    problem_id: str
    url: str
    language: str
    start_date: str
    end_date: str
    metadata: dict[str, Any]
    search_text: str
    tokens: set[str]
    topic_tokens: set[str]
    injection_signals: tuple[str, ...]


def _source_weight(source: str, settings: Settings) -> float:
    return float(settings.bot_config.retrieval.source_weights.get(source, 1.0))


def _build_document(
    *,
    doc_id: str,
    source: str,
    doc_type: str,
    title: str,
    summary: str,
    topics: list[str],
    highlights: list[str],
    action_items: list[str],
    open_questions: list[str],
    problem_id: str,
    url: str,
    language: str,
    start_date: str,
    end_date: str,
    metadata: dict[str, Any],
    settings: Settings,
) -> KnowledgeDocument:
    search_parts = [
        title,
        summary,
        *topics,
        *highlights,
        *action_items,
        *open_questions,
        problem_id,
        url,
    ]
    search_text = "\n".join(part for part in search_parts if part)
    return KnowledgeDocument(
        doc_id=doc_id,
        source=source,
        source_weight=_source_weight(source, settings),
        doc_type=doc_type,
        title=title,
        summary=summary,
        topics=topics,
        highlights=highlights,
        action_items=action_items,
        open_questions=open_questions,
        taxonomy=detect_taxonomy(search_text),
        problem_id=_normalize_problem_id(problem_id),
        url=str(url or "").strip(),
        language=str(language or "en").strip(),
        start_date=str(start_date or "").strip(),
        end_date=str(end_date or "").strip(),
        metadata=metadata,
        search_text=search_text,
        tokens=set(tokenize(search_text)),
        topic_tokens=set(tokenize(" ".join(topics))),
        injection_signals=tuple(detect_injection_signals(search_text)),
    )


def build_chunk_document(raw: dict[str, Any], settings: Settings) -> KnowledgeDocument:
    chunk_index = int(raw.get("chunk_index", 0))
    return _build_document(
        doc_id=f"acpc_chunk:{chunk_index}",
        source="acpc_chunk",
        doc_type="chat_chunk",
        title=f"ACPC chunk {chunk_index}",
        summary=str(raw.get("summary", "")),
        topics=_coerce_list(raw.get("topics")),
        highlights=_coerce_list(raw.get("highlights")),
        action_items=_coerce_list(raw.get("action_items")),
        open_questions=_coerce_list(raw.get("open_questions")),
        problem_id="",
        url="",
        language="mixed",
        start_date=str(raw.get("start_date", "")),
        end_date=str(raw.get("end_date", "")),
        metadata={
            "message_count": raw.get("message_count"),
            "sender_count": raw.get("sender_count"),
            "top_senders": raw.get("top_senders", []),
        },
        settings=settings,
    )


def build_final_memory_document(final_memory: dict[str, Any], settings: Settings) -> KnowledgeDocument:
    return _build_document(
        doc_id="acpc_memory:overview",
        source="acpc_memory",
        doc_type="camp_overview",
        title=str(final_memory.get("chat_name", "ACPC camp overview")),
        summary=str(final_memory.get("summary", "")),
        topics=_coerce_list(final_memory.get("major_topics")),
        highlights=_coerce_list(final_memory.get("highlights")),
        action_items=_coerce_list(final_memory.get("action_items")),
        open_questions=_coerce_list(final_memory.get("open_questions")),
        problem_id="",
        url="",
        language="mixed",
        start_date=str(final_memory.get("date_range", {}).get("start", "")),
        end_date=str(final_memory.get("date_range", {}).get("end", "")),
        metadata={"chunk_count": final_memory.get("chunk_count")},
        settings=settings,
    )


def build_external_document(raw: dict[str, Any], settings: Settings, line_number: int) -> KnowledgeDocument:
    source = str(raw.get("source", "external_curated")).strip() or "external_curated"
    title = str(raw.get("title", "")).strip() or f"{source} document {line_number}"
    summary = str(raw.get("summary", "")).strip() or str(raw.get("text", "")).strip()
    tags = _coerce_list(raw.get("tags"))
    topics = _coerce_list(raw.get("topics")) or tags
    highlights = _coerce_list(raw.get("highlights"))

    return _build_document(
        doc_id=str(raw.get("doc_id", f"{source}:{line_number}")).strip(),
        source=source,
        doc_type=str(raw.get("doc_type", "reference_note")).strip(),
        title=title,
        summary=summary,
        topics=topics,
        highlights=highlights,
        action_items=_coerce_list(raw.get("action_items")),
        open_questions=_coerce_list(raw.get("open_questions")),
        problem_id=str(raw.get("problem_id", "")),
        url=str(raw.get("url", "")),
        language=str(raw.get("language", "en")),
        start_date="",
        end_date="",
        metadata={
            "contest": raw.get("contest"),
            "difficulty": raw.get("difficulty"),
            "tags": tags,
        },
        settings=settings,
    )


def load_external_documents(path: Path, settings: Settings) -> list[KnowledgeDocument]:
    if not path.exists():
        return []

    documents: list[KnowledgeDocument] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise RuntimeError(f"Invalid JSON in {path}:{line_number}: {error.msg}") from error
            if not isinstance(raw, dict):
                continue
            documents.append(build_external_document(raw, settings, line_number))
    return documents


class KnowledgeBase:
    def __init__(
        self,
        final_memory: dict[str, Any],
        documents: list[KnowledgeDocument],
        chunk_documents: list[KnowledgeDocument],
    ) -> None:
        self.final_memory = final_memory
        self.documents = documents
        self.chunks = chunk_documents

    @classmethod
    def load(cls, settings: Settings) -> "KnowledgeBase":
        final_memory = load_json(settings.final_memory_file)
        raw_chunks = load_json(settings.chunk_summaries_file)

        chunk_documents = [build_chunk_document(item, settings) for item in raw_chunks]
        documents = [build_final_memory_document(final_memory, settings), *chunk_documents]
        documents.extend(load_external_documents(settings.external_documents_file, settings))

        return cls(
            final_memory=final_memory,
            documents=documents,
            chunk_documents=chunk_documents,
        )

    def search(self, query: str, limit: int) -> list[KnowledgeDocument]:
        query_tokens = tokenize(query)
        query_text = normalize_space(query).lower()
        query_taxonomy = detect_taxonomy(query)
        query_problem_ids = extract_problem_ids(query)

        scored: list[tuple[float, str, KnowledgeDocument]] = []
        for document in self.documents:
            score = 0.0

            for token in query_tokens:
                if token in document.tokens:
                    score += 2.0
                if token in document.topic_tokens:
                    score += 4.0

            if query_text and query_text in document.search_text.lower():
                score += 8.0

            for label in query_taxonomy:
                if label in document.taxonomy:
                    score += 6.0

            if query_problem_ids and document.problem_id in query_problem_ids:
                score += 15.0

            if score > 0:
                if document.injection_signals:
                    score *= 0.35
                scored.append((score * document.source_weight, document.doc_id, document))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored[:limit]]

    def document_counts_by_source(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for document in self.documents:
            counts[document.source] = counts.get(document.source, 0) + 1
        return dict(sorted(counts.items()))
