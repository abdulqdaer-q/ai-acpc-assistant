from .bot_config import PromptConfig, RetrievalConfig
from .knowledge import ChunkDocument
from .text_utils import add_line_numbers, detect_taxonomy, extract_code_snippet

def render_global_context(final_memory: dict, retrieval_config: RetrievalConfig) -> str:
    return (
        f"Chat summary: {final_memory.get('summary', '')}\n"
        f"Major topics: {', '.join(final_memory.get('major_topics', [])) or 'n/a'}\n"
        f"Highlights: {' | '.join(final_memory.get('highlights', [])[:retrieval_config.global_highlights_limit]) or 'n/a'}\n"
        f"Open questions: {' | '.join(final_memory.get('open_questions', [])[:retrieval_config.global_open_questions_limit]) or 'n/a'}"
    )


def render_chunk_context(chunks: list[ChunkDocument], retrieval_config: RetrievalConfig) -> str:
    if not chunks:
        return "No closely matching camp-memory chunks were retrieved."

    rendered = []
    for chunk in chunks:
        rendered.append(
            "\n".join(
                [
                    f"Chunk {chunk.chunk_index} | {chunk.start_date} -> {chunk.end_date}",
                    f"Topics: {', '.join(chunk.topics) or 'n/a'}",
                    f"Summary: {chunk.summary}",
                    f"Highlights: {' | '.join(chunk.highlights[:retrieval_config.chunk_highlights_limit]) or 'n/a'}",
                    f"Open questions: {' | '.join(chunk.open_questions[:retrieval_config.chunk_open_questions_limit]) or 'n/a'}",
                ]
            )
        )
    return "\n\n".join(rendered)


def build_user_prompt(
    question: str,
    conversation_history: str,
    final_memory: dict,
    retrieved_chunks: list[ChunkDocument],
    prompt_config: PromptConfig,
    retrieval_config: RetrievalConfig,
) -> str:
    taxonomy = detect_taxonomy(question)
    code_snippet = extract_code_snippet(question)
    labels = prompt_config.labels
    code_section = prompt_config.no_code_text

    if code_snippet:
        code_section = f"{labels['code']}:\n" + add_line_numbers(code_snippet)

    response_requirements = "\n".join(
        f"- {requirement}" for requirement in prompt_config.response_requirements
    )
    return (
        f"{labels['student_question']}:\n{question.strip()}\n\n"
        f"{labels['detected_taxonomy']}:\n{', '.join(taxonomy) if taxonomy else prompt_config.no_taxonomy_text}\n\n"
        f"{labels['conversation_history']}:\n{conversation_history}\n\n"
        f"{labels['global_memory']}:\n{render_global_context(final_memory, retrieval_config)}\n\n"
        f"{labels['retrieved_chunks']}:\n{render_chunk_context(retrieved_chunks, retrieval_config)}\n\n"
        f"{code_section}\n\n"
        f"Response requirements:\n{response_requirements}"
    )
