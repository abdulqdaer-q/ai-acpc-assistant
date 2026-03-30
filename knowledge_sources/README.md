# knowledge_sources

Optional external documents for the bot's curated RAG layer.

The bot will load `knowledge_sources/documents.jsonl` if it exists.
Use `documents.example.jsonl` as the starting schema reference.

Each line should be one JSON object with a normalized schema such as:

```json
{
  "doc_id": "codeforces:977C",
  "source": "codeforces",
  "doc_type": "problem_metadata",
  "problem_id": "977C",
  "title": "Less or Equal",
  "summary": "Find an integer x such that exactly k elements are less than or equal to x.",
  "topics": ["binary search", "sorting"],
  "tags": ["implementation", "sortings"],
  "highlights": [
    "Focus on boundary handling for k=0 and duplicates."
  ],
  "url": "https://codeforces.com/problemset/problem/977/C",
  "language": "en"
}
```

Recommended source values:
- `external_curated`
- `codeforces`
- `cses`
- `icpc`
- `acpc_internal`

Recommended doc types:
- `problem_metadata`
- `editorial_note`
- `topic_note`
- `reference_note`

Keep these documents concise and curated. Do not dump giant raw webpages into this file.
The retrieval layer gives each source a configurable weight from `bot_config.json`, so source quality matters.
