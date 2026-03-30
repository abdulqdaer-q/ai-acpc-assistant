import json
import os
import re
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

from tqdm import tqdm

# -----------------------------
# CONFIG
# -----------------------------
INPUT_FILE = "telegram_chat.json"
CHUNK_SUMMARIES_FILE = "chunk_summaries.json"
LEGACY_SUMMARIES_FILE = "summaries.json"
FINAL_MEMORY_FILE = "final_memory.json"
PROGRESS_FILE = "progress.json"
PIPELINE_VERSION = 4

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
OLLAMA_RETRIES = int(os.getenv("OLLAMA_RETRIES", "2"))

MAX_CHARS_PER_CHUNK = int(os.getenv("MAX_CHARS_PER_CHUNK", "12000"))
MAX_MESSAGE_CHARS_FOR_PROMPT = int(os.getenv("MAX_MESSAGE_CHARS_FOR_PROMPT", "500"))
MAX_CHARS_PER_SYNTHESIS_BATCH = int(os.getenv("MAX_CHARS_PER_SYNTHESIS_BATCH", "6000"))
MAX_SUMMARY_UNIT_CHARS = int(os.getenv("MAX_SUMMARY_UNIT_CHARS", "1000"))
TOP_SENDERS_PER_CHUNK = 5
TOP_SENDERS_FINAL = 15
TOP_DAYS_FINAL = 10

URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)


def normalize_message_text(raw_text):
    if isinstance(raw_text, str):
        return raw_text
    if isinstance(raw_text, dict):
        return str(raw_text.get("text", ""))
    if isinstance(raw_text, list):
        return "".join(normalize_message_text(part) for part in raw_text)
    if raw_text is None:
        return ""
    return str(raw_text)


def clean_text(text):
    text = URL_PATTERN.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def truncate_text(text, limit):
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def build_records(messages):
    records = []

    for message in messages:
        if message.get("type") != "message":
            continue

        text = clean_text(normalize_message_text(message.get("text", "")))
        if not text:
            continue

        prompt_text = truncate_text(text, MAX_MESSAGE_CHARS_FOR_PROMPT)
        sender = message.get("from") or message.get("actor") or "[unknown]"
        date = str(message.get("date", ""))
        records.append(
            {
                "id": message.get("id"),
                "date": date,
                "day": date[:10],
                "month": date[:7],
                "sender": sender,
                "text": text,
                "prompt_text": prompt_text,
                "prompt_length": len(prompt_text),
                "char_count": len(text),
                "word_count": len(text.split()),
            }
        )

    return records


def split_into_chunks(records, max_chars=MAX_CHARS_PER_CHUNK):
    chunks = []
    current_chunk = []
    current_length = 0

    for record in records:
        rendered_length = record["prompt_length"] + len(record["sender"]) + len(record["date"]) + 8
        separator_length = 1 if current_chunk else 0
        next_length = current_length + separator_length + rendered_length

        if current_chunk and next_length > max_chars:
            chunks.append(current_chunk)
            current_chunk = []
            current_length = 0
            next_length = rendered_length

        current_chunk.append(record)
        current_length = next_length

    if current_chunk:
        chunks.append(current_chunk)

    print(f"Total chunks: {len(chunks)}")
    return chunks


def split_prompt_items(items, max_chars):
    batches = []
    current_batch = []
    current_length = 0

    for item in items:
        item_length = item["prompt_length"]
        separator_length = 2 if current_batch else 0
        next_length = current_length + separator_length + item_length

        if current_batch and next_length > max_chars:
            batches.append(current_batch)
            current_batch = []
            current_length = 0
            next_length = item_length

        current_batch.append(item)
        current_length = next_length

    if current_batch:
        batches.append(current_batch)

    return batches


def render_chunk_records(chunk_records):
    lines = []
    for record in chunk_records:
        lines.append(f"[{record['date']}] {record['sender']}: {record['prompt_text']}")
    return "\n".join(lines)


def extract_json_object(text):
    text = text.strip()
    if not text:
        raise ValueError("Empty LLM response")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def post_ollama_json(prompt, system_prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": OLLAMA_TEMPERATURE,
            "num_ctx": OLLAMA_NUM_CTX,
        },
    }

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    last_error = None
    for attempt in range(1, OLLAMA_RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=OLLAMA_TIMEOUT_SECONDS) as response:
                body = json.loads(response.read().decode("utf-8"))
            return extract_json_object(body.get("response", ""))
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"Ollama HTTP {error.code}: {details}")
        except urllib.error.URLError as error:
            last_error = RuntimeError(
                f"Could not reach Ollama at {OLLAMA_URL}. "
                f"Is `ollama serve` running and is the model pulled? Original error: {error}"
            )
        except Exception as error:
            last_error = RuntimeError(f"Invalid Ollama response: {error}")

        print(f"❌ Ollama call failed on attempt {attempt}/{OLLAMA_RETRIES}: {last_error}")

    raise last_error


def ensure_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def safe_post_ollama_json(prompt, system_prompt, context_label):
    try:
        return post_ollama_json(prompt, system_prompt)
    except Exception as error:
        print(f"⚠️ {context_label} failed: {error}")
        return {}


def has_meaningful_response(summary_text, topics, highlights, action_items, open_questions):
    return any([summary_text, topics, highlights, action_items, open_questions])


def format_top_senders(sender_counts, limit):
    return [
        {"name": sender, "messages": count}
        for sender, count in sender_counts.most_common(limit)
    ]


def unique_strings(values, limit=None):
    items = []
    seen = set()

    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
        if limit is not None and len(items) >= limit:
            break

    return items


def build_summary_unit(summary_text, topics, highlights, action_items, open_questions, label):
    summary_text = str(summary_text or "").strip()
    topics = ensure_list(topics)
    highlights = ensure_list(highlights)
    action_items = ensure_list(action_items)
    open_questions = ensure_list(open_questions)

    prompt_text = truncate_text(
        "\n".join(
            [
                label,
                f"Summary: {summary_text or 'none'}",
                f"Topics: {'; '.join(topics) if topics else 'none'}",
                f"Highlights: {'; '.join(highlights) if highlights else 'none'}",
                f"Action items: {'; '.join(action_items) if action_items else 'none'}",
                f"Open questions: {'; '.join(open_questions) if open_questions else 'none'}",
            ]
        ),
        MAX_SUMMARY_UNIT_CHARS,
    )

    return {
        "summary": summary_text,
        "topics": topics,
        "highlights": highlights,
        "action_items": action_items,
        "open_questions": open_questions,
        "prompt_text": prompt_text,
        "prompt_length": len(prompt_text),
    }


def render_summary_units(summary_units):
    return "\n\n".join(unit["prompt_text"] for unit in summary_units)


def build_fallback_fields(summary_units, label):
    topic_counts = Counter()
    collected_highlights = []
    collected_actions = []
    collected_questions = []
    summary_excerpts = []

    for unit in summary_units:
        topic_counts.update(ensure_list(unit.get("topics")))
        collected_highlights.extend(ensure_list(unit.get("highlights")))
        collected_actions.extend(ensure_list(unit.get("action_items")))
        collected_questions.extend(ensure_list(unit.get("open_questions")))

        summary_text = str(unit.get("summary", "")).strip()
        if summary_text:
            summary_excerpts.append(truncate_text(summary_text, 180))

    topics = [topic for topic, _count in topic_counts.most_common(6)] or ["general discussion"]
    highlights = unique_strings(collected_highlights, limit=5)
    if not highlights:
        highlights = unique_strings(summary_excerpts, limit=3)

    summary_text = (
        f"{label} covering {len(summary_units)} summaries. "
        f"Main themes include {', '.join(topics[:3])}."
    )

    return {
        "summary": summary_text,
        "topics": topics,
        "highlights": highlights,
        "action_items": unique_strings(collected_actions, limit=5),
        "open_questions": unique_strings(collected_questions, limit=5),
    }


def synthesize_summary_batch(chat_name, summary_units, stage_index, batch_index, total_batches):
    system_prompt = (
        "You synthesize Telegram chat summaries into a higher-level summary. "
        "Preserve recurring themes, key highlights, action items, and open questions. "
        "Respond with strict JSON only."
    )

    prompt = (
        f"Chat name: {chat_name}\n"
        f"Synthesis stage: {stage_index}\n"
        f"Batch: {batch_index + 1}/{total_batches}\n"
        f"Items in batch: {len(summary_units)}\n"
        "Return exactly this JSON object:\n"
        "{\n"
        '  "summary": "2-5 sentence summary",\n'
        '  "topics": ["topic 1", "topic 2"],\n'
        '  "highlights": ["important point 1", "important point 2"],\n'
        '  "action_items": ["action 1"],\n'
        '  "open_questions": ["question 1"]\n'
        "}\n\n"
        "Summaries to synthesize:\n"
        f"{render_summary_units(summary_units)}"
    )

    llm = safe_post_ollama_json(
        prompt,
        system_prompt,
        f"Synthesis stage {stage_index} batch {batch_index + 1}",
    )

    summary_text = str(llm.get("summary", "")).strip()
    topics = ensure_list(llm.get("topics"))
    highlights = ensure_list(llm.get("highlights"))
    action_items = ensure_list(llm.get("action_items"))
    open_questions = ensure_list(llm.get("open_questions"))

    if not has_meaningful_response(summary_text, topics, highlights, action_items, open_questions):
        rescue_prompt = (
            f"Chat name: {chat_name}\n"
            f"Synthesis stage: {stage_index}\n"
            f"Batch: {batch_index + 1}/{total_batches}\n"
            "The previous attempt returned empty or unusable output. "
            "You must still produce a non-empty summary even if the content is repetitive.\n"
            "Return exactly this JSON object:\n"
            "{\n"
            '  "summary": "2-4 sentence summary",\n'
            '  "topics": ["topic 1"],\n'
            '  "highlights": ["important point 1"],\n'
            '  "action_items": [],\n'
            '  "open_questions": []\n'
            "}\n\n"
            "Summaries to synthesize:\n"
            f"{render_summary_units(summary_units)}"
        )
        llm = safe_post_ollama_json(
            rescue_prompt,
            system_prompt,
            f"Synthesis rescue stage {stage_index} batch {batch_index + 1}",
        )
        summary_text = str(llm.get("summary", "")).strip()
        topics = ensure_list(llm.get("topics"))
        highlights = ensure_list(llm.get("highlights"))
        action_items = ensure_list(llm.get("action_items"))
        open_questions = ensure_list(llm.get("open_questions"))

    if not has_meaningful_response(summary_text, topics, highlights, action_items, open_questions):
        fallback = build_fallback_fields(
            summary_units,
            f"Synthesis stage {stage_index} batch {batch_index + 1}",
        )
        summary_text = fallback["summary"]
        topics = fallback["topics"]
        highlights = fallback["highlights"]
        action_items = fallback["action_items"]
        open_questions = fallback["open_questions"]
        print(
            f"⚠️ Falling back to deterministic synthesis for stage {stage_index} batch {batch_index + 1}"
        )

    return {
        "summary": summary_text,
        "topics": topics,
        "highlights": highlights,
        "action_items": action_items,
        "open_questions": open_questions,
    }


def summarize_chunk(chat_name, chunk_records, chunk_index):
    sender_counts = Counter(record["sender"] for record in chunk_records)
    start_date = chunk_records[0]["date"]
    end_date = chunk_records[-1]["date"]
    message_count = len(chunk_records)
    sender_count = len(sender_counts)
    top_senders = format_top_senders(sender_counts, TOP_SENDERS_PER_CHUNK)

    system_prompt = (
        "You summarize Telegram chat chunks. Focus on substantive discussion, decisions, "
        "questions, explanations, and action items. Ignore boilerplate code syntax unless the "
        "discussion is specifically about that code. Respond with strict JSON only."
    )

    prompt = (
        f"Chat name: {chat_name}\n"
        f"Chunk index: {chunk_index}\n"
        f"Date range: {start_date} -> {end_date}\n"
        f"Message count: {message_count}\n"
        "Return exactly this JSON object:\n"
        "{\n"
        '  "summary": "2-4 sentence summary",\n'
        '  "topics": ["topic 1", "topic 2"],\n'
        '  "highlights": ["important point 1", "important point 2"],\n'
        '  "action_items": ["action 1"],\n'
        '  "open_questions": ["question 1"]\n'
        "}\n\n"
        "Conversation chunk:\n"
        f"{render_chunk_records(chunk_records)}"
    )

    llm = safe_post_ollama_json(prompt, system_prompt, f"Chunk {chunk_index}")

    summary_text = str(llm.get("summary", "")).strip()
    topics = ensure_list(llm.get("topics"))
    highlights = ensure_list(llm.get("highlights"))
    action_items = ensure_list(llm.get("action_items"))
    open_questions = ensure_list(llm.get("open_questions"))

    if not has_meaningful_response(summary_text, topics, highlights, action_items, open_questions):
        rescue_prompt = (
            f"Chat name: {chat_name}\n"
            f"Chunk index: {chunk_index}\n"
            f"Date range: {start_date} -> {end_date}\n"
            f"Message count: {message_count}\n"
            "The previous attempt returned empty fields. This chunk may be low-signal or casual chat, "
            "but you must still summarize it. Never return an empty JSON object.\n"
            "Return exactly this JSON object:\n"
            "{\n"
            '  "summary": "1-3 sentence summary",\n'
            '  "topics": ["topic 1"],\n'
            '  "highlights": ["important point 1"],\n'
            '  "action_items": [],\n'
            '  "open_questions": []\n'
            "}\n\n"
            "Conversation chunk:\n"
            f"{render_chunk_records(chunk_records)}"
        )
        llm = safe_post_ollama_json(
            rescue_prompt,
            system_prompt,
            f"Chunk {chunk_index} rescue",
        )
        summary_text = str(llm.get("summary", "")).strip()
        topics = ensure_list(llm.get("topics"))
        highlights = ensure_list(llm.get("highlights"))
        action_items = ensure_list(llm.get("action_items"))
        open_questions = ensure_list(llm.get("open_questions"))

    if not has_meaningful_response(summary_text, topics, highlights, action_items, open_questions):
        fallback_highlights = []
        for record in sorted(chunk_records, key=lambda item: (-item["char_count"], item["date"]))[:3]:
            excerpt = truncate_text(record["prompt_text"], 160)
            if excerpt:
                fallback_highlights.append(f"{record['sender']}: {excerpt}")

        top_sender_names = ", ".join(
            f"{item['name']} ({item['messages']})" for item in top_senders[:3]
        ) or "unknown participants"
        summary_text = (
            f"Low-signal or casual discussion between {sender_count} participants from "
            f"{start_date} to {end_date}. Most active senders: {top_sender_names}."
        )
        topics = ["general discussion"]
        highlights = fallback_highlights[:2]
        action_items = []
        open_questions = []
        print(f"⚠️ Falling back to deterministic summary for chunk {chunk_index}")

    return {
        "chunk_index": chunk_index,
        "start_date": start_date,
        "end_date": end_date,
        "message_count": message_count,
        "sender_count": sender_count,
        "top_senders": top_senders,
        "summary": summary_text,
        "topics": topics,
        "highlights": highlights,
        "action_items": action_items,
        "open_questions": open_questions,
        "character_count": sum(record["char_count"] for record in chunk_records),
        "word_count": sum(record["word_count"] for record in chunk_records),
    }


def build_final_memory(chat_name, all_messages, records, chunk_summaries):
    sender_counts = Counter(record["sender"] for record in records)
    day_counts = Counter(record["day"] for record in records if record["day"])
    month_counts = Counter(record["month"] for record in records if record["month"])
    service_actions = Counter(
        message.get("action")
        for message in all_messages
        if message.get("type") == "service" and message.get("action")
    )

    top_senders = format_top_senders(sender_counts, TOP_SENDERS_FINAL)
    top_days = [{"day": day, "messages": count} for day, count in day_counts.most_common(TOP_DAYS_FINAL)]
    month_distribution = [{"month": month, "messages": count} for month, count in month_counts.most_common()]
    start_date = records[0]["date"] if records else ""
    end_date = records[-1]["date"] if records else ""

    summary_units = [
        build_summary_unit(
            chunk_summary["summary"],
            chunk_summary["topics"],
            chunk_summary["highlights"],
            chunk_summary["action_items"],
            chunk_summary["open_questions"],
            (
                f"Chunk {chunk_summary['chunk_index']} | "
                f"{chunk_summary['start_date']} -> {chunk_summary['end_date']}"
            ),
        )
        for chunk_summary in chunk_summaries
    ]

    stage_index = 1
    while len(summary_units) > 1:
        batches = split_prompt_items(summary_units, MAX_CHARS_PER_SYNTHESIS_BATCH)
        next_stage_units = []

        for batch_index, batch in enumerate(batches):
            synthesized = synthesize_summary_batch(
                chat_name,
                batch,
                stage_index,
                batch_index,
                len(batches),
            )
            next_stage_units.append(
                build_summary_unit(
                    synthesized["summary"],
                    synthesized["topics"],
                    synthesized["highlights"],
                    synthesized["action_items"],
                    synthesized["open_questions"],
                    f"Synthesis stage {stage_index} batch {batch_index + 1}/{len(batches)}",
                )
            )

        summary_units = next_stage_units
        stage_index += 1

    final_fields = summary_units[0] if summary_units else build_fallback_fields([], "Final synthesis")

    return {
        "chat_name": chat_name,
        "summary": final_fields["summary"],
        "message_count": len(records),
        "participant_count": len(sender_counts),
        "service_event_count": sum(1 for message in all_messages if message.get("type") == "service"),
        "date_range": {
            "start": start_date,
            "end": end_date,
        },
        "top_senders": top_senders,
        "top_days": top_days,
        "month_distribution": month_distribution,
        "service_actions": [{"action": action, "count": count} for action, count in service_actions.most_common()],
        "major_topics": final_fields["topics"],
        "highlights": final_fields["highlights"],
        "action_items": final_fields["action_items"],
        "open_questions": final_fields["open_questions"],
        "chunk_count": len(chunk_summaries),
        "chunk_overview": [
            {
                "chunk_index": chunk_summary["chunk_index"],
                "start_date": chunk_summary["start_date"],
                "end_date": chunk_summary["end_date"],
                "summary": chunk_summary["summary"],
                "topics": chunk_summary["topics"],
            }
            for chunk_summary in chunk_summaries
        ],
        "model": OLLAMA_MODEL,
    }


def load_progress():
    progress_path = Path(PROGRESS_FILE)
    if not progress_path.exists():
        return {"version": PIPELINE_VERSION, "last_index": 0, "chunk_summaries": []}

    with progress_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if data.get("version") != PIPELINE_VERSION:
        return {"version": PIPELINE_VERSION, "last_index": 0, "chunk_summaries": []}

    last_index = int(data.get("last_index", 0))
    chunk_summaries = data.get("chunk_summaries", [])
    if not isinstance(chunk_summaries, list):
        chunk_summaries = []

    return {
        "version": PIPELINE_VERSION,
        "last_index": last_index,
        "chunk_summaries": chunk_summaries,
    }


def save_progress(index, chunk_summaries):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as file:
        json.dump(
            {
                "version": PIPELINE_VERSION,
                "last_index": index,
                "chunk_summaries": chunk_summaries,
            },
            file,
            ensure_ascii=False,
            indent=2,
        )


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    all_messages = data.get("messages", [])
    records = build_records(all_messages)
    if not records:
        raise RuntimeError("No text messages found in the Telegram export.")

    chunks = split_into_chunks(records)
    progress = load_progress()
    start_index = progress["last_index"]
    chunk_summaries = progress["chunk_summaries"]

    if start_index > len(chunks) or len(chunk_summaries) > len(chunks):
        start_index = 0
        chunk_summaries = []

    print(f"Ollama URL: {OLLAMA_URL}")
    print(f"Ollama model: {OLLAMA_MODEL}")
    print(f"Resuming from chunk {start_index} / {len(chunks)}")

    chat_name = data.get("name", "Telegram chat")

    for index in tqdm(range(start_index, len(chunks)), desc="Summarizing chunks"):
        summary = summarize_chunk(chat_name, chunks[index], index)
        if index < len(chunk_summaries):
            chunk_summaries[index] = summary
        else:
            chunk_summaries.append(summary)
        save_progress(index + 1, chunk_summaries)

    with open(CHUNK_SUMMARIES_FILE, "w", encoding="utf-8") as file:
        json.dump(chunk_summaries, file, ensure_ascii=False, indent=2)

    with open(LEGACY_SUMMARIES_FILE, "w", encoding="utf-8") as file:
        json.dump(
            [chunk_summary["summary"] for chunk_summary in chunk_summaries],
            file,
            ensure_ascii=False,
            indent=2,
        )

    final_memory = build_final_memory(chat_name, all_messages, records, chunk_summaries)

    with open(FINAL_MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(final_memory, file, ensure_ascii=False, indent=2)

    print(f"✅ Saved {len(chunk_summaries)} chunk summaries to {CHUNK_SUMMARIES_FILE}")
    print(f"✅ Saved legacy summaries to {LEGACY_SUMMARIES_FILE}")
    print(f"✅ Saved final memory to {FINAL_MEMORY_FILE}")
    print(f"Progress file {PROGRESS_FILE} updated for resume capability.")


if __name__ == "__main__":
    main()
