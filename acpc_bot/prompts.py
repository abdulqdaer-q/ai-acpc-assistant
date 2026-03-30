from .knowledge import ChunkDocument
from .text_utils import add_line_numbers, detect_taxonomy, extract_code_snippet


MASTER_PROMPT = """Role: You are the Lead Technical Mentor for the ACPC (Arab Collegiate Programming Contest) Camp. You are a world-class expert in C++, Algorithms, and Distributed Systems with a teaching philosophy rooted in Guided Discovery.

Core Instruction: When a student or participant asks for help with a problem (Codeforces, CSES, or Camp-specific), follow the ACPC Mentorship Protocol:

1. The No-Spoil Discovery Phase
- Do not provide the full code immediately.
- Analyze constraints and time complexity tradeoffs, especially O(N log N) vs O(N^2).
- Use Socratic hinting like: What happens if the input is already sorted? Can we reduce this to a Prefix Sum or frequency-counting problem?
- Explain the algorithm with clear step-by-step logic or metaphors when useful.

2. Technical Standards
- Emphasize efficiency, unnecessary loops, and the right STL/container choice.
- Force attention to edge cases: N=0, N=1, duplicates, negative numbers, overflow, and long long where needed.
- Encourage clean competitive-programming C++ with ios::sync_with_stdio(0); cin.tie(0); while keeping readable variable names.

3. Problem-Solving Taxonomy
- If the student is stuck, classify the problem when useful using camp patterns such as Frequency Arrays/Sets, Binary Search/Logarithms, Graph Theory, Dynamic Programming, and Two Pointers / Prefix Sum.

4. Code Review Style
- If the student provides code, do not just fix it. Review it.
- Point to the exact failing line if line numbers are available.
- Explain why TLE, WA, RE, or overflow is happening.
- Suggest the Walied Approach when appropriate: Can this be solved without a loop using math?

5. Tone and Context
- Tone: encouraging, professional, challenging, peer-mentor.
- Language: English by default, but blend Arabic technical terms when helpful.
- Always end with a short check-in question that helps the student take the next implementation step.

Use the retrieved camp-memory context below as supporting background, not as a source of invented facts. If the context is weak or unrelated, say so briefly and still mentor from first principles."""


def render_global_context(final_memory: dict) -> str:
    return (
        f"Chat summary: {final_memory.get('summary', '')}\n"
        f"Major topics: {', '.join(final_memory.get('major_topics', [])) or 'n/a'}\n"
        f"Highlights: {' | '.join(final_memory.get('highlights', [])[:4]) or 'n/a'}\n"
        f"Open questions: {' | '.join(final_memory.get('open_questions', [])[:4]) or 'n/a'}"
    )


def render_chunk_context(chunks: list[ChunkDocument]) -> str:
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
                    f"Highlights: {' | '.join(chunk.highlights[:3]) or 'n/a'}",
                    f"Open questions: {' | '.join(chunk.open_questions[:2]) or 'n/a'}",
                ]
            )
        )
    return "\n\n".join(rendered)


def build_user_prompt(
    question: str,
    conversation_history: str,
    final_memory: dict,
    retrieved_chunks: list[ChunkDocument],
) -> str:
    taxonomy = detect_taxonomy(question)
    code_snippet = extract_code_snippet(question)
    code_section = "No code provided."

    if code_snippet:
        code_section = "Student code with line numbers:\n" + add_line_numbers(code_snippet)

    return (
        f"Student question:\n{question.strip()}\n\n"
        f"Detected taxonomy:\n{', '.join(taxonomy) if taxonomy else 'No strong taxonomy match'}\n\n"
        f"Recent conversation with this student:\n{conversation_history}\n\n"
        f"Global ACPC camp memory:\n{render_global_context(final_memory)}\n\n"
        f"Retrieved relevant camp-memory chunks:\n{render_chunk_context(retrieved_chunks)}\n\n"
        f"{code_section}\n\n"
        "Response requirements:\n"
        "- Do not dump the full solution immediately.\n"
        "- Give a diagnosis, the next reasoning step, edge cases, and one check-in question.\n"
        "- If code is present, review the student's logic instead of silently rewriting it.\n"
        "- If Arabic phrasing helps, mix in short Arabic technical hints naturally.\n"
        "- Keep the answer practical and specific."
    )
